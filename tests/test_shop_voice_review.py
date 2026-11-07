"""Separate voice vs factual support; synthetic SDK fixtures are not NLI scores."""
import asyncio
import json
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.config import ROOT,Settings
from app.dialogue import FALLBACK
from app.main import create_app
from app.semantic_review import (IndexedReview,Review,ModelAnalysisProvider,ReviewOutcome,
                                 evidence_bundle,review_reply,rewrite_feedback)
from scripts.retest_scene_roleplay import OLD,QUERY


def wire(text,issues=None):
    from app.semantic_review import review_units
    return {'confidence':.95,'role_issues':issues or [],'units':[
        {'id':u['id'],'kind':'assertion','verdict':'supported','evidence_ids':['scene_profile']}
        for u in review_units(text)]}


def provider_for(output):
    def handler(request):
        payload=json.loads(request.content)
        assert '必须先做的独立角色口吻检查' in payload['messages'][0]['content']
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(output)}}]})
    return ModelAnalysisProvider(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key'),
                                 httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))


def test_supported_atmosphere_cannot_erase_separate_role_issue():
    async def check():
        history=[{'role':'user','content':QUERY}]
        return await review_reply(provider_for(wire(OLD,['u0'])),OLD,history,evidence_bundle(history,[],None,None))
    result=asyncio.run(check())
    assert result.status=='revise' and result.result.role_issues==[0]
    assert all(s.verdict=='supported' for s in result.result.segments)
    feedback=rewrite_feedback(result.result)
    assert 'role_mismatch' in feedback and '保留授权' in feedback and '窗外' in feedback


@pytest.mark.parametrize('mutation',['missing','unknown','duplicate','wrong_type'])
def test_bad_wire_role_issue_ids_fail_closed(mutation):
    output=wire(OLD,['u0'])
    if mutation=='missing':output.pop('role_issues')
    if mutation=='unknown':output['role_issues']=['u99']
    if mutation=='duplicate':output['role_issues']=['u0','u0']
    if mutation=='wrong_type':output['role_issues']=[0]
    async def check():
        return await review_reply(provider_for(output),OLD,[],[{'id':'scene_profile'}])
    result=asyncio.run(check())
    assert result.status=='unavailable' and result.failure=='invalid_output' and result.result is None


@pytest.mark.parametrize('indices',[[2],[0,0],[-1],[True],[.5]])
def test_domain_role_issue_indexes_are_strict_and_in_range(indices):
    with pytest.raises(ValidationError):
        Review(decision='revise',confidence=.95,role_issues=indices,segments=[{
            'text':'窗外安静。','kind':'assertion','verdict':'supported',
            'evidence_ids':['scene_profile'],'reason':'evidence_supports'}])


def test_accept_cannot_hide_valid_role_issue():
    with pytest.raises(ValidationError):
        Review(decision='accept',confidence=.95,role_issues=[0],segments=[{
            'text':'我不知道店况。','kind':'epistemic','verdict':'supported',
            'evidence_ids':[],'reason':'evidence_supports'}])


def test_role_issue_requires_visible_scene_context():
    async def check():
        return await review_reply(provider_for(wire(OLD,['u0'])),OLD,[],[{'id':'role_profile'}])
    result=asyncio.run(check())
    assert result.status=='unavailable' and result.failure=='unknown_evidence'


@pytest.mark.parametrize('text',[
    '店里挺安静的，暖灯下翻书很舒服。',
    '出版社具体什么时候送到，我还不确定。',
    '“我不知道自家店况”这句话不太合角色。',
    '以后路过可以来坐坐。',
])
def test_empty_role_issues_preserve_nonproblem_fixture_paths(text):
    # Model classifications are fixtures; only contract/control flow is tested.
    async def check():
        return await review_reply(provider_for(wire(text)),text,[],[{'id':'scene_profile'}])
    result=asyncio.run(check())
    assert result.status=='accept' and result.result.role_issues==[]


@pytest.mark.parametrize('second',['safe','repeat','invalid'])
def test_sdk_role_issue_triggers_one_rewrite_and_never_saves_bad_draft(tmp_path,second):
    good='店里这会儿挺安静，正好听你聊聊今天。'
    requests=[]
    def handler(request):
        payload=json.loads(request.content);requests.append(payload)
        data=json.loads(payload['messages'][1]['content'])
        output={'confidence':.95,'role_issues':['u0'] if len(requests)==1 or second=='repeat' else [],
            'units':[{'id':u['id'],'kind':'assertion','verdict':'supported','evidence_ids':['scene_profile']} for u in data['units']]}
        if len(requests)==2 and second=='invalid':output['role_issues']=['u999']
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(output)}}]})
    class Judge(ModelAnalysisProvider):
        async def parse(self,*args):
            self.http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
            return await super().parse(*args)
    judge=Judge(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key'))
    generator=SimpleNamespace(generate=AsyncMock(side_effect=[OLD,good if second=='safe' else OLD]))
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'voice.sqlite3')),
                   generator,semantic_judge=judge)
    client=TestClient(app);headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    response=client.post('/v1/chat',headers=headers,json={'message':QUERY})
    assert response.status_code==200 and response.json()['reply']==(good if second=='safe' else FALLBACK)
    assert generator.generate.await_count==len(requests)==2
    assert 'role_mismatch' in generator.generate.call_args_list[1].args[1]
    assert '保留授权' in generator.generate.call_args_list[1].args[1]
    assert OLD not in str(client.get('/v1/session').json()['messages'])
    assert 'role_issues' not in response.json()


def test_targeted_live_entry_calls_judge_once_and_requires_opt_in(monkeypatch):
    from scripts import retest_shop_voice as script
    reviewer=AsyncMock(return_value=ReviewOutcome('unavailable',None,'timeout'))
    monkeypatch.setattr(script,'review_reply',reviewer)
    report=asyncio.run(script.retest(Settings(_env_file=None,chat_provider='gemini')))
    assert reviewer.await_count==1 and report['attempts']==report['max_attempts']==1
    assert 'generation' not in report and report['failure']=='timeout'
    result=subprocess.run([sys.executable,'scripts/retest_shop_voice.py'],cwd=ROOT,
                          env={**os.environ,'CHAT_PROVIDER':'invalid'},capture_output=True,text=True)
    assert result.returncode==2 and '显式--live' in result.stderr

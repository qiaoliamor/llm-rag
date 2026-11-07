"""Author-permitted narrative regression fixtures, not model accuracy scoring."""
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
from app.config import ROOT,Settings
from app.dialogue import SCENE_PROFILE,instructions
from app.main import create_app
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,ReviewOutcome,review_units

APPROVED='这会儿店里挺安静的，只能听到偶尔翻动书页的沙沙声。窗外斜阳正好，桌上的暖灯也刚亮起。你今天想聊点什么，还是打算随便坐坐？'


def completion(content):
    return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
        'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(content)}}]})


@pytest.mark.parametrize('text',[APPROVED,'窗外挺安静，我放下手里的书。',
    '书页沙沙作响，有人在背景安静读书。','我给自己倒杯茶，再翻两页书。'])
def test_approved_narrative_goes_through_sdk_without_forced_rewrite(tmp_path,text):
    seen=[]
    def handler(request):
        payload=json.loads(request.content);seen.append(payload)
        assert '无需确定是谁翻书' in payload['messages'][0]['content']
        data=json.loads(payload['messages'][1]['content'])
        assert next(e for e in data['evidence'] if e['id']=='scene_profile')['data']['version']=='1.1'
        return completion({'confidence':.95,'role_issues':[],'units':[{
            'id':u['id'],'kind':'nonfactual' if u['text'].rstrip().endswith('？') else 'assertion',
            'verdict':'not_applicable' if u['text'].rstrip().endswith('？') else 'supported',
            'evidence_ids':[] if u['text'].rstrip().endswith('？') else ['scene_profile']} for u in data['units']]})
    judge=ModelAnalysisProvider(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key'),
                                httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
    generator=SimpleNamespace(generate=AsyncMock(return_value=text))
    client=TestClient(create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'narrative.sqlite3')),
                                generator,semantic_judge=judge))
    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    response=client.post('/v1/chat',headers=headers,json={'message':'你店里安静吗？'})
    assert response.json()['reply']==text and response.json()['semantic_review']['status']=='accepted'
    assert generator.generate.await_count==len(seen)==1


@pytest.mark.parametrize('bad',[
    '窗外安静，我小时候是母亲教我开书店的。',
    '书页沙沙响，我们已经恋爱三年了。',
    '店里挺安静，你去年到这里哭过一次。',
    '暖灯刚亮，你已经坐在窗边了。',
    '窗外的斜阳说明你所在的北京现在25度。',
])
def test_personal_or_real_world_claim_does_not_inherit_narrative_permission(tmp_path,bad):
    def review(text,unsafe):
        return {'decision':'revise' if unsafe else 'accept','confidence':.95,'role_issues':[],
            'segments':[{'text':text,'kind':'assertion','verdict':'unsupported' if unsafe else 'supported',
            'evidence_ids':[] if unsafe else ['scene_profile'],'reason':'missing_evidence' if unsafe else 'evidence_supports'}]}
    generator=SimpleNamespace(generate=AsyncMock(side_effect=[bad,APPROVED]))
    judge=SimpleNamespace(review=AsyncMock(side_effect=[review(bad,True),review(APPROVED,False)]))
    client=TestClient(create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'boundary.sqlite3')),
                                generator,semantic_judge=judge))
    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    response=client.post('/v1/chat',headers=headers,json={'message':'你好'})
    assert response.json()['reply']==APPROVED and generator.generate.await_count==2
    assert bad not in str(client.get('/v1/session').json()['messages'])
    assert '保留场景设定授权' in generator.generate.call_args_list[1].args[1]


def test_policy_and_positive_example_are_shared_in_generation_and_review():
    assert SCENE_PROFILE['style_example']==APPROVED
    assert '无需追究是谁' in SCENE_PROFILE['improvisation']
    assert APPROVED in INDEXED_PROMPT and 'role_issues=[]' in INDEXED_PROMPT
    for mode in ('canon','rag','direct'):
        assert APPROVED in instructions(mode) and '不把每次翻页' in instructions(mode)


def test_only_one_previously_failed_case_is_retested_and_cli_is_gated(monkeypatch):
    from scripts import retest_narrative_boundary as script
    reviewer=AsyncMock(return_value=ReviewOutcome('unavailable',None,'timeout'))
    monkeypatch.setattr(script,'review_reply',reviewer)
    report=asyncio.run(script.retest(Settings(_env_file=None,chat_provider='gemini')))
    assert reviewer.await_count==report['attempts']==report['max_attempts']==1
    assert report['case_id']=='scene-conditional-expanded' and report['failure']=='timeout'
    assert report['candidate']!=APPROVED
    result=subprocess.run([sys.executable,'scripts/retest_narrative_boundary.py'],cwd=ROOT,
        env={**os.environ,'CHAT_PROVIDER':'invalid'},capture_output=True,text=True)
    assert result.returncode==2 and '显式--live' in result.stderr

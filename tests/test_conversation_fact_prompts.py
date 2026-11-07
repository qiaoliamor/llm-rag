"""Prompt delivery / pipeline regressions, not mock semantic accuracy scores."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx2
import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.dialogue import CONVERSATION_FACT_RULES,FALLBACK,instructions
from app.main import create_app
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle,review_reply


CASES=[
    # Hand-authored transport fixtures: labels are NOT inferred by this test.
    ('店里具体的情况我没办法确定，也没收到什么新的消息。','你好','unsupported',[]),
    ('你今天过来，是想找本什么书，还是随便转转？','你好','unsupported',[]),
    ('你今天过来，是想找本什么书，还是随便转转？','我明天打算来书店','unsupported',[]),
    ('你今天过来，是想找本什么书，还是随便转转？','我上周来过书店','unsupported',[]),
    ('你今天过来，是想找本什么书，还是随便转转？','我已经在你店里了','supported',['user_0']),
    ('以后有空可以来坐坐。','你好','not_applicable',[]),
    ('你现在到店里了吗？','你好','not_applicable',[]),
    ('不是说没有收到消息，而是目前还无法确定。','你好','supported',[]),
]


@pytest.mark.parametrize('text,query,verdict,ids',CASES)
def test_sdk_carries_scope_rules_and_maps_fixture_verdicts(text,query,verdict,ids):
    calls=[]
    def handler(request):
        payload=json.loads(request.content);calls.append(payload)
        assert payload['messages'][0]['content']==INDEXED_PROMPT
        assert '先审前提' in payload['messages'][0]['content']
        data=json.loads(payload['messages'][1]['content'])
        assert data['evidence'][-1]['text']==query
        kind='nonfactual' if verdict=='not_applicable' else 'epistemic' if not ids and verdict=='supported' else 'assertion'
        output={'confidence':.95,'role_issues':[],'units':[{'id':u['id'],'kind':kind,'verdict':verdict,'evidence_ids':ids} for u in data['units']]}
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(output)}}]})
    async def check():
        config=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key')
        judge=ModelAnalysisProvider(config,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        history=[{'role':'user','content':query}]
        return await review_reply(judge,text,history,evidence_bundle(history,[],None,None))
    result=asyncio.run(check())
    assert result.status==('revise' if verdict=='unsupported' else 'accept') and len(calls)==1


@pytest.mark.parametrize('bad',[
    '店里具体的情况我没办法确定，也没收到什么新的消息。',
    '你今天过来，是想找本什么书，还是随便转转？',
])
@pytest.mark.parametrize('second',['safe','unsafe','error'])
def test_both_prompts_reach_rewrite_and_no_bad_reply_is_saved(tmp_path,bad,second):
    safe='你今天想聊点什么？'
    def result(text,unsafe):
        return {'decision':'revise' if unsafe else 'accept','confidence':.95,'segments':[{
            'text':text,'kind':'assertion' if unsafe else 'question','verdict':'unsupported' if unsafe else 'not_applicable',
            'evidence_ids':[],'reason':'missing_evidence' if unsafe else 'nonfactual'}]}
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[bad,safe if second=='safe' else bad]))
    judge=SimpleNamespace(review=AsyncMock(side_effect=[result(bad,True),
        ValueError('private-test-error') if second=='error' else result(safe,False) if second=='safe' else result(bad,True)]))
    config=Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'synthetic.sqlite3'))
    client=TestClient(create_app(config,provider,semantic_judge=judge))
    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    response=client.post('/v1/chat',headers=headers,json={'message':'你好'})
    assert response.status_code==200 and response.json()['reply']==(safe if second=='safe' else FALLBACK)
    for call in provider.generate.call_args_list:
        assert CONVERSATION_FACT_RULES in call.args[1]
    assert 'missing_evidence' in provider.generate.call_args_list[1].args[1]
    assert bad not in str(client.get('/v1/session').json()['messages'])
    assert provider.generate.await_count==judge.review.await_count==2


def test_prompt_source_covers_negative_claims_and_presuppositions():
    assert CONVERSATION_FACT_RULES in instructions('canon')
    assert CONVERSATION_FACT_RULES in instructions('rag')
    assert CONVERSATION_FACT_RULES in instructions('direct')
    for phrase in ('角色边界的未知','接收记录为空','今天已到店','明天打算来','先审前提'):
        assert phrase in INDEXED_PROMPT


def test_targeted_live_script_is_gated_and_capped_without_network(monkeypatch):
    from scripts import retest_semantic_failures as script
    assert len(script.CASES)==2
    counts={'judge':0,'generation':0}
    async def judge(*args,**kwargs):
        from app.semantic_review import ReviewOutcome
        counts['judge']+=1
        return ReviewOutcome('unavailable',None,'upstream_unavailable')
    async def generate(*args):
        from app.dialogue import ProviderFailure
        counts['generation']+=1
        raise ProviderFailure('rate_limit','private-test-error',429)
    monkeypatch.setattr(script,'review_reply',judge)
    monkeypatch.setattr(script.GeminiProvider,'generate',generate)
    report=asyncio.run(script.retest(Settings(_env_file=None,chat_provider='gemini'),interval=0))
    assert report['attempts']==4 and counts=={'judge':2,'generation':2}
    assert 'private-test-error' not in str(report)
    root=Path(__file__).resolve().parent.parent
    result=subprocess.run([sys.executable,'scripts/retest_semantic_failures.py'],cwd=root,
        env={**os.environ,'CHAT_PROVIDER':'invalid'},capture_output=True,text=True)
    assert result.returncode==2 and '显式--live' in result.stderr

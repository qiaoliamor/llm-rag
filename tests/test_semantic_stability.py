"""Protocol regressions only; fake labels do not establish semantic quality."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import httpx2
import pytest
from app.config import Settings
from app.semantic_review import ModelAnalysisProvider,IndexedReview,review_units,review_reply


@pytest.mark.parametrize('text',[
    '你好。\n\n你住在New Willow City。','“店里安静。”这是假设，不是近况。',
    '假如店里安静，我们可以聊书；我还不能确定近况。','没有标点也应覆盖',
    '  我记得你的名字。\n你想聊聊吗？  ',
])
def test_units_cover_exact_original_without_model_copy(text):
    units=review_units(text)
    assert ''.join(u['text'] for u in units)==text
    assert [u['id'] for u in units]==[f'u{i}' for i in range(len(units))]


@pytest.mark.parametrize('ids',[[],['u0'],['u0','u0'],['u1','u0'],['u0','u2'],['u0','u1','u2']])
def test_missing_duplicate_reordered_and_extra_units_fail_closed(ids):
    provider=ModelAnalysisProvider(Settings(_env_file=None,chat_provider='mock'))
    provider.parse=AsyncMock(return_value=IndexedReview(confidence=.95,units=[
        {'id':id,'kind':'nonfactual','verdict':'not_applicable','evidence_ids':[]} for id in ids]))
    outcome=asyncio.run(review_reply(provider,'你好。你想聊什么？',[],[]))
    assert outcome.status=='unavailable' and outcome.failure=='invalid_output'
    assert outcome.result is None


@pytest.mark.parametrize('text',['','   ','文'*2501,'好。'*33])
def test_local_limits_do_not_call_model(text):
    provider=ModelAnalysisProvider(Settings(_env_file=None,chat_provider='mock'))
    provider.parse=AsyncMock()
    result=asyncio.run(review_reply(provider,text,[],[]))
    assert result.status=='unavailable'
    provider.parse.assert_not_called()


def test_mixed_unit_keeps_all_text_and_unsupported_clause():
    provider=ModelAnalysisProvider(Settings(_env_file=None,chat_provider='mock'))
    text='你住在合成青禾市，走十分钟就能到书店。'
    provider.parse=AsyncMock(return_value=IndexedReview(confidence=.95,units=[{
        'id':'u0','kind':'assertion','verdict':'unsupported','evidence_ids':[]}]))
    result=asyncio.run(provider.review(text,[],[]))
    assert result.decision=='revise' and result.segments[0].text==text
    data=provider.parse.call_args.args[2]
    assert set(data)=={'units','evidence'} and 'candidate' not in data


@pytest.mark.parametrize('provider_name',['gemini','openai'])
@pytest.mark.parametrize('mode',['truncated','refused','malformed','unknown_id','empty','low_confidence'])
def test_real_sdk_failure_codes_and_zero_retries(provider_name,mode):
    calls=[]
    def handler(request):
        calls.append(json.loads(request.content))
        output={'confidence':.2 if mode=='low_confidence' else .95,'units':[
            {'id':'u0','kind':'assertion','verdict':'supported','evidence_ids':['missing' if mode=='unknown_id' else 'C01']}]}
        message={'role':'assistant','content':json.dumps(output)}
        if mode=='malformed':message['content']='{"confidence":'
        if mode=='refused':message={'role':'assistant','content':None,'refusal':'private-upstream-refusal'}
        choices=[] if mode=='empty' else [{'index':0,'finish_reason':'length' if mode=='truncated' else 'stop','message':message}]
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test','choices':choices})
    async def check():
        config=Settings(_env_file=None,chat_provider=provider_name,gemini_api_key='test-key',openai_api_key='test-key')
        provider=ModelAnalysisProvider(config,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        return await review_reply(provider,'我今年28岁。',[],[{'id':'C01'}])
    result=asyncio.run(check())
    expected={'truncated':'truncated_output','refused':'refused_output','malformed':'invalid_output',
              'unknown_id':'unknown_evidence','empty':'incomplete_output','low_confidence':'low_confidence'}
    assert result.failure==expected[mode] and result.status in ('unavailable','uncertain')
    assert len(calls)==1
    assert 'private-upstream' not in str(result)


def test_paired_benchmark_is_fixed_and_cannot_run_implicitly():
    from scripts.compare_semantic_review import cases,baseline_provider,summarize
    fixtures,digest=cases()
    assert len(fixtures)==8 and len(digest)==64
    assert baseline_provider() and {c['expected'] for c in fixtures}=={'accept','revise'}
    env={**os.environ,'GEMINI_API_KEY':'test-must-not-send','CHAT_PROVIDER':'invalid-provider'}
    root=Path(__file__).resolve().parent.parent
    result=subprocess.run([sys.executable,'scripts/compare_semantic_review.py'],cwd=root,env=env,capture_output=True,text=True)
    assert result.returncode==2 and '显式--live' in result.stderr and 'test-must-not-send' not in result.stderr
    assert summarize([])['indexed']['p50_seconds'] is None


def test_frozen_baseline_uses_original_transport_and_converts_domain_result():
    from scripts.compare_semantic_review import baseline_provider
    def handler(request):
        payload=json.loads(request.content)
        assert payload['response_format']['json_schema']['name']=='WireReview'
        assert payload['max_tokens']==1000 and 'candidate' in json.loads(payload['messages'][1]['content'])
        content={'confidence':.95,'segments':[{'text':'我今年28岁。','kind':'assertion','verdict':'supported','evidence_ids':['C01']}]}
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(content)}}]})
    async def check():
        provider=baseline_provider()(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key'),
                                     httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        return await review_reply(provider,'我今年28岁。',[],[{'id':'C01'}])
    assert asyncio.run(check()).status=='accept'


def test_indexed_sdk_rewrite_rechecks_final_and_never_saves_draft(tmp_path):
    from types import SimpleNamespace
    from fastapi.testclient import TestClient
    from app.main import create_app
    bad='柜台旁多了三箱诗集。';good='你想聊聊喜欢的书吗？'
    requests=[]
    def handler(request):
        payload=json.loads(request.content);requests.append(payload)
        units=json.loads(payload['messages'][1]['content'])['units']
        content={'confidence':.95,'units':[{'id':u['id'],'kind':'assertion' if len(requests)==1 else 'nonfactual',
                 'verdict':'unsupported' if len(requests)==1 else 'not_applicable','evidence_ids':[]} for u in units]}
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(content)}}]})
    class Judge(ModelAnalysisProvider):
        async def parse(self,*args):
            self.http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(handler))
            return await super().parse(*args)
    config=Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'isolated.sqlite3'))
    judge=Judge(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key'))
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[bad,good]))
    client=TestClient(create_app(config,provider,semantic_judge=judge))
    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    response=client.post('/v1/chat',headers=headers,json={'message':'你店里怎么样？'})
    assert response.status_code==200
    assert response.json()['reply']==good and response.json()['semantic_review']['calls']==2
    messages=client.get('/v1/session').json()['messages']
    assert bad not in str(messages) and messages[-1]['content']==good
    assert len(requests)==provider.generate.await_count==2


@pytest.mark.parametrize('http_status,expected',[(400,'invalid_request'),(401,'authentication_failed'),
                                              (403,'permission_denied'),(429,'rate_limit'),(503,'upstream_unavailable')])
def test_http_failures_have_safe_distinct_codes(http_status,expected):
    def handler(request):
        return httpx2.Response(http_status,json={'error':{'message':'secret-upstream-content'}})
    async def check():
        judge=ModelAnalysisProvider(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-key'),
                                    httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        return await review_reply(judge,'我今年28岁。',[],[{'id':'C01'}])
    outcome=asyncio.run(check())
    assert outcome.status=='unavailable' and outcome.failure==expected
    assert 'secret-upstream' not in str(outcome)


def test_reviews_share_one_total_budget_and_scene_feedback_is_explicit(monkeypatch):
    from types import SimpleNamespace
    from app import reply_pipeline as pipeline
    from app.semantic_review import Review,ReviewOutcome
    from app.dialogue import FALLBACK
    bad='店里具体的情况我没办法确定，也没收到什么新的消息。'
    accepted=Review(decision='accept',confidence=.95,segments=[{'text':bad,'kind':'assertion',
        'verdict':'supported','evidence_ids':['role_profile'],'reason':'evidence_supports'}])
    budgets=[]
    async def judge(*args,timeout):
        budgets.append(timeout)
        return ReviewOutcome('accept',accepted)
    clock=iter([0,3,3,8])
    monkeypatch.setattr(pipeline,'monotonic',lambda:next(clock))
    monkeypatch.setattr(pipeline,'review_reply',judge)
    provider=SimpleNamespace(generate=AsyncMock(return_value=bad))
    reply,guarded,status=asyncio.run(pipeline.generate_checked(provider,[],'prompt','店里怎么样',[],None,None,{},judge=object()))
    assert budgets==[8,5] and reply==FALLBACK and status['calls']==2
    rewrite_prompt=provider.generate.call_args_list[1].args[1]
    assert bad in rewrite_prompt and 'missing_evidence' in rewrite_prompt


def test_exhausted_shared_review_budget_prevents_a_second_call(monkeypatch):
    from types import SimpleNamespace
    from app import reply_pipeline as pipeline
    from app.semantic_review import Review,ReviewOutcome
    from app.dialogue import FALLBACK
    bad='柜台旁多了三箱诗集。'
    result=Review(decision='revise',confidence=.95,segments=[{'text':bad,'kind':'assertion',
        'verdict':'unsupported','evidence_ids':[],'reason':'missing_evidence'}])
    clock=iter([0,8])
    monkeypatch.setattr(pipeline,'monotonic',lambda:next(clock))
    reviewer=AsyncMock(return_value=ReviewOutcome('revise',result))
    monkeypatch.setattr(pipeline,'review_reply',reviewer)
    provider=SimpleNamespace(generate=AsyncMock(return_value=bad))
    reply,_,status=asyncio.run(pipeline.generate_checked(provider,[],'prompt','你好',[],None,None,{},judge=object()))
    assert reply==FALLBACK and status['failure']=='timeout' and reviewer.await_count==1

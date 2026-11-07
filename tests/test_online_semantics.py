import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock,Mock
import httpx2
import openai
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.config import Settings
from app.main import create_app
from app.dialogue import FALLBACK,ProviderFailure
from app.memory_routing import route_memory,RouteDecision
from app.semantic_review import Review,Segment,review_reply,evidence_bundle,needs_review,ModelAnalysisProvider


def run(awaitable):return asyncio.run(awaitable)
def history(query,previous=None):
    return ([{'role':'user','content':previous}] if previous else [])+[{'role':'user','content':query}]

def review(text,verdict='supported',ids=None,kind='assertion',decision=None,confidence=.95):
    reason={'supported':'evidence_supports','unsupported':'missing_evidence','contradicted':'contradiction',
            'uncertain':'uncertain','not_applicable':'nonfactual'}[verdict]
    return {'decision':decision or ('accept' if verdict in ('supported','not_applicable') else 'abstain' if verdict=='uncertain' else 'revise'),
            'confidence':confidence,'segments':[{'text':text,'kind':kind,'verdict':verdict,
            'evidence_ids':ids if ids is not None else ['C01'] if verdict=='supported' else [],'reason':reason}]}

def client_for(tmp_path,provider=None,judge=None,router=None,**config):
    app=create_app(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///'+str(tmp_path/'local.sqlite3'),**config),
                   provider,memory_router=router,semantic_judge=judge)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    return c,h

def send(c,h,message):return c.post('/v1/chat',headers=h,json={'message':message})
def enable(c,h,on=True):
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':on,'timezone':'Asia/Tokyo'}).status_code==200

def remember(c,h,fact):
    m=c.post('/v1/memories',headers=h,json={'fact':fact}).json()['item']
    r=c.patch('/v1/memories/'+m['id'],headers=h,json={'version':m['version'],'confirm':True})
    assert r.status_code==200
    return r.json()['item']


@pytest.mark.parametrize('query,expected',[
    ('你好',False),('解释一下向量数据库',False),('我今天很难过',False),('我明天有面试',False),
    ('我以前学过画画，今天只想休息',False),('别翻旧账，你记得我的名字吗？',False),
    ('护照号码一般有几位？',False),('住在北京需要注意什么？',False),
    ('我现在住在合成青禾市，明天天气怎么样？',False),
    ('不要检索长期记忆，告诉我我的名字',False),('别用长期记忆，我的名字是什么？',False),('不要翻旧账，记得我的猫吗？',False),('我想知道你叫什么',False),
    ('我的名字是什么？',True),('我住哪儿？',True),('还记得我的猫叫什么吗？',True),
    ('上次那个面试后来怎么样了',True),('结合我以前的经历帮我想想',True),
])
def test_local_routing_does_not_call_model(query,expected):
    router=SimpleNamespace(decide=AsyncMock())
    result=run(route_memory(query,history(query),enabled=True,router=router))
    assert result.need_memory==expected
    router.decide.assert_not_called()


def test_consent_recent_context_and_assistant_not_evidence():
    q='我的名字是什么？'
    assert not run(route_memory(q,history(q),enabled=False)).need_memory
    assert not run(route_memory(q,history(q,'我叫合成若竹'),enabled=True)).need_memory
    h=[{'role':'assistant','content':'你叫合成若竹'},{'role':'user','content':q}]
    assert run(route_memory(q,h,enabled=True)).need_memory
    assert run(route_memory('解释数据库',history('解释数据库'),enabled=True,routing_enabled=False)).need_memory
    assert not run(route_memory('不要使用长期记忆',history('不要使用长期记忆'),enabled=True,routing_enabled=False)).need_memory


@pytest.mark.parametrize('output,expected',[
    ({'need_memory':True,'query':'我的面试经历','reason':'personal_history_needed','confidence':.9},True),
    ({'need_memory':True,'query':'我的面试经历','reason':'personal_history_needed','confidence':.2},False),
    ({'need_memory':True,'query':'','reason':'personal_history_needed','confidence':.9},False),
    ({'need_memory':False,'query':'','reason':'uncertain','confidence':.8},False),
    ({'need_memory':True,'query':'x'*201,'reason':'personal_history_needed','confidence':.9},False),
])
def test_ambiguous_routing_is_bounded_and_validated(output,expected):
    router=SimpleNamespace(decide=AsyncMock(return_value=output));q='你觉得什么适合我？'
    assert run(route_memory(q,history(q),enabled=True,router=router)).need_memory==expected
    assert router.decide.await_count==1


def test_router_error_or_timeout_does_not_retrieve():
    q='你觉得什么适合我？'
    for method in [AsyncMock(side_effect=ValueError('private')),AsyncMock(side_effect=asyncio.TimeoutError())]:
        r=run(route_memory(q,history(q),enabled=True,router=SimpleNamespace(decide=method)))
        assert not r.need_memory and r.source=='unavailable'


def test_no_retrieval_call_for_current_context_or_decline(tmp_path):
    c,h=client_for(tmp_path);enable(c,h);m=remember(c,h,'我叫合成若竹')
    store=c.app.state.memory_store
    original=store.retrieve;store.retrieve=Mock(wraps=original)
    for q in ('你好','我今天很累','解释向量数据库','别翻旧账，你记得我的名字吗？'):
        assert send(c,h,q).status_code==200
    assert store.retrieve.call_count==0
    result=send(c,h,'我的名字是什么？').json()
    assert result['retrieved_memory_ids']==[m['id']] and store.retrieve.call_count==1
    assert result['memory_route']['need_memory']
    send(c,h,'我叫合成当前名')
    result=send(c,h,'我的名字是什么？').json()
    assert result['memory_route']['reason']=='recent_context' and store.retrieve.call_count==1


@pytest.mark.parametrize('failure',['bad_id','incomplete','low_confidence','abstain','malformed','timeout'])
def test_review_fails_closed(failure):
    text='我今年28岁。';output=review(text)
    if failure=='bad_id':output['segments'][0]['evidence_ids']=['not-exposed']
    elif failure=='incomplete':output['segments'][0]['text']='我今年'
    elif failure=='low_confidence':output['confidence']=.2
    elif failure=='abstain':output=review(text,'uncertain')
    elif failure=='malformed':output['decision']='sure'
    judge=SimpleNamespace(review=AsyncMock(return_value=output,side_effect=asyncio.TimeoutError() if failure=='timeout' else None))
    status,result=run(review_reply(judge,text,history('你好'),[{'id':'C01'}]))
    assert status in ('unavailable','uncertain')
    if status=='unavailable':assert result is None
    else:assert result.decision=='abstain' or result.confidence<.7


def test_accept_cannot_hide_bad_verdict_or_invalid_reason():
    for output in [review('错误','unsupported',decision='accept'),review('错误',ids=[]),
                   {**review('正确'),'segments':[{**review('正确')['segments'][0],'reason':'missing_evidence'}]}]:
        with pytest.raises(ValidationError):Review.model_validate(output)


def test_evidence_excludes_assistant_facts_and_projects_tools():
    h=[{'role':'user','content':'我叫合成若竹'},{'role':'assistant','content':'虚构过去'},{'role':'user','content':'你好'}]
    bundle=evidence_bundle(h,[{'id':'m','fact':'我住在合成青禾市','event_date':None}],
                           {'status':'ok','temperature_c':6,'secret_internal':'omit'},None)
    text=json.dumps(bundle,ensure_ascii=False)
    assert '虚构过去' not in text and 'secret_internal' not in text
    assert 'memory_m' in text and 'user_0' in text and 'user_2' in text
    assert not needs_review('嗯，我在听。',evidence=[],weather=None,mood=None)
    assert needs_review('嗯，我在听。',evidence=[1],weather=None,mood=None)
    assert needs_review('柜台旁多了三箱诗集。',evidence=[],weather=None,mood=None)


@pytest.mark.parametrize('second_safe',[True,False])
def test_semantic_miss_is_rewritten_once_then_rechecked(tmp_path,second_safe):
    bad='柜台旁多了三箱诗集。';good='你愿意聊聊喜欢的书吗？'
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[bad,good if second_safe else bad]))
    judge=SimpleNamespace(review=AsyncMock(side_effect=[review(bad,'unsupported'),
          review(good,'not_applicable',kind='question') if second_safe else review(bad,'unsupported')]))
    c,h=client_for(tmp_path,provider,judge)
    result=send(c,h,'你好').json()
    assert result['reply']==(good if second_safe else FALLBACK)
    assert result['guarded'] and provider.generate.await_count==judge.review.await_count==2
    assert c.get('/v1/session').json()['messages'][-1]['content']==result['reply']
    assert bad not in str(c.get('/v1/session').json()['messages'])


def test_valid_semantics_can_override_lexical_false_positive(tmp_path):
    text='要是这会儿店里很安静，我们再聊聊书。'
    provider=SimpleNamespace(generate=AsyncMock(return_value=text))
    judge=SimpleNamespace(review=AsyncMock(return_value=review(text,'not_applicable',kind='conditional')))
    c,h=client_for(tmp_path,provider,judge)
    assert send(c,h,'你好').json()['reply']==text
    assert provider.generate.await_count==judge.review.await_count==1


def test_judge_cannot_override_hard_canon_guard(tmp_path):
    text='我今年19岁。'
    provider=SimpleNamespace(generate=AsyncMock(return_value=text))
    judge=SimpleNamespace(review=AsyncMock(return_value=review(text)))
    c,h=client_for(tmp_path,provider,judge)
    assert send(c,h,'你好').json()['reply']==FALLBACK
    assert provider.generate.await_count==judge.review.await_count==2


def test_judge_error_is_bounded_and_draft_not_saved(tmp_path):
    provider=SimpleNamespace(generate=AsyncMock(return_value='我记得你的猫叫合成松饼。'))
    judge=SimpleNamespace(review=AsyncMock(side_effect=ValueError('private-error-key')))
    c,h=client_for(tmp_path,provider,judge)
    r=send(c,h,'你好');assert r.status_code==200
    assert r.json()['reply']==FALLBACK and 'private-error' not in r.text
    assert provider.generate.await_count==judge.review.await_count==1
    assert '合成松饼' not in str(c.get('/v1/session').json()['messages'])


def test_epoch_change_during_review_revokes_output(tmp_path):
    provider=SimpleNamespace(generate=AsyncMock(return_value='你想聊聊书吗？'))
    judge=SimpleNamespace(review=AsyncMock())
    c,h=client_for(tmp_path,provider,judge);enable(c,h)
    uid=next(iter(c.app.state.sessions.values())).user_id
    async def revoke(reply,history,evidence):
        c.app.state.memory_store.configure(uid,False,'Asia/Tokyo')
        return review(reply,'not_applicable',kind='question')
    judge.review.side_effect=revoke
    assert send(c,h,'你好').status_code==409
    assert c.get('/v1/session').json()['messages']==[]


@pytest.mark.parametrize('provider_name',['gemini','openai'])
def test_real_sdk_structured_protocol_with_memory_transport(provider_name):
    seen=[]
    def handler(request):
        p=json.loads(request.content);seen.append(p)
        schema=p['response_format']['json_schema']['name']
        content=({'need_memory':True,'query':'我的经历','reason':'personal_history_needed','confidence':.9}
                 if schema=='RouteDecision' else {'confidence':.95,'role_issues':[],'units':[{'id':'u0','kind':'assertion','verdict':'supported','evidence_ids':['C01']}]} )
        return httpx2.Response(200,json={'id':'test','object':'chat.completion','created':0,'model':'test',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(content)}}]})
    # A fresh transport client is used for each call (SDK closes it).
    async def checks():
        settings=Settings(_env_file=None,chat_provider=provider_name,gemini_api_key='test-gemini',openai_api_key='test-openai')
        a=ModelAnalysisProvider(settings,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        result=await a.decide('什么适合我',history('什么适合我'));assert result.need_memory
        b=ModelAnalysisProvider(settings,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        result=await b.review('我今年28岁。',history('你好'),[{'id':'C01'}]);assert result.decision=='accept'
    run(checks())
    assert len(seen)==2 and seen[0]['temperature']==seen[1]['temperature']==0
    assert seen[0]['max_tokens']==500 and seen[1]['max_tokens']==700


def test_epoch_change_during_router_prevents_retrieval(tmp_path):
    router=SimpleNamespace(decide=AsyncMock());c,h=client_for(tmp_path,router=router);enable(c,h)
    store=c.app.state.memory_store;store.retrieve=Mock(wraps=store.retrieve)
    uid=next(iter(c.app.state.sessions.values())).user_id
    async def revoke(query,recent):
        store.configure(uid,False,'Asia/Tokyo')
        return {'need_memory':True,'query':'我的经历','reason':'personal_history_needed','confidence':.9}
    router.decide.side_effect=revoke
    assert send(c,h,'什么适合我？').status_code==409
    store.retrieve.assert_not_called()
    assert c.get('/v1/session').json()['messages']==[]


def test_generation_failure_after_revise_does_not_save_draft(tmp_path):
    text='柜台旁多了三箱诗集。'
    provider=SimpleNamespace(generate=AsyncMock(side_effect=[text,ProviderFailure('rate_limit','稍后重试',429)]))
    judge=SimpleNamespace(review=AsyncMock(return_value=review(text,'unsupported')))
    c,h=client_for(tmp_path,provider,judge)
    assert send(c,h,'你好').status_code==429
    assert c.get('/v1/session').json()['messages']==[]
    assert provider.generate.await_count==2 and judge.review.await_count==1


def test_actual_auxiliary_timeouts_are_cancelled():
    async def slow(*args):await asyncio.sleep(1)
    q='什么适合我？'
    result=run(route_memory(q,history(q),enabled=True,router=SimpleNamespace(decide=slow),timeout=.01))
    assert not result.need_memory and result.source=='unavailable'
    status,_=run(review_reply(SimpleNamespace(review=slow),'我今年28岁。',history('你好'),[],timeout=.01))
    assert status=='unavailable'


def test_lightweight_wire_cannot_bypass_domain_validation():
    from app.semantic_review import IndexedReview
    settings=Settings(_env_file=None,chat_provider='mock')
    for invalid in [
        {'confidence':.95,'role_issues':[],'units':[]},
        {'confidence':.95,'role_issues':[],'units':[{'id':'u0','kind':'assertion','verdict':'supported','evidence_ids':[]}]},
        {'confidence':.95,'role_issues':[],'units':[{'id':'u0','kind':'nonfactual','verdict':'supported','evidence_ids':['C01']}]},
    ]:
        provider=ModelAnalysisProvider(settings)
        provider.parse=AsyncMock(return_value=IndexedReview.model_validate(invalid))
        with pytest.raises((ValidationError,ValueError,KeyError)):
            run(provider.review('错误',history('你好'),[{'id':'C01'}]))


@pytest.mark.parametrize('status',[400,429])
def test_auxiliary_sdk_errors_fail_closed_without_retries(status):
    count=0
    def handler(request):
        nonlocal count
        count+=1
        return httpx2.Response(status,json={'error':{'message':'private-upstream-token','type':'bad_request','code':status}})
    async def check():
        settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='test-private')
        provider=ModelAnalysisProvider(settings,httpx2.AsyncClient(transport=httpx2.MockTransport(handler)))
        outcome,result=await review_reply(provider,'我今年28岁。',history('你好'),[{'id':'C01'}])
        assert outcome=='unavailable' and result is None
    run(check());assert count==1


def test_only_insignificant_sentence_whitespace_is_normalized():
    original='你想聊聊书吗？\n\n你可以慢慢说。'
    segments=review('你想聊聊书吗？你可以慢慢说。','not_applicable',kind='suggestion')
    judge=SimpleNamespace(review=AsyncMock(return_value=segments))
    outcome=run(review_reply(judge,original,history('你好'),[]))
    assert outcome.status=='accept'
    for original,changed in [('你住在New Willow City。','你住在NewWillow City。'),
                             ('你住在合成青禾市。','你住在青禾市。')]:
        judge.review.return_value=review(changed,ids=['C01'])
        outcome=run(review_reply(judge,original,history('你好'),[{'id':'C01'}]))
        assert outcome.failure=='incomplete_coverage'


@pytest.mark.parametrize('verdict,kind,expected',[('unsupported','assertion','revise'),('not_applicable','nonfactual','accept')])
def test_provider_decision_and_reason_are_derived_from_validated_labels(verdict,kind,expected):
    from app.semantic_review import IndexedReview
    wire=IndexedReview(confidence=.95,role_issues=[],units=[{'id':'u0','kind':kind,'verdict':verdict,'evidence_ids':[]}])
    provider=ModelAnalysisProvider(Settings(_env_file=None,chat_provider='mock'))
    provider.parse=AsyncMock(return_value=wire)
    result=run(provider.review('合成内容',history('你好'),[]))
    assert result.decision==expected
    assert result.segments[0].reason==('missing_evidence' if verdict=='unsupported' else 'nonfactual')


def test_transport_rejects_unknown_labels_or_model_supplied_decisions():
    from app.semantic_review import IndexedReview
    for data in [
        {'confidence':.9,'role_issues':[],'units':[{'id':'u0','kind':'invented','verdict':'supported','evidence_ids':['C01']}]},
        {'decision':'accept','confidence':.9,'role_issues':[],'units':[]},
    ]:
        with pytest.raises(ValidationError):IndexedReview.model_validate(data)


def test_role_profile_cannot_prove_current_shop_message_activity(tmp_path):
    text='店里具体的情况我没办法确定，也没收到什么新的消息。'
    provider=SimpleNamespace(generate=AsyncMock(return_value=text))
    # Reproduces a real synthetic misjudgment: citing identity does not turn a
    # factual dynamic-scene claim into evidence-backed current state.
    judge=SimpleNamespace(review=AsyncMock(return_value=review(text,ids=['role_profile'])))
    c,h=client_for(tmp_path,provider,judge)
    result=send(c,h,'你店里今天安静吗？').json()
    assert result['reply']==FALLBACK and result['guarded']
    assert provider.generate.await_count==judge.review.await_count==2

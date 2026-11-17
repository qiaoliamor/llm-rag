"""Stage reservation and total deadline contracts; no wall-clock waits or live APIs."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
import os
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.config import Settings
from app.memory_understanding import (MemoryCallBudget, ModelMemoryUnderstanding, MemoryPlan,
    EvidenceSelection, MemoryMetadata, PLAN_PROMPT, PLAN_PROMPT_V3, SELECT_PROMPT, SELECT_PROMPT_V3, SELECT_PROMPT_V5, PLAN_PROMPT_V5)
from app.main import create_app
from app.progression import Bond
from test_understanding import plan, proposal


def test_plan_consuming_old_shared_budget_still_reserves_full_selection_stage():
    now=[0.]
    b=MemoryCallBudget.start(Settings(_env_file=None),clock=lambda:now[0])
    now[0]=2.558
    assert 4-now[0]==pytest.approx(1.442)  # Historical short remainder, not a fresh API call.
    assert b.plan_seconds==8 and b.selection_timeout()==8 and b.deadline==16
    now[0]=6.003
    assert b.selection_timeout()==8  # Historical plan timeout no longer consumes the selection reservation.
    now[0]=14.;assert b.selection_timeout()==2
    now[0]=17.;assert b.selection_timeout()==0


@pytest.mark.parametrize('field',['memory_understanding_timeout_seconds','memory_selection_timeout_seconds'])
@pytest.mark.parametrize('value',[0,11,float('inf'),float('nan')])
def test_stage_configuration_is_finite_and_bounded(field,value):
    with pytest.raises(ValidationError):Settings(_env_file=None,**{field:value})


def test_sdk_selection_uses_own_cap_not_plan_cap(monkeypatch):
    calls=[]
    async def parse(self,schema,prompt,data,timeout,tokens):
        calls.append((schema,timeout));return plan() if schema is MemoryPlan else {'ids':[],'confidence':.95}
    monkeypatch.setattr('app.semantic_review.ModelAnalysisProvider.parse',parse)
    async def run():
        p=ModelMemoryUnderstanding(Settings(_env_file=None,memory_understanding_timeout_seconds=2,memory_selection_timeout_seconds=7))
        await p.analyze({});await p.select({})
    asyncio.run(run())
    assert calls==[(MemoryPlan,2),(EvidenceSelection,7)]
    assert len(PLAN_PROMPT)<len(PLAN_PROMPT_V3)/2
    assert len(SELECT_PROMPT)<len(SELECT_PROMPT_V3)/2
    assert not PLAN_PROMPT.startswith(PLAN_PROMPT_V3)


@pytest.fixture(params=['sqlite','postgres'])
def context(request,tmp_path,monkeypatch):
    url=os.environ.get('TEST_POSTGRES_URL') if request.param=='postgres' else 'sqlite:///'+str(tmp_path/'budget.sqlite3')
    if not url:pytest.skip('requires script-created temporary PostgreSQL')
    clock=[0.];monkeypatch.setattr('app.memory_understanding.monotonic',lambda:clock[0])
    analyst=SimpleNamespace(analyze=AsyncMock(),select=AsyncMock())
    reply='うん、聞いているよ。'
    judge=SimpleNamespace(review=AsyncMock(return_value={'decision':'accept','confidence':.95,'role_issues':[],
        'segments':[{'text':reply,'kind':'nonfactual','verdict':'not_applicable','evidence_ids':[],'reason':'nonfactual'}]}))
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',memory_database_url=url,
        dialogue_mode='companion',growth_enabled=True,memory_understanding_mode='semantic',reply_understanding_mode='semantic',
        weather_understanding_mode='semantic',emotion_understanding_mode='semantic')
    provider=SimpleNamespace(generate=AsyncMock(return_value=reply))
    app=create_app(settings,provider,memory_understander=analyst,semantic_judge=judge)
    with TestClient(app) as c:
        h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
        uid=next(iter(app.state.sessions.values())).user_id
        with app.state.memory_store.db.begin() as db:db.get(Bond,(uid,'shen_yan')).score=30
        assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True}).status_code==200
        store=app.state.memory_store
        m=store.candidate(uid,'私の名前は合成葵です。','synthetic',store.settings(uid)['epoch'],manual=True,metadata=MemoryMetadata('profile','name'))
        m=store.mutate(uid,m['id'],m['version'],confirm=True)
        async def analyze(data):
            clock[0]=2.558
            return plan(need=True,query='名前',target_slots=['name'])
        analyst.analyze.side_effect=analyze;analyst.select.return_value={'ids':[m['id']],'confidence':.95}
        yield SimpleNamespace(c=c,h=h,store=store,mid=m['id'],analyst=analyst,clock=clock,provider=provider,judge=judge)
    store.engine.dispose()


def test_actual_chat_reserves_selection_time_and_injects_confirmed_memory(context,monkeypatch):
    from app import main
    original=main.select_evidence;observed=[]
    async def selection(*args,**kw):
        observed.append(kw['timeout']);return await original(*args,**kw)
    monkeypatch.setattr(main,'select_evidence',selection)
    x=context;r=x.c.post('/v1/chat',headers=x.h,json={'message':'私の名前は？','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[x.mid]
    assert observed==[8]
    x.analyst.analyze.assert_awaited_once();x.analyst.select.assert_awaited_once()


def test_total_budget_consumed_by_local_retrieval_does_not_start_selection(context,monkeypatch):
    x=context;original=x.store.semantic_candidates
    def delayed(*a,**kw):
        value=original(*a,**kw);x.clock[0]=17;return value
    monkeypatch.setattr(x.store,'semantic_candidates',delayed)
    r=x.c.post('/v1/chat',headers=x.h,json={'message':'私の名前は？','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[]
    x.analyst.select.assert_not_awaited()


def test_selection_failure_is_not_retried_and_does_not_inject_old_memory(context):
    x=context;x.analyst.select.side_effect=TimeoutError('synthetic')
    r=x.c.post('/v1/chat',headers=x.h,json={'message':'私の名前は？','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[]
    x.analyst.select.assert_awaited_once()


def test_empty_selection_does_not_override_explicit_player_fact_and_rewrites_once(context):
    from app.memory_understanding import EMPTY_MEMORY_CONTEXT
    x=context
    bad='犬は飼っていなかったはずだけど……新しい家族を迎えたのかな？'
    good='名前、聞かせて。'
    x.analyst.select.return_value={'ids':[],'confidence':.95}
    x.provider.generate.side_effect=[bad,good]
    x.judge.review.side_effect=[
        {'decision':'revise','confidence':.95,'role_issues':[],
         'segments':[{'text':bad,'kind':'assertion','verdict':'unsupported','evidence_ids':[],'reason':'missing_evidence'}]},
        {'decision':'accept','confidence':.95,'role_issues':[],
         'segments':[{'text':good,'kind':'nonfactual','verdict':'not_applicable','evidence_ids':[],'reason':'nonfactual'}]}]
    r=x.c.post('/v1/chat',headers=x.h,json={'message':'犬を飼っている。名前を覚えてる？','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['reply']==good and r.json()['guarded']
    assert r.json()['retrieved_memory_ids']==[]
    assert x.provider.generate.await_count==x.judge.review.await_count==2
    assert EMPTY_MEMORY_CONTEXT in x.provider.generate.call_args_list[0].args[1]


@pytest.mark.parametrize('text,locale',[('我不喝咖啡。','zh-CN'),('コーヒーは飲まない。','ja-JP')])
def test_explicit_negative_preference_preserves_source_and_requires_confirmation(context,text,locale):
    # The model interpretation is authored; this verifies admission/confirmation, not actual semantics.
    x=context;x.analyst.analyze.side_effect=None
    x.analyst.analyze.return_value=plan(proposal(text,category='preference',slot='preference'))
    r=x.c.post('/v1/chat',headers=x.h,json={'message':text,'locale':locale})
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[]
    m=r.json()['memory_candidates'][0]
    assert m['fact']==text and m['status']=='candidate'
    uid=next(iter(x.c.app.state.sessions.values())).user_id
    assert all(item['id']!=m['id'] for item in x.store.semantic_candidates(
        uid,'咖啡' if locale=='zh-CN' else 'コーヒー',target_slots=['preference']))
    changed=x.c.patch('/v1/memories/'+m['id'],headers=x.h,json={'version':m['version'],'confirm':True})
    assert changed.status_code==200 and changed.json()['item']['status']=='confirmed'
    assert changed.json()['item']['fact']==text
    assert any(item['id']==m['id'] and item['fact']==text for item in x.store.semantic_candidates(
        uid,'咖啡' if locale=='zh-CN' else 'コーヒー',target_slots=['preference']))


def test_selection_v6_is_shorter_and_query_v5_is_preserved():
    assert PLAN_PROMPT==PLAN_PROMPT_V5
    assert len(SELECT_PROMPT)<len(SELECT_PROMPT_V5)
    assert SELECT_PROMPT.startswith('same-language-memory-v6')

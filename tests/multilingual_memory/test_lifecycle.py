"""End-to-end semantic memory flow in disposable SQLite/PostgreSQL only."""
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.memory import MemoryStore
from app.progression import Bond
from app.memory_understanding import MemoryMetadata, MEMORY_CONTEXT_RULES
from test_understanding import plan, proposal, date_spec

NOW=datetime(2026,11,11,0,tzinfo=timezone.utc)


@pytest.fixture(params=['sqlite','postgres'])
def env(request,tmp_path,monkeypatch):
    url=os.environ.get('TEST_POSTGRES_URL') if request.param=='postgres' else 'sqlite:///'+str(tmp_path/'semantic.sqlite3')
    if not url:pytest.skip('requires independent temporary PostgreSQL')
    monkeypatch.setattr('app.memory_understanding.local_now',lambda tz:NOW)
    monkeypatch.setattr('app.memory.utcnow',lambda:NOW.replace(tzinfo=None))
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=plan()),select=AsyncMock(return_value={'ids':[],'confidence':.95}))
    provider=SimpleNamespace(generate=AsyncMock(return_value='うん、ゆっくり話してね。'))
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',dialogue_mode='companion',growth_enabled=True,
        memory_understanding_mode='semantic',memory_database_url=url)
    app=create_app(settings,provider,memory_understander=analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    return SimpleNamespace(app=app,c=c,h=h,uid=uid,store=app.state.memory_store,analyst=analyst,provider=provider,url=url,settings=settings)


def enable(e,score=30):
    with e.store.db.begin() as db:db.get(Bond,(e.uid,'shen_yan')).score=score
    if score>=30:assert e.c.patch('/v1/settings',headers=e.h,json={'memory_enabled':True,'timezone':'Asia/Tokyo'}).status_code==200


def chat(e,message,locale='ja-JP'):
    return e.c.post('/v1/chat',headers=e.h,json={'message':message,'locale':locale})


def items(e):return e.c.get('/v1/memories').json()['items']


def test_distinct_original_names_require_explicit_replacement(env):
    e=env;enable(e)
    for text in ('私の名前はA-Bです。','私の名前はABです。'):
        e.analyst.analyze.return_value=plan(proposal(text,category='profile',slot='name'))
        response=chat(e,text)
        assert response.status_code==200
        candidates=response.json()['memory_candidates']
        assert len(candidates)==1
        m=candidates[0]
        assert m['fact']==text
        if text=='私の名前はA-Bです。':
            old_id=m['id']
            assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'confirm':True}).status_code==200
    assert m['id']!=old_id
    current=next(x for x in items(e) if x['id']==m['id'])
    assert current['conflicts']==[old_id]
    path='/v1/memories/'+m['id']
    assert e.c.patch(path,headers=e.h,json={'version':m['version'],'confirm':True}).status_code==409
    assert e.c.patch(path,headers=e.h,json={'version':m['version'],'confirm':True,'replace_conflicts':True}).status_code==200
    assert [(x['id'],x['fact'],x['status']) for x in items(e)]==[(m['id'],'私の名前はABです。','confirmed')]
    assert old_id not in [x['id'] for x in e.store.semantic_candidates(e.uid,'名前',target_slots=['name'])]


@pytest.mark.parametrize('message,expression,locale',[
    ('明日、合成東京で面接があります。','明日','ja-JP'),
    ('我明天在合成北京市有面试。','明天','zh-CN'),
])
def test_cross_session_confirmation_retrieval_correction_delete_and_no_revival(env,message,expression,locale):
    e=env;enable(e)
    e.analyst.analyze.return_value=plan(proposal(message,date_spec('relative_days',expression,days=1)))
    r=chat(e,message,locale)
    assert r.status_code==200 and r.json()['memory_understanding']['status']=='ready'
    m=items(e)[0]
    assert m['fact']==message and m['event_date']=='2026-11-12' and m['status']=='candidate'
    assert r.json()['retrieved_memory_ids']==[]
    query='面接の日を覚えてる？' if locale=='ja-JP' else '还记得我的面试日期吗？'
    keyword='面接' if locale=='ja-JP' else '面试'
    e.analyst.analyze.return_value=plan(need=True,query=keyword)
    assert chat(e,query,locale).json()['retrieved_memory_ids']==[]  # unconfirmed never used
    e.analyst.select.assert_not_awaited()
    assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'confirm':True}).status_code==200
    confirmed=items(e)[0]
    assert confirmed['event_date']=='2026-11-12'  # confirmation does not reinterpret relative dates
    new=create_app(e.settings,e.provider,memory_understander=e.analyst)
    fresh=TestClient(new);fresh.cookies.update(e.c.cookies)
    session=fresh.get('/v1/session').json();e.c=fresh;e.h={'x-csrf-token':session['csrf_token']}
    assert session['messages']==[] and items(e)[0]['fact']==message
    e.analyst.select.return_value={'ids':[m['id']],'confidence':.95}
    r=chat(e,query,locale)
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[m['id']]
    assert message in e.provider.generate.call_args.args[1]
    assert MEMORY_CONTEXT_RULES in e.provider.generate.call_args.args[1]
    assert 'source_message_id' not in e.provider.generate.call_args.args[1]
    corrected=message.replace(expression,'明後日' if locale=='ja-JP' else '后天')
    new_expression='明後日' if locale=='ja-JP' else '后天'
    e.analyst.analyze.return_value=plan(proposal(corrected,date_spec('relative_days',new_expression,days=2)))
    assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':confirmed['version'],'fact':corrected}).status_code==200
    corrected_item=items(e)[0]
    assert corrected_item['event_date']=='2026-11-13' and corrected_item['fact']==corrected
    assert e.c.get('/v1/session').json()['messages']==[]
    assert e.c.delete('/v1/memories/'+m['id'],headers=e.h,params={'version':corrected_item['version']}).status_code==200
    assert MemoryStore(e.url).list(e.uid)==[]
    assert MemoryStore(e.url).semantic_candidates(e.uid,keyword)==[]
    r=chat(e,corrected,locale)
    assert r.status_code==200 and r.json()['memory_candidates']==[]  # exact deleted fact cannot auto revive
    assert items(e)==[]
    e.analyst.analyze.return_value=plan(proposal(corrected,date_spec('relative_days',new_expression,days=2)))
    assert e.c.post('/v1/memories',headers=e.h,json={'fact':corrected}).status_code==200  # explicit reauthorization
    assert items(e)[0]['status']=='candidate'


@pytest.mark.parametrize('message,reason',[
    ('こんにちは','no_cross_session_need'),('你好','no_cross_session_need'),
    ('今日の話だけ聞いて。','current_context_sufficient'),('我刚才已经说清楚了。','current_context_sufficient'),
])
def test_no_database_retrieval_for_semantically_unneeded_history(env,monkeypatch,message,reason):
    e=env;enable(e);e.analyst.analyze.return_value=plan(reason=reason)
    monkeypatch.setattr(e.store,'retrieve',Mock(side_effect=AssertionError('legacy retrieval forbidden')))
    monkeypatch.setattr(e.store,'semantic_candidates',Mock(side_effect=AssertionError('unneeded retrieval forbidden')))
    monkeypatch.setattr('app.main.extract_candidates',Mock(side_effect=AssertionError('legacy extraction forbidden')))
    r=chat(e,message)
    assert r.status_code==200 and not r.json()['memory_route']['need_memory']
    e.analyst.analyze.assert_awaited_once();e.analyst.select.assert_not_awaited()


def test_authorization_gates_and_structured_decline(env,monkeypatch):
    e=env
    r=chat(e,'覚えてる？')
    assert r.status_code==200 and r.json()['memory_understanding']['status']=='disabled'
    e.analyst.analyze.assert_not_awaited()
    enable(e,29)
    assert e.c.patch('/v1/settings',headers=e.h,json={'memory_enabled':True}).status_code==403
    e.analyst.analyze.assert_not_awaited()
    enable(e)
    e.analyst.analyze.return_value=plan(memory_use='decline',reason='declined')
    monkeypatch.setattr(e.store,'semantic_candidates',Mock(side_effect=AssertionError('declined retrieval')))
    r=chat(e,'記憶を使わず、覚えないで。')
    assert r.status_code==200 and r.json()['memory_understanding']['status']=='declined'
    assert not items(e)
    assert e.c.patch('/v1/settings',headers=e.h,json={'memory_enabled':False}).status_code==200
    before=e.analyst.analyze.await_count;chat(e,'私のこと覚えてる？')
    assert e.analyst.analyze.await_count==before


@pytest.mark.parametrize('failure',['timeout','invalid','invented'])
def test_understanding_failure_keeps_chat_but_not_memory_and_no_regex_fallback(env,monkeypatch,failure):
    e=env;enable(e)
    if failure=='timeout':e.analyst.analyze.side_effect=TimeoutError('synthetic')
    elif failure=='invalid':e.analyst.analyze.return_value={'wrong':'shape'}
    else:e.analyst.analyze.return_value=plan(proposal('我明天在另一座城市面试。'))
    monkeypatch.setattr('app.main.extract_candidates',Mock(side_effect=AssertionError('no fallback')))
    monkeypatch.setattr(e.store,'semantic_candidates',Mock(side_effect=AssertionError('no retrieval on failure')))
    r=chat(e,'我明天有面试。','zh-CN')
    assert r.status_code==200 and r.json()['memory_understanding']['status']=='unavailable'
    assert not r.json()['memory_candidates'] and not r.json()['retrieved_memory_ids'] and not items(e)
    e.analyst.analyze.assert_awaited_once()


def test_no_answer_selection_and_other_user_ids_cannot_enter_context(env):
    e=env;enable(e);epoch=e.store.settings(e.uid)['epoch']
    m=e.store.candidate(e.uid,'明日、東京で面接があります。','synthetic',epoch,manual=True,metadata=MemoryMetadata('event','event',None))
    e.store.mutate(e.uid,m['id'],m['version'],confirm=True)
    other=TestClient(e.app);other.get('/v1/session')
    e.analyst.analyze.return_value=plan(need=True,query='面接')
    e.analyst.select.return_value={'ids':[],'confidence':.95}
    r=chat(e,'面接の予定を覚えてる？')
    assert r.status_code==200 and not r.json()['retrieved_memory_ids']
    e.analyst.select.return_value={'ids':['foreign-user-id'],'confidence':.99}
    r=chat(e,'面接の予定を覚えてる？')
    assert r.status_code==200 and not r.json()['retrieved_memory_ids']
    assert r.json()['memory_understanding']['selection']=='unavailable'
    assert other.get('/v1/memories').json()['items']==[]


def test_revocation_during_understanding_cancels_turn_and_does_not_restore_data(env):
    e=env;enable(e)
    async def revoke(data):
        e.store.configure(e.uid,False,'Asia/Tokyo')
        return plan(proposal('明日、面接です。',date_spec('relative_days','明日',days=1)))
    e.analyst.analyze.side_effect=revoke
    r=chat(e,'明日、面接です。')
    assert r.status_code==409 and r.json()['code']=='memory_changed'
    e.provider.generate.assert_not_awaited()
    assert not items(e) and e.c.get('/v1/session').json()['messages']==[]


def test_manual_metadata_failure_unknown_date_and_version_ownership_checked_before_model(env):
    e=env;enable(e);e.analyst.analyze.side_effect=TimeoutError('synthetic')
    fact='来月、面接があります。'
    assert e.c.post('/v1/memories',headers=e.h,json={'fact':fact}).status_code==200
    m=items(e)[0];assert m['fact']==fact and m['event_date'] is None
    before=e.analyst.analyze.await_count
    assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version']+1,'fact':'別の内容'}).status_code==409
    assert e.analyst.analyze.await_count==before
    other=TestClient(e.app);other_h={'x-csrf-token':other.get('/v1/session').json()['csrf_token']}
    assert other.patch('/v1/memories/'+m['id'],headers=other_h,json={'version':m['version'],'fact':'別の内容'}).status_code==404
    assert e.analyst.analyze.await_count==before
    assert e.c.post('/v1/memories',json={'fact':fact}).status_code==403
    assert e.analyst.analyze.await_count==before


def test_generation_failure_never_commits_proposals(env):
    from app.dialogue import ProviderFailure
    e=env;enable(e);e.analyst.analyze.return_value=plan(proposal('明日、面接です。',date_spec('relative_days','明日',days=1)))
    e.provider.generate.side_effect=ProviderFailure('timeout','synthetic',504)
    r=chat(e,'明日、面接です。')
    assert r.status_code==504 and not items(e)
    assert e.c.get('/v1/session').json()['messages']==[]
    e.provider.generate.assert_awaited_once()


def test_production_mode_default_is_semantic(monkeypatch):
    monkeypatch.delenv('MEMORY_UNDERSTANDING_MODE',raising=False)
    assert Settings(_env_file=None).memory_understanding_mode=='semantic'


def test_semantic_appointment_expiry_and_candidate_expiry(env,monkeypatch):
    from app.memory import Memory
    e=env;enable(e)
    text='明日、面接です。';e.analyst.analyze.return_value=plan(proposal(text,date_spec('relative_days','明日',days=1)))
    assert chat(e,text).status_code==200
    m=items(e)[0]
    assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'confirm':True}).status_code==200
    with e.store.db() as db:assert db.get(Memory,m['id']).expires_at==datetime(2026,12,13)
    monkeypatch.setattr('app.memory.utcnow',lambda:datetime(2026,12,14))
    assert e.store.semantic_candidates(e.uid,'面接')==[]
    assert items(e)[0]['expired']
    monkeypatch.setattr('app.memory.utcnow',lambda:NOW.replace(tzinfo=None))
    text='来週火曜日に別の面接です。';e.analyst.analyze.return_value=plan(proposal(text,date_spec('weekday','来週火曜日',week_offset=1,weekday=1)))
    assert chat(e,text).status_code==200
    m=next(m for m in items(e) if m['status']=='candidate')
    monkeypatch.setattr('app.memory.utcnow',lambda:NOW.replace(tzinfo=None)+timedelta(hours=25))
    assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'confirm':True}).status_code==409


def test_proposals_and_reward_share_failure_rollback(env,monkeypatch):
    e=env;enable(e);growth=e.app.state.progression
    with e.store.db.begin() as db:db.get(Bond,(e.uid,'shen_yan')).last_turn=NOW.replace(tzinfo=None)
    growth.clock=lambda:NOW.replace(tzinfo=None)+timedelta(seconds=60)
    original=growth.snapshot
    def fail(db,account,bond):
        if bond.score>30:raise RuntimeError('synthetic transaction failure')
        return original(db,account,bond)
    e.analyst.analyze.return_value=plan(proposal('明日、面接です。',date_spec('relative_days','明日',days=1)))
    with monkeypatch.context() as patch:
        patch.setattr(growth,'snapshot',fail)
        client=TestClient(e.app,raise_server_exceptions=False);client.cookies.update(e.c.cookies)
        assert client.post('/v1/chat',headers=e.h,json={'message':'明日、面接です。','locale':'ja-JP'}).status_code==500
    assert not items(e)
    assert e.c.get('/v1/session').json()['messages']==[]
    assert growth.get(e.uid)['character']['score']==30


def test_same_relative_original_on_another_day_proposes_new_date_without_rewriting_old(env,monkeypatch):
    e=env;enable(e);text='明日、面接です。'
    e.analyst.analyze.return_value=plan(proposal(text,date_spec('relative_days','明日',days=1)))
    assert chat(e,text).status_code==200
    old=items(e)[0]
    assert e.c.patch('/v1/memories/'+old['id'],headers=e.h,json={'version':old['version'],'confirm':True}).status_code==200
    monkeypatch.setattr('app.memory_understanding.local_now',lambda tz:NOW+timedelta(days=1))
    monkeypatch.setattr('app.memory.utcnow',lambda:NOW.replace(tzinfo=None)+timedelta(days=1))
    r=chat(e,text)
    assert r.status_code==200 and len(r.json()['memory_candidates'])==1
    rows=items(e)
    assert len(rows)==2 and all(m['fact']==text for m in rows)
    assert {(m['event_date'],m['status']) for m in rows}=={('2026-11-12','confirmed'),('2026-11-13','candidate')}


def test_semantic_name_type_hint_retrieves_without_shared_words_and_keeps_owner_filter(env):
    e=env;enable(e)
    original='私は葵です。'
    e.analyst.analyze.return_value=plan(proposal(original,category='profile',slot='name'))
    assert chat(e,original).status_code==200
    m=items(e)[0]
    assert e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'confirm':True}).status_code==200
    e.analyst.analyze.return_value=plan(need=True,query='名前',target_slots=['name'])
    e.analyst.select.return_value={'ids':[m['id']],'confidence':.95}
    r=chat(e,'名前を覚えてる？')
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[m['id']]
    assert original in e.provider.generate.call_args.args[1]


def test_persisted_legacy_appointment_slot_remains_retrievable_without_data_migration(env):
    e=env;enable(e)
    m=e.store.candidate(e.uid,'我下周二有面试。','legacy-synthetic',e.store.settings(e.uid)['epoch'],manual=True,
        metadata=MemoryMetadata('event','event:面试','2026-11-17'))
    e.store.mutate(e.uid,m['id'],m['version'],confirm=True)
    e.analyst.analyze.return_value=plan(need=True,query='面接',target_slots=['appointment'])
    e.analyst.select.return_value={'ids':[m['id']],'confidence':.95}
    r=chat(e,'以前話した面接の予定は？')
    assert r.status_code==200 and r.json()['retrieved_memory_ids']==[m['id']]
    assert items(e)[0]['fact']=='我下周二有面试。'


def test_semantic_personal_query_requests_review_even_with_no_evidence_and_no_chinese_cues(env):
    from app.semantic_review import Review
    e=env;enable(e)
    judge=SimpleNamespace(review=AsyncMock(return_value=Review.model_validate({
        'decision':'accept','confidence':.95,'role_issues':[],
        'segments':[{'text':'よかったら、教えてくれる？','kind':'question','verdict':'not_applicable','evidence_ids':[],'reason':'nonfactual'}]})))
    app=create_app(e.settings,e.provider,memory_understander=e.analyst,semantic_judge=judge)
    client=TestClient(app);client.cookies.update(e.c.cookies)
    h={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
    e.provider.generate.return_value='よかったら、教えてくれる？'
    e.analyst.analyze.return_value=plan(need=True,query='名前',target_slots=['name'])
    r=client.post('/v1/chat',headers=h,json={'message':'名前を覚えてる？','locale':'ja-JP'})
    assert r.status_code==200 and not r.json()['retrieved_memory_ids']
    judge.review.assert_awaited_once()
    assert r.json()['semantic_review']['status']=='accepted'
    judge.review.reset_mock()
    e.analyst.analyze.return_value=plan()
    r=client.post('/v1/chat',headers=h,json={'message':'こんにちは','locale':'ja-JP'})
    assert r.status_code==200 and r.json()['semantic_review']['status']=='skipped'
    judge.review.assert_not_awaited()


def test_locked_existing_memory_edit_cannot_call_metadata_model(env):
    e=env;enable(e)
    m=e.store.candidate(e.uid,'原文の合成記憶。','seed',e.store.settings(e.uid)['epoch'],manual=True,metadata=MemoryMetadata())
    e.store.mutate(e.uid,m['id'],m['version'],confirm=True);m=items(e)[0]
    with e.store.db.begin() as db:db.get(Bond,(e.uid,'shen_yan')).score=29
    r=e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'fact':'変更した原文。'})
    assert r.status_code==403 and r.json()['code']=='ability_locked'
    e.analyst.analyze.assert_not_awaited()
    assert items(e)[0]['fact']=='原文の合成記憶。'
    assert e.c.delete('/v1/memories/'+m['id'],headers=e.h,params={'version':m['version']}).status_code==200


def test_revoked_before_manual_analysis_never_sends_correction(env,monkeypatch):
    e=env;enable(e)
    m=e.store.candidate(e.uid,'原文の合成記憶。','seed',e.store.settings(e.uid)['epoch'],manual=True,metadata=MemoryMetadata())
    e.store.mutate(e.uid,m['id'],m['version'],confirm=True);m=items(e)[0]
    validate=e.store.validate_edit
    def revoke(*args):
        original=validate(*args);e.store.configure(e.uid,False,'Asia/Tokyo');return original
    monkeypatch.setattr(e.store,'validate_edit',revoke)
    r=e.c.patch('/v1/memories/'+m['id'],headers=e.h,json={'version':m['version'],'fact':'変更した原文。'})
    assert r.status_code==409 and r.json()['code']=='memory_disabled'
    e.analyst.analyze.assert_not_awaited()
    assert items(e)[0]['fact']=='原文の合成記憶。'

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app
from app.dialogue import ProviderFailure
from app.progression import Account, Bond, Entry, THRESHOLDS


@pytest.fixture(params=['sqlite','postgres'])
def app(request,tmp_path):
    if request.param=='postgres':
        url=os.environ.get('TEST_POSTGRES_URL')
        if not url:pytest.skip('independent temporary PG only')
    else:url='sqlite:///'+str(tmp_path/'synthetic.sqlite3')
    return create_app(Settings(_env_file=None,chat_provider='mock',weather_provider='mock',
        growth_enabled=True,dialogue_mode='companion',memory_database_url=url))


def boot(app,cookies=None):
    c=TestClient(app)
    if cookies:c.cookies.update(cookies)
    data=c.get('/v1/session').json()
    return c,{'x-csrf-token':data['csrf_token']},data


def token():return str(uuid4())
def gift(c,h,key=None,gift_id='bookmark',character='shen_yan'):
    return c.post('/v1/characters/'+character+'/gifts',headers=h,json={'request_id':key or token(),'gift_id':gift_id})
def credit(c,h,key=None):
    return c.post('/v1/account/demo-credit',headers=h,json={'request_id':key or token()})
def uid(app,c):
    return next(s.user_id for s in app.state.sessions.values()
                if app.state.memory_store.is_owner(s.user_id,c.cookies.get('persona_player')))


def test_new_account_optional_profile_update_clear_and_identity_isolation(app):
    c,h,s=boot(app);other,ho,_=boot(app)
    assert s['account']['coins']==100 and s['account']['character']['score']==0
    assert not any(s['account']['character']['abilities'].values())
    profile={'name':'合成小雨','email':'synthetic@example.invalid','phone':'+81 00000000'}
    r=c.patch('/v1/account/profile',headers=h,json=profile)
    assert r.status_code==200 and r.json()['profile']==profile
    assert other.get('/v1/account').json()['profile']=={'name':'','email':'','phone':''}
    assert c.patch('/v1/account/profile',headers=ho,json=profile).status_code==403
    assert c.patch('/v1/account/profile',json=profile).status_code==403
    again,_,_=boot(app,dict(c.cookies))
    assert again.get('/v1/account').json()['profile']==profile
    assert c.delete('/v1/account/profile',headers=h).json()['coins']==100
    assert again.get('/v1/account').json()['profile']=={'name':'','email':'','phone':''}


@pytest.mark.parametrize('body',[
    {'email':'bad'}, {'phone':'abcde'}, {'name':'x'*41}, {'email':'x'*255},
    {'name':True}, {'coins':999}, {'user_id':'someone-else'},
])
def test_profile_invalid_inputs_cannot_mutate_wallet(app,body):
    c,h,_=boot(app)
    assert c.patch('/v1/account/profile',headers=h,json=body).status_code==422
    assert c.get('/v1/account').json()['coins']==100


def test_atomic_gifts_idempotency_and_conflicting_replay(app):
    c,h,_=boot(app);key=token()
    first=gift(c,h,key).json();second=gift(c,h,key).json()
    assert first==second and first['coins']==80 and first['character']['score']==5
    assert len(second['ledger'])==1
    assert gift(c,h,key,gift_id='tea').status_code==409
    assert credit(c,h,key).status_code==409
    other,ho,_=boot(app)
    assert gift(other,ho,key).json()['coins']==80
    assert c.get('/v1/account').json()['coins']==80
    assert gift(c,h,gift_id='lamp').status_code==409
    assert gift(c,h,character='unknown').status_code==404
    assert c.get('/v1/account').json()['character']['score']==5


def test_forged_amounts_csrf_and_invalid_ids(app):
    c,h,_=boot(app)
    assert gift(c,{},gift_id='bookmark').status_code==403
    for extra in [{'price':0},{'points':100},{'user_id':'other'}]:
        body={'request_id':token(),'gift_id':'bookmark',**extra}
        assert c.post('/v1/characters/shen_yan/gifts',headers=h,json=body).status_code==422
    assert gift(c,h,gift_id='fake').status_code==422
    assert gift(c,h,key='invalid').status_code==422
    assert c.post('/v1/account/demo-credit',headers=h,json={'request_id':token(),'amount':10000}).status_code==422
    assert c.get('/v1/account').json()['coins']==100


def test_demo_credit_limit_and_replay_not_real_payment(app):
    c,h,_=boot(app);key=token()
    assert credit(c,h,key).json()['coins']==200
    assert credit(c,h,key).json()['coins']==200
    for _ in range(4):assert credit(c,h).status_code==200
    assert credit(c,h).status_code==429
    state=c.get('/v1/account').json()
    assert state['coins']==600 and state['character']['score']==0 and state['currency_mode']=='demo'
    assert c.post('/v1/account/recharge',headers=h,json={'amount':10}).status_code==404


def test_exact_unlocks_and_explicit_consent_with_full_score_cap(app):
    c,h,_=boot(app)
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True}).status_code==403
    assert c.patch('/v1/emotion/settings',headers=h,json={'enabled':True}).status_code==403
    assert c.get('/v1/weather/locations?q=Tokyo').status_code==403
    assert c.patch('/v1/weather/settings',headers=h,json={'enabled':True}).status_code==403
    for i in range(1,21):
        if c.get('/v1/account').json()['coins']<20:assert credit(c,h).status_code==200
        state=gift(c,h).json();score=i*5
        assert state['character']['score']==score
        assert state['character']['abilities']=={k:score>=v for k,v in THRESHOLDS.items()}
        # Unlocking is NOT consenting. No API setting was silently enabled.
        assert not c.get('/v1/memories').json()['settings']['memory_enabled']
        assert not c.get('/v1/emotion').json()['settings']['enabled']
        assert not c.get('/v1/weather/settings').json()['enabled']
    before=c.get('/v1/account').json()
    assert gift(c,h).status_code==409
    assert c.get('/v1/account').json()==before
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True}).status_code==200
    assert c.patch('/v1/emotion/settings',headers=h,json={'enabled':True}).status_code==200
    item=c.post('/v1/memories',headers=h,json={'fact':'我叫合成小雨'}).json()['item']
    assert c.patch('/v1/memories/'+item['id'],headers=h,json={'version':item['version'],'confirm':True}).status_code==200
    recalled=c.post('/v1/chat',headers=h,json={'message':'我的名字是什么？'})
    assert recalled.status_code==200 and item['id'] in recalled.json()['retrieved_memory_ids']
    mood=c.post('/v1/chat',headers=h,json={'message':'我很紧张'})
    assert mood.status_code==200 and mood.json()['emotion']['assessment'] is not None
    assert c.get('/v1/weather/locations?q=Tokyo').json()['items'][0]['id']==1
    assert c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1}).status_code==200
    forecast=c.post('/v1/chat',headers=h,json={'message':'明天天气怎么样？'})
    assert forecast.status_code==200 and forecast.json()['weather']['status']=='ok'


def test_locked_existing_data_can_be_read_revoked_and_deleted(app):
    c,h,_=boot(app);store=app.state.memory_store;user=uid(app,c)
    store.configure(user,True,'Asia/Tokyo')
    row=store.candidate(user,'我叫合成小雨',token(),store.settings(user)['epoch'],manual=True)
    row=store.mutate(user,row['id'],row['version'],confirm=True)
    assert c.get('/v1/memories').json()['items'][0]['id']==row['id']
    store.retrieve=Mock(side_effect=AssertionError('locked memory must never be read'))
    assert c.post('/v1/chat',headers=h,json={'message':'你好'}).status_code==200
    assert c.post('/v1/memories',headers=h,json={'fact':'我住在合成新城'}).status_code==403
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':False}).status_code==200
    assert c.delete('/v1/memories/'+row['id'],headers=h,params={'version':row['version']}).status_code==200
    again,_,_=boot(app,dict(c.cookies))
    assert again.get('/v1/memories').json()['items']==[]
    assert c.delete('/v1/weather/settings',headers=h).status_code==200
    assert c.delete('/v1/emotion/settings',headers=h).status_code==200


def test_server_active_time_caps_idle_and_failed_or_guarded_turns(app):
    c,h,_=boot(app);growth=app.state.progression;user=uid(app,c)
    now=[datetime(2026,11,10,0,0,0)]
    growth.clock=lambda:now[0]
    assert growth.successful_turn(user,now[0])['character']['score']==0
    now[0]+=timedelta(seconds=60)
    assert growth.successful_turn(user,now[0])['character']['score']==1
    assert growth.successful_turn(user,now[0])['character']['score']==1  # repeated/refresh
    now[0]+=timedelta(hours=1)
    assert growth.successful_turn(user,now[0])['character']['score']==1  # idle gap
    for _ in range(20):
        now[0]+=timedelta(seconds=60);growth.successful_turn(user,now[0])
    assert growth.get(user)['character']['score']==10  # UTC daily cap
    now[0]+=timedelta(days=1,seconds=60)
    assert growth.successful_turn(user,now[0])['character']['score']==10
    now[0]+=timedelta(seconds=60)
    assert growth.successful_turn(user,now[0])['character']['score']==11


def test_generation_latency_is_not_active_time(app):
    c,h,_=boot(app);growth=app.state.progression;user=uid(app,c)
    started=datetime(2026,11,10)
    now=[started+timedelta(seconds=100)];growth.clock=lambda:now[0]
    growth.successful_turn(user,started)
    next_start=now[0]+timedelta(seconds=10)
    now[0]=next_start+timedelta(seconds=100)
    state=growth.successful_turn(user,next_start)
    assert state['character']['active_seconds']==10 and state['character']['score']==0


def test_growth_persists_and_profile_not_in_model_context(app):
    c,h,_=boot(app);key=token();gift(c,h,key)
    c.patch('/v1/account/profile',headers=h,json={'name':'合成用户','email':'private@example.invalid'})
    provider=SimpleNamespace(generate=AsyncMock(return_value='我在呢。'))
    config=app.state.memory_store.engine.url.render_as_string(hide_password=False)
    other_app=create_app(Settings(_env_file=None,chat_provider='mock',growth_enabled=True,
        dialogue_mode='companion',memory_database_url=config),provider)
    other,ho,s=boot(other_app,dict(c.cookies))
    assert s['account']['coins']==80 and s['account']['character']['score']==5
    assert gift(other,ho,key).json()['coins']==80
    assert other.post('/v1/chat',headers=ho,json={'message':'你好'}).status_code==200
    assert 'private@example.invalid' not in str(provider.generate.call_args)


def test_parallel_gifts_do_not_overspend(app):
    c,h,_=boot(app);credit(c,h)
    growth=app.state.progression;user=uid(app,c)
    def buy(_):
        try:growth.action(user,token(),'lamp','shen_yan');return True
        except ProviderFailure as exc:
            assert exc.code=='insufficient_coins';return False
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(buy,range(2)))
    assert sum(result)==1
    state=growth.get(user)
    assert state['coins']==80 and state['character']['score']==20


@pytest.mark.parametrize('threshold',[30,60,90])
def test_exact_boundary_from_active_time(app,threshold):
    c,h,_=boot(app);growth=app.state.progression;user=uid(app,c)
    start=datetime(2026,11,10)
    with app.state.memory_store.db.begin() as db:
        row=db.get(Bond,(user,'shen_yan'));row.score=threshold-1;row.last_turn=start
    ability=next(k for k,v in THRESHOLDS.items() if v==threshold)
    assert not growth.get(user)['character']['abilities'][ability]
    growth.clock=lambda:start+timedelta(seconds=60)
    result=growth.successful_turn(user,start+timedelta(seconds=60))
    assert result['character']['score']==threshold and result['character']['abilities'][ability]


@pytest.mark.parametrize('guarded',[False,True])
def test_failed_or_guarded_api_reply_does_not_reward_time(app,guarded):
    provider=SimpleNamespace(generate=AsyncMock(return_value='我今年19岁。' if guarded else None,
        side_effect=None if guarded else ProviderFailure('timeout','合成超时',504)))
    url=app.state.memory_store.engine.url.render_as_string(hide_password=False)
    instance=create_app(Settings(_env_file=None,chat_provider='mock',growth_enabled=True,
        dialogue_mode='companion',memory_database_url=url),provider)
    c,h,_=boot(instance);growth=instance.state.progression;user=uid(instance,c)
    start=datetime(2026,11,10);growth.clock=lambda:start
    growth.successful_turn(user,start)
    growth.clock=lambda:start+timedelta(seconds=60)
    result=c.post('/v1/chat',headers=h,json={'message':'你好'})
    assert result.status_code==(200 if guarded else 504)
    assert growth.get(user)['character']['score']==0


def test_concurrent_same_request_is_charged_once(app):
    c,h,_=boot(app);growth=app.state.progression;user=uid(app,c);key=token()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _:growth.action(user,key,'bookmark','shen_yan'),range(2)))
    state=growth.get(user)
    assert state['coins']==80 and state['character']['score']==5 and len(state['ledger'])==1


def test_locked_old_tool_consent_cannot_call_tools_and_can_be_revoked(app):
    c,h,_=boot(app);user=uid(app,c);store=app.state.memory_store
    place=asyncio.run(app.state.weather_provider.place(1)).model_dump()
    store.configure_weather(user,True,place)
    store.configure_emotion(user,{'enabled':True})
    app.state.weather_provider.forecast=AsyncMock(side_effect=AssertionError('locked'))
    app.state.emotion_provider.analyze=AsyncMock(side_effect=AssertionError('locked'))
    r=c.post('/v1/chat',headers=h,json={'message':'我好紧张，今天下雨吗？'})
    assert r.status_code==200 and r.json()['emotion']['assessment'] is None
    app.state.weather_provider.forecast.assert_not_awaited()
    app.state.emotion_provider.analyze.assert_not_awaited()
    assert c.patch('/v1/weather/settings',headers=h,json={'enabled':False,'city_id':1}).status_code==200
    assert c.patch('/v1/emotion/settings',headers=h,json={'enabled':False}).status_code==200


def test_client_reported_time_cannot_award_points(app):
    c,h,_=boot(app);growth=app.state.progression
    growth.clock=lambda:datetime(2026,11,10)
    for _ in range(2):
        r=c.post('/v1/chat',headers=h,json={'message':'你好','duration_seconds':999999,'score':100})
        assert r.status_code==200 and r.json()['account']['character']['score']==0


def test_production_growth_default(monkeypatch):
    monkeypatch.delenv('GROWTH_ENABLED',raising=False)
    assert Settings(_env_file=None).growth_enabled


def test_product_unlock_order_is_memory_weather_then_emotion():
    assert THRESHOLDS=={'memory':30,'weather':60,'emotion':90}


def test_weather_is_available_at_60_and_emotion_waits_until_90(app):
    c,h,_=boot(app);user=uid(app,c)
    with app.state.memory_store.db.begin() as db:
        db.get(Bond,(user,'shen_yan')).score=60
    assert c.get('/v1/weather/locations?q=Tokyo').status_code==200
    assert c.patch('/v1/emotion/settings',headers=h,json={'enabled':True}).status_code==403
    with app.state.memory_store.db.begin() as db:
        db.get(Bond,(user,'shen_yan')).score=90
    assert c.patch('/v1/emotion/settings',headers=h,json={'enabled':True}).status_code==200


def test_old_cross_midnight_completion_cannot_reset_daily_allowance(app):
    c,_,_=boot(app);growth=app.state.progression;user=uid(app,c)
    now=datetime(2026,11,11,0,20)
    with app.state.memory_store.db.begin() as db:
        bond=db.get(Bond,(user,'shen_yan'))
        bond.score=10;bond.talk_day='2026-11-11';bond.talk_points_today=10;bond.last_turn=now
    growth.clock=lambda:now
    growth.successful_turn(user,datetime(2026,11,10,23,59))
    growth.clock=lambda:now+timedelta(seconds=60)
    result=growth.successful_turn(user,growth.clock())
    assert result['character']['score']==10
    with app.state.memory_store.db() as db:
        bond=db.get(Bond,(user,'shen_yan'))
        assert bond.talk_day=='2026-11-11' and bond.talk_points_today==10


@pytest.mark.parametrize('failure',['reward','candidate'])
def test_failed_completion_rolls_back_history_candidates_and_reward(app,monkeypatch,failure):
    c,h,_=boot(app);growth=app.state.progression;store=app.state.memory_store;user=uid(app,c)
    start=datetime(2026,11,10)
    with store.db.begin() as db:
        bond=db.get(Bond,(user,'shen_yan'));bond.score=30;bond.last_turn=start
    assert c.patch('/v1/settings',headers=h,json={'memory_enabled':True}).status_code==200
    growth.clock=lambda:start+timedelta(seconds=60)
    snapshot=growth.snapshot
    def failing_snapshot(db,account,bond):
        if bond.score>30:raise RuntimeError('synthetic reward storage failure')
        return snapshot(db,account,bond)
    with monkeypatch.context() as patch:
        if failure=='reward':patch.setattr(growth,'snapshot',failing_snapshot)
        else:patch.setattr(store,'candidate',Mock(side_effect=RuntimeError('synthetic memory storage failure')))
        with TestClient(app,raise_server_exceptions=False) as client:
            client.cookies.update(c.cookies)
            result=client.post('/v1/chat',headers=h,json={'message':'我明天有一场面试。'})
        assert result.status_code==500
    session=next(s for s in app.state.sessions.values() if s.user_id==user)
    assert session.messages==[]
    assert store.list(user)==[]
    assert growth.get(user)['character']['score']==30

"""Semantic emotion lifecycle using synthetic players and disposable databases."""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dialogue import ProviderFailure
from app.emotion import DEFAULTS
from app.main import create_app
from app.progression import Bond
from app import emotion_understanding as e
from test_emotion_semantics import plan,report,estimate


@pytest.fixture(params=['sqlite','postgres'])
def env(request,tmp_path):
    url=os.environ.get('TEST_POSTGRES_URL') if request.param=='postgres' else 'sqlite:///'+str(tmp_path/'emotion-semantic.sqlite3')
    if not url:pytest.skip('requires independent temporary PostgreSQL')
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',dialogue_mode='companion',growth_enabled=True,
        memory_understanding_mode='semantic',weather_understanding_mode='semantic',emotion_understanding_mode='semantic',memory_database_url=url)
    analyst=SimpleNamespace(decide=AsyncMock(return_value=plan()),analyze=AsyncMock(return_value=estimate()))
    legacy=SimpleNamespace(analyze=AsyncMock(side_effect=AssertionError('legacy must not run')))
    generator=SimpleNamespace(generate=AsyncMock(return_value='うん、ゆっくり聞かせて。'))
    app=create_app(settings,generator,emotion_provider=legacy,emotion_understander=analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    return SimpleNamespace(settings=settings,app=app,c=c,h=h,uid=uid,store=app.state.memory_store,analyst=analyst,generator=generator,legacy=legacy)


def unlock(x,score=90):
    with x.store.db.begin() as db:db.get(Bond,(x.uid,'shen_yan')).score=score


def enable(x,**kw):
    unlock(x)
    assert x.c.patch('/v1/emotion/settings',headers=x.h,json={**DEFAULTS,'enabled':True,**kw}).status_code==200


def chat(x,message='合成の話',locale='ja-JP'):
    return x.c.post('/v1/chat',headers=x.h,json={'message':message,'locale':locale})


@pytest.mark.parametrize('message,labels,locale',[
    ('悲しくない、ただ疲れてる',['tired'],'ja-JP'),('我不是难过，只是累了',['tired'],'zh-CN'),
])
def test_report_context_and_ephemeral_state(env,message,labels,locale):
    x=env;enable(x);x.analyst.decide.return_value=plan(report(message,labels))
    r=chat(x,message,locale)
    assert r.status_code==200 and r.json()['emotion']['status']=='self_report'
    a=r.json()['emotion']['assessment']
    assert a['source']=='model' and a['basis']=='self_report' and a['confidence']<1
    assert message not in e.emotion_prompt(r.json()['emotion'],{**DEFAULTS,'enabled':True})
    assert e.CONTEXT_PROMPT in x.generator.generate.call_args.args[1]
    assert x.c.get('/v1/emotion').json()['assessment']['labels']==labels
    assert x.c.get('/v1/memories').json()['items']==[]
    x.analyst.analyze.assert_not_awaited();x.legacy.analyze.assert_not_awaited()
    new=TestClient(create_app(x.settings,x.generator,emotion_understander=x.analyst));new.cookies.update(x.c.cookies);new.get('/v1/session')
    assert new.get('/v1/emotion').json()['settings']['enabled']
    assert new.get('/v1/emotion').json()['assessment'] is None  # no disk emotion cache


@pytest.mark.parametrize('score,on',[(0,False),(90,False),(0,True)])
def test_capability_and_consent_precede_both_calls(env,score,on):
    x=env;unlock(x,score)
    if on:x.store.configure_emotion(x.uid,{**DEFAULTS,'enabled':True})
    assert chat(x,'今は悲しい').json()['emotion']['status']=='disabled'
    x.analyst.decide.assert_not_awaited();x.analyst.analyze.assert_not_awaited()


def test_interval_early_request_cooldown_and_transient_preference(env):
    x=env;enable(x)
    assert chat(x).json()['emotion']['status']=='waiting'
    x.analyst.decide.return_value=plan(request_analysis=True,preference='listen',preference_source='話だけ聞いて')
    x.analyst.analyze.return_value=estimate(ids=['u2'])
    assert chat(x,'話だけ聞いて').json()['emotion']['status']=='analyzed'
    assert '"player_preference": "listen"' in x.generator.generate.call_args.args[1]
    assert x.c.get('/v1/emotion').json()['settings']['preference']=='ask'
    assert chat(x,'話だけ聞いて').json()['emotion']['status']=='cached'
    assert x.analyst.analyze.await_count==1


def test_crud_manual_correction_isolation_clear_delete_restart(env):
    x=env;enable(x)
    assert x.c.patch('/v1/emotion/assessment',json={'label':'joy'}).status_code==403
    assert x.c.patch('/v1/emotion/assessment',headers=x.h,json={'label':'joy','preference':'listen'}).status_code==200
    assert chat(x).json()['emotion']['status']=='user_override'
    assert x.c.get('/v1/emotion').json()['assessment']['source']=='user'
    x.analyst.analyze.assert_not_awaited()
    stranger=TestClient(x.app);stranger.get('/v1/session')
    assert stranger.get('/v1/emotion').json()['assessment'] is None
    assert x.c.delete('/v1/emotion/assessment',headers=x.h).status_code==200
    assert x.c.get('/v1/emotion').json()['assessment'] is None
    assert x.c.get('/v1/session').json()['messages']==[]
    unlock(x,0)
    assert x.c.patch('/v1/emotion/settings',headers=x.h,json={**DEFAULTS,'enabled':False}).status_code==200
    assert x.c.delete('/v1/emotion/settings',headers=x.h).status_code==200
    assert x.c.get('/v1/emotion').json()=={'settings':DEFAULTS,'assessment':None}
    fresh=TestClient(create_app(x.settings,x.generator,emotion_understander=x.analyst));fresh.cookies.update(x.c.cookies);fresh.get('/v1/session')
    assert fresh.get('/v1/emotion').json()=={'settings':DEFAULTS,'assessment':None}


@pytest.mark.parametrize('stage',['decide','analyze'])
def test_revoke_inflight_stops_generation_and_old_results(env,stage):
    x=env;enable(x);x.analyst.decide.return_value=plan(request_analysis=True)
    async def revoke(data):
        x.store.configure_emotion(x.uid,{**DEFAULTS,'enabled':False})
        return plan(request_analysis=True) if stage=='decide' else estimate()
    getattr(x.analyst,stage).side_effect=revoke
    assert chat(x).status_code==409
    x.generator.generate.assert_not_awaited()
    if stage=='decide':x.analyst.analyze.assert_not_awaited()
    assert x.c.get('/v1/emotion').json()['assessment'] is None
    assert x.c.get('/v1/session').json()['messages']==[]


def test_invalid_plan_and_manual_correction_not_replaced_by_failure(env):
    x=env;enable(x)
    x.c.patch('/v1/emotion/assessment',headers=x.h,json={'label':'joy','preference':'listen'})
    x.analyst.decide.return_value={'invalid':'synthetic'}
    r=chat(x)
    assert r.status_code==200 and r.json()['emotion']['assessment'] is None
    assert x.c.get('/v1/emotion').json()['assessment']['labels']==['joy']
    x.analyst.analyze.assert_not_awaited()


def test_new_report_not_saved_on_generation_failure_or_old_label_revived(env):
    x=env;enable(x)
    x.c.patch('/v1/emotion/assessment',headers=x.h,json={'label':'sadness'})
    x.analyst.decide.return_value=plan(report('悲しくない',['unknown']))
    x.generator.generate.side_effect=ProviderFailure('timeout','synthetic timeout',504)
    assert chat(x,'悲しくない').status_code==504
    assert x.c.get('/v1/emotion').json()['assessment'] is None
    assert x.c.get('/v1/session').json()['messages']==[]


def test_default_semantic_mode_and_no_legacy_entry(monkeypatch,tmp_path):
    monkeypatch.delenv('EMOTION_UNDERSTANDING_MODE')
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',dialogue_mode='companion',growth_enabled=True,
        memory_database_url='sqlite:///'+str(tmp_path/'default.sqlite3'))
    assert settings.emotion_understanding_mode=='semantic'
    legacy=AsyncMock(side_effect=AssertionError('legacy must not run'));monkeypatch.setattr('app.main.assess',legacy)
    p=SimpleNamespace(decide=AsyncMock(return_value=plan()),analyze=AsyncMock())
    app=create_app(settings,emotion_understander=p);c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    with app.state.memory_store.db.begin() as db:db.get(Bond,(uid,'shen_yan')).score=90
    c.patch('/v1/emotion/settings',headers=h,json={**DEFAULTS,'enabled':True})
    assert c.post('/v1/chat',headers=h,json={'message':'こんにちは','locale':'ja-JP'}).json()['emotion']['status']=='waiting'
    p.decide.assert_awaited_once();legacy.assert_not_awaited()

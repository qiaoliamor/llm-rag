"""Default companion flow on synthetic identities and disposable databases."""
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dialogue import ProviderFailure
from app.main import create_app
from app.memory import MemoryStore
from app.progression import Bond
from app.weather import MockWeatherProvider
from app import weather_understanding as w
from test_semantics import NOW, TOKYO, plan, date_spec


@pytest.fixture(params=['sqlite','postgres'])
def env(request,tmp_path,monkeypatch):
    url=os.environ.get('TEST_POSTGRES_URL') if request.param=='postgres' else 'sqlite:///'+str(tmp_path/'weather.sqlite3')
    if not url:pytest.skip('requires independent temporary PostgreSQL')
    monkeypatch.setattr(w,'clock',lambda:NOW)
    monkeypatch.setattr('app.weather.clock',lambda:NOW)
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=plan(city='さいたま市',date=date_spec('relative_days','明日',days=1))))
    provider=MockWeatherProvider();provider.search=AsyncMock(return_value=[TOKYO]);provider.forecast=AsyncMock(wraps=provider.forecast)
    generator=SimpleNamespace(generate=AsyncMock(return_value='これはオフラインの合成デモの天気だよ。'))
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',dialogue_mode='companion',growth_enabled=True,
        memory_understanding_mode='semantic',weather_understanding_mode='semantic',memory_database_url=url)
    app=create_app(settings,generator,provider,weather_understander=analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    return SimpleNamespace(app=app,c=c,h=h,uid=uid,store=app.state.memory_store,analyst=analyst,provider=provider,generator=generator,settings=settings)


def unlock(e,score=60):
    with e.store.db.begin() as db:db.get(Bond,(e.uid,'shen_yan')).score=score


def enable(e,city_id=None):
    unlock(e)
    assert e.c.patch('/v1/weather/settings',headers=e.h,json={'enabled':True,'city_id':city_id}).status_code==200


def chat(e,message='さいたま市の明日の天気は？',locale='ja-JP'):
    return e.c.post('/v1/chat',headers=e.h,json={'message':message,'locale':locale})


@pytest.mark.parametrize('message,value',[
    ('さいたま市の明日の天気は？',plan(city='さいたま市',date=date_spec('relative_days','明日',days=1))),
    ('广州明天下雨吗？',plan(city='广州',date=date_spec('relative_days','明天',days=1))),
])
def test_locale_query_prompt_and_temporary_place_does_not_save(env,message,value):
    e=env;enable(e);e.analyst.analyze.return_value=value
    r=chat(e,message,'zh-CN' if message.startswith('广州') else 'ja-JP')
    assert r.status_code==200 and r.json()['weather']['status']=='ok'
    assert r.json()['weather']['date']=='2026-11-13'
    assert '2026-11-13' in e.generator.generate.call_args.args[1]
    assert e.c.get('/v1/weather/settings').json()['place'] is None
    assert e.analyst.analyze.call_args.args[0]=={'current_message':message,'pending':None}
    # Mock has no semantic judge: use bounded tool facts in the requested language.
    assert r.json()['guarded']
    prefix='这是演示天气。' if message.startswith('广州') else 'これはデモの天気だよ。'
    assert r.json()['reply'].startswith(prefix)


def test_default_settings_are_semantic_without_environment(monkeypatch,tmp_path):
    monkeypatch.delenv('WEATHER_UNDERSTANDING_MODE')
    settings=Settings(_env_file=None,chat_provider='mock',weather_provider='mock',dialogue_mode='companion',growth_enabled=True,
        memory_database_url='sqlite:///'+str(tmp_path/'default-weather.sqlite3'))
    assert settings.weather_understanding_mode=='semantic'
    legacy=AsyncMock(side_effect=AssertionError('must not invoke legacy weather'))
    monkeypatch.setattr('app.main.query_weather',legacy)
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=plan('none')))
    app=create_app(settings,weather_understander=analyst)
    c=TestClient(app);h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    uid=next(iter(app.state.sessions.values())).user_id
    with app.state.memory_store.db.begin() as db:db.get(Bond,(uid,'shen_yan')).score=60
    assert c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':None}).status_code==200
    assert c.post('/v1/chat',headers=h,json={'message':'こんにちは','locale':'ja-JP'}).json()['weather'] is None
    analyst.analyze.assert_awaited_once();legacy.assert_not_awaited()


@pytest.mark.parametrize('score,enabled',[(0,False),(60,False),(0,True)])
def test_capability_and_consent_gate_model_and_tools(env,score,enabled):
    e=env;unlock(e,score)
    if enabled:e.store.configure_weather(e.uid,True,None)
    r=chat(e)
    assert r.status_code==200 and r.json()['weather'] is None
    e.analyst.analyze.assert_not_awaited();e.provider.search.assert_not_awaited();e.provider.forecast.assert_not_awaited()


def test_weather_settings_crud_isolation_revoke_delete_restart(env):
    e=env;unlock(e)
    assert e.c.get('/v1/weather/locations',params={'q':'さいたま市'}).status_code==200
    assert e.c.patch('/v1/weather/settings',headers={},json={'enabled':True,'city_id':1}).status_code==403
    enable(e,1)
    saved=e.c.get('/v1/weather/settings').json()
    assert saved['enabled'] and saved['place']['id']==1
    stranger=TestClient(e.app);stranger.get('/v1/session')
    assert stranger.get('/v1/weather/settings').json()['place'] is None
    fresh=TestClient(create_app(e.settings,e.generator,e.provider,weather_understander=e.analyst))
    fresh.cookies.update(e.c.cookies);fresh.get('/v1/session')
    assert fresh.get('/v1/weather/settings').json()['place']['id']==1
    # Opt-out and delete stay available after losing eligibility.
    unlock(e,0);e.provider.cache['synthetic-public']=(0,{'status':'ok'})
    assert e.c.patch('/v1/weather/settings',headers=e.h,json={'enabled':False,'city_id':1}).status_code==200
    assert e.provider.cache=={}
    e.analyst.analyze.reset_mock();chat(e)
    e.analyst.analyze.assert_not_awaited()
    e.provider.cache['synthetic-public']=(0,{'status':'ok'})
    assert e.c.delete('/v1/weather/settings',headers=e.h).status_code==200
    assert e.provider.cache=={}
    assert MemoryStore(e.settings.memory_database_url.get_secret_value()).weather_settings(e.uid)=={'enabled':False,'place':None}
    fresh2=TestClient(create_app(e.settings,e.generator,e.provider,weather_understander=e.analyst));fresh2.cookies.update(e.c.cookies)
    fresh2.get('/v1/session')
    assert fresh2.get('/v1/weather/settings').json()['place'] is None
    assert fresh2.get('/v1/session').json()['messages']==[]


@pytest.mark.parametrize('phase',['analysis','search','forecast'])
def test_revocation_stops_inflight_reply_and_further_tools(env,phase):
    e=env;enable(e)
    async def analysis(data):
        e.store.configure_weather(e.uid,False,None)
        return plan(city='さいたま市')
    async def search(city):
        e.store.configure_weather(e.uid,False,None)
        return [TOKYO]
    async def forecast(place,intent):
        e.store.configure_weather(e.uid,False,None)
        return {'status':'ok'}
    if phase=='analysis':e.analyst.analyze.side_effect=analysis
    elif phase=='search':e.provider.search.side_effect=search
    else:e.provider.forecast.side_effect=forecast
    assert chat(e).status_code==409
    e.generator.generate.assert_not_awaited()
    if phase=='analysis':e.provider.search.assert_not_awaited()
    if phase!='forecast':e.provider.forecast.assert_not_awaited()
    assert e.c.get('/v1/session').json()['messages']==[]


def test_pending_followup_cancel_and_settings_clear(env):
    e=env;enable(e)
    e.analyst.analyze.return_value=plan(date=date_spec('relative_days','明日',days=1))
    assert chat(e,'明日の天気は？').json()['weather']['status']=='location_required'
    e.analyst.analyze.return_value=plan(city='さいたま市',use_pending=True)
    assert chat(e,'さいたま市').json()['weather']['status']=='ok'
    e.analyst.analyze.return_value=plan(date=date_spec('relative_days','明日',days=1))
    chat(e,'明日の天気は？')
    e.analyst.analyze.return_value=plan('decline')
    assert chat(e,'やっぱり調べないで').json()['weather'] is None
    e.analyst.analyze.return_value=plan(city='さいたま市',use_pending=True)
    assert chat(e,'さいたま市').json()['weather']['status']=='clarification_required'
    assert e.analyst.analyze.call_args.args[0]['pending'] is None
    e.analyst.analyze.return_value=plan(date=date_spec('relative_days','明日',days=1));chat(e,'明日の天気は？')
    assert e.c.delete('/v1/weather/settings',headers=e.h).status_code==200
    assert next(iter(e.app.state.sessions.values())).pending_weather is None


def test_invalid_model_output_preserves_basic_chat(env):
    e=env;enable(e);e.analyst.analyze.return_value={'unexpected':'synthetic'}
    r=chat(e)
    assert r.status_code==200 and r.json()['weather']['status']=='understanding_unavailable'
    assert r.json()['reply']
    e.provider.search.assert_not_awaited();e.provider.forecast.assert_not_awaited()


def test_invalid_city_search_rejected_before_provider(env):
    e=env;unlock(e)
    for city in ('東京123','https://evil.test','東京\n住所'):
        assert e.c.get('/v1/weather/locations',params={'q':city}).status_code==422
    e.provider.search.assert_not_awaited();e.analyst.analyze.assert_not_awaited()


@pytest.mark.parametrize('previous',[False,True])
def test_failed_generation_never_saves_or_revives_pending(env,previous):
    e=env;enable(e)
    e.analyst.analyze.return_value=plan(date=date_spec('relative_days','明日',days=1))
    if previous:
        assert chat(e,'明日の天気は？').json()['weather']['status']=='location_required'
        assert next(iter(e.app.state.sessions.values())).pending_weather is not None
    before=e.c.get('/v1/session').json()['messages']
    e.generator.generate.side_effect=ProviderFailure('timeout','synthetic timeout',504)
    assert chat(e,'明日の天気は？').status_code==504
    assert next(iter(e.app.state.sessions.values())).pending_weather is None
    assert e.c.get('/v1/session').json()['messages']==before


@pytest.mark.parametrize('kind',['forecast','current'])
def test_reviewed_japanese_weather_preserves_original_reply_without_rewrite(env,kind):
    from test_presentation import verdict
    from app.weather_presentation import ANSWER_PROMPT
    e=env;enable(e)
    judge=SimpleNamespace(review=AsyncMock(side_effect=lambda reply,history,evidence:verdict(reply)))
    app=create_app(e.settings,e.generator,e.provider,weather_understander=e.analyst,semantic_judge=judge)
    c=TestClient(app);c.cookies.update(e.c.cookies)
    e.app=app;e.c=c;e.h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    e.analyst.analyze.return_value=plan(city='さいたま市',kind=kind)
    reply='これはオフラインの合成デモの天気だよ。' if kind=='forecast' else 'これはデモの天気だよ。今は15度くらい。'
    e.generator.generate.return_value=reply
    response=chat(e,'さいたま市の天気は？').json()
    assert response['reply']==reply and not response['guarded']
    assert response['semantic_review']['status']=='accepted'
    e.generator.generate.assert_awaited_once();judge.review.assert_awaited_once()
    assert ANSWER_PROMPT in e.generator.generate.call_args.args[1]
    assert e.c.get('/v1/session').json()['messages'][-1]['content']==reply


@pytest.mark.parametrize('failure',['timeout','invalid_output'])
def test_weather_judge_failure_no_unsafe_reply_or_new_history(env,failure):
    e=env;enable(e)
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()) if failure=='timeout' else AsyncMock(return_value={'bad':'synthetic'}))
    app=create_app(e.settings,e.generator,e.provider,weather_understander=e.analyst,semantic_judge=judge)
    c=TestClient(app);c.cookies.update(e.c.cookies);e.app=app;e.c=c
    e.h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    result=chat(e)
    if failure=='timeout':
        assert result.status_code==503
        assert e.c.get('/v1/session').json()['messages']==[]
    else:
        assert result.status_code==200
        assert result.json()['reply'].startswith('うん、聞いているよ。')
    assert next(iter(e.app.state.sessions.values())).pending_weather is None
    judge.review.assert_awaited_once();e.generator.generate.assert_awaited_once()


def test_configured_provider_wires_versioned_weather_judge(env,monkeypatch):
    from test_presentation import verdict
    from unittest.mock import Mock
    e=env;enable(e)
    judge=SimpleNamespace(review=AsyncMock(side_effect=lambda reply,history,evidence:verdict(reply)))
    factory=Mock(return_value=judge)
    monkeypatch.setattr('app.weather_presentation.WeatherAnalysisProvider',factory)
    # Generation, weather understanding, weather HTTP and the review factory are
    # all injected mocks. Setting the provider name must never reach a live API.
    settings=e.settings.model_copy(update={'chat_provider':'gemini'})
    app=create_app(settings,e.generator,e.provider,weather_understander=e.analyst)
    c=TestClient(app);c.cookies.update(e.c.cookies);e.app=app;e.c=c
    e.h={'x-csrf-token':c.get('/v1/session').json()['csrf_token']}
    response=chat(e)
    assert response.status_code==200 and response.json()['semantic_review']['status']=='accepted'
    assert response.json()['reply']=='これはオフラインの合成デモの天気だよ。'
    factory.assert_called_once_with(settings);judge.review.assert_awaited_once()

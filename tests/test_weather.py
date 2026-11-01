"""Synthetic, isolated M3 tests. No live provider, .env or player data."""
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dialogue import instructions, MockProvider
from app.main import create_app
from app.memory import MemoryStore, WeatherProfile
from app.weather import (OpenMeteoProvider, MockWeatherProvider, Place, WeatherIntent,
                         WeatherError, weather_intent, target_date, query_weather, weather_prompt)

NOW = datetime(2026, 11, 1, 15, 30, tzinfo=timezone.utc)
TOKYO = Place(id=1,name='合成东京',country='日本',admin1='东京',latitude=35.6,longitude=139.7,timezone='Asia/Tokyo')
OSAKA = TOKYO.model_copy(update={'id':2,'name':'合成大阪','latitude':34.7,'longitude':135.5})


def payload():
    return {'timezone':'Asia/Tokyo',
            'current':{'time':'2026-11-02T00:30','temperature_2m':15,'apparent_temperature':14,'precipitation':0.5,'weather_code':61,'wind_speed_10m':12},
            'current_units':{'temperature_2m':'°C','apparent_temperature':'°C','precipitation':'mm','wind_speed_10m':'km/h'},
            'daily':{'time':['2026-11-02','2026-11-03'],'weather_code':[61,3],'temperature_2m_min':[10,11],'temperature_2m_max':[18,19],'precipitation_probability_max':[70,20],'wind_speed_10m_max':[15,13]},
            'daily_units':{'temperature_2m_min':'°C','temperature_2m_max':'°C','precipitation_probability_max':'%','wind_speed_10m_max':'km/h'}}


@pytest.mark.parametrize('message,city,day,kind',[
    ('明天天气怎么样？',None,'明天','forecast'),
    ('现在天气如何',None,'today','current'),
    ('东京明天天气','东京','明天','forecast'),
    ('明天去大阪，天气怎么样？','大阪','明天','forecast'),
    ('我在东京，明天下雨吗？','东京','明天','forecast'),
    ('巴黎会下雨吗','巴黎','today','forecast'),
    ('冷不冷？',None,'today','forecast'),
    ('出门要带伞吗？',None,'today','forecast'),
    ('今天天气',None,'今天','forecast'),
    ('今天东京天气','东京','今天','forecast'),
    ('北京今天下雨吗？','北京','今天','forecast'),
    ('东京天气怎么样？','东京','today','forecast'),
    ('东京2026-11-03天气','东京','2026-11-03','forecast'),
])
def test_intent(message,city,day,kind):
    intent=weather_intent(message)
    assert (intent.city,intent.day,intent.kind)==(city,day,kind)


@pytest.mark.parametrize('message',['心里下雨了','心情像天气一样阴沉','风雨同舟','你真热情','我们聊本书吧','冷笑话','不要查天气了','不用查东京天气','别查天气'])
def test_metaphors_do_not_call_weather(message):
    assert weather_intent(message) is None


def test_dates_use_destination_timezone_and_reject_past():
    assert target_date(WeatherIntent(day='明天'),TOKYO,NOW).isoformat()=='2026-11-03'
    la=TOKYO.model_copy(update={'timezone':'America/Los_Angeles'})
    assert target_date(WeatherIntent(day='明天'),la,NOW).isoformat()=='2026-11-02'
    for day in ['2026-11-01','2026-11-09','2026-02-30','unsupported']:
        with pytest.raises(WeatherError): target_date(WeatherIntent(day=day),TOKYO,NOW)


def run(coro): return asyncio.run(coro)


def test_http_projection_cache_expiry_and_privacy(monkeypatch):
    monkeypatch.setattr('app.weather.clock',lambda:NOW)
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json=payload())
    provider=OpenMeteoProvider(httpx.MockTransport(handler))
    result=run(provider.forecast(TOKYO,WeatherIntent(day='明天')))
    assert result['date']=='2026-11-03' and result['min_c']==11 and result['rain_probability_pct']==20
    assert result['kind']=='forecast' and 'temperature_c' not in result
    assert 'latitude' not in result and 'hourly' not in result
    assert run(provider.forecast(TOKYO,WeatherIntent(day='明天')))['cached'] is True
    assert len(requests)==1
    key=next(iter(provider.cache));ts,data=provider.cache[key];provider.cache[key]=(ts-601,data)
    assert run(provider.forecast(TOKYO,WeatherIntent(day='明天')))['cached'] is False
    assert len(requests)==2
    current=run(provider.forecast(TOKYO,WeatherIntent(kind='current')))
    assert current['temperature_c']==15 and 'rain_probability_pct' not in current
    assert set(requests[0].url.params)=={'latitude','longitude','timezone','current','daily','forecast_days','temperature_unit','wind_speed_unit','precipitation_unit'}
    assert '合成东京' not in str(requests[0].url)


@pytest.mark.parametrize('change,code',[
    ('missing','invalid_response'),('null','invalid_response'),('unit','invalid_response'),
    ('stale','stale'),('nan','invalid_response'),('inverted','invalid_response'),('date','invalid_response')])
def test_bad_weather_never_becomes_evidence(monkeypatch,change,code):
    monkeypatch.setattr('app.weather.clock',lambda:NOW)
    data=payload(); intent=WeatherIntent()
    if change=='missing': data.pop('daily')
    if change=='null': data['daily']['temperature_2m_min'][0]=None
    if change=='unit': data['daily_units']['temperature_2m_min']='°F'
    if change=='stale':
        intent=WeatherIntent(kind='current');data['current']['time']='2026-10-20T00:00'
    if change=='nan': data['daily']['temperature_2m_min'][0]=float('nan')
    if change=='inverted': data['daily']['temperature_2m_min'][0]=60
    if change=='date': data['daily']['time']=[]
    # NaN is constructed after transport parsing to avoid emitting invalid JSON.
    provider=OpenMeteoProvider();provider._json=AsyncMock(return_value=data)
    with pytest.raises(WeatherError) as exc: run(provider.forecast(TOKYO,intent))
    assert exc.value.code==code and provider.cache=={}


@pytest.mark.parametrize('failure,code',[(429,'rate_limit'),(500,'unavailable'),(302,'unavailable'),('timeout','timeout'),('broken','unavailable')])
def test_upstream_errors_sanitized(failure,code):
    def handler(request):
        if failure=='timeout': raise httpx.ReadTimeout('private-response-and-key')
        if failure=='broken': return httpx.Response(200,text='not json private-response-and-key')
        return httpx.Response(failure,text='private-response-and-key')
    provider=OpenMeteoProvider(httpx.MockTransport(handler))
    with pytest.raises(WeatherError) as exc: run(provider.search('Tokyo'))
    assert exc.value.code==code and 'private' not in str(exc.value)


def test_search_resolution_and_local_rate_limit():
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json={'results':[TOKYO.model_dump(),OSAKA.model_dump()]} if request.url.path.endswith('search') else TOKYO.model_dump())
    provider=OpenMeteoProvider(httpx.MockTransport(handler))
    assert len(run(provider.search('Tokyo')))==2
    assert run(provider.place(1))==TOKYO
    assert requests[0].url.params['name']=='Tokyo'
    import time
    provider.calls.extend([time.monotonic()]*60)
    with pytest.raises(WeatherError,match='rate_limit'): run(provider.search('Tokyo'))


def connected(tmp_path,provider=None,model=None):
    settings=Settings(_env_file=None,chat_provider='mock',memory_database_url=f'sqlite:///{tmp_path}/weather.sqlite3')
    weather=provider or MockWeatherProvider()
    app=create_app(settings,model,weather)
    client=TestClient(app); data=client.get('/v1/session').json()
    return client,{'x-csrf-token':data['csrf_token']},weather,settings


def send(client,headers,message):
    result=client.post('/v1/chat',headers=headers,json={'message':message})
    assert result.status_code==200,result.text
    return result.json()


def test_default_disabled_no_network_or_implicit_location(tmp_path):
    weather=OpenMeteoProvider();weather.search=AsyncMock();weather.forecast=AsyncMock()
    client,h,_,_=connected(tmp_path,weather)
    assert client.get('/v1/weather/settings').json()=={'enabled':False,'place':None}
    data=send(client,h,'明天去东京，天气怎么样')
    assert data['weather']['status']=='disabled'
    weather.search.assert_not_called();weather.forecast.assert_not_called()
    assert send(client,h,'心里下雨了')['weather'] is None


def test_settings_crud_isolation_restart_delete(tmp_path):
    client,h,weather,settings=connected(tmp_path)
    assert client.get('/v1/weather/locations',params={'q':'Tokyo'}).json()['items']
    assert client.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1}).status_code==200
    assert send(client,h,'明天天气如何')['weather']['status']=='ok'
    other=TestClient(client.app);other.get('/v1/session')
    assert other.get('/v1/weather/settings').json()=={'enabled':False,'place':None}
    restart=TestClient(create_app(settings,weather_provider=weather));restart.cookies.update(client.cookies);restart.get('/v1/session')
    assert restart.get('/v1/weather/settings').json()['enabled']
    assert client.patch('/v1/weather/settings',headers=h,json={'enabled':False,'city_id':None}).status_code==200
    assert send(client,h,'明天天气')['weather']['status']=='disabled'
    assert client.delete('/v1/weather/settings',headers=h).status_code==200
    assert client.get('/v1/session').json()['messages']==[]
    assert client.get('/v1/weather/settings').json()=={'enabled':False,'place':None}
    assert send(client,h,'明天天气')['weather']['status']=='disabled'
    with client.app.state.memory_store.db() as db: assert not db.query(WeatherProfile).all()
    assert weather.cache=={}


@pytest.mark.parametrize('method,path,body',[
    ('patch','/v1/weather/settings',{'enabled':True}),('delete','/v1/weather/settings',None)])
def test_settings_auth_csrf_origin(tmp_path,method,path,body):
    c,h,_,_=connected(tmp_path)
    assert getattr(c,method)(path,json=body).status_code==403 if method=='patch' else getattr(c,method)(path).status_code==403
    kwargs={'json':body} if body is not None else {}
    assert getattr(c,method)(path,headers={**h,'origin':'https://evil.example'},**kwargs).status_code==403
    assert getattr(TestClient(c.app),method)(path,**kwargs).status_code==401


def test_invalid_city_id_and_no_results(tmp_path):
    c,h,weather,_=connected(tmp_path)
    for value in ['', 'x', 'x'*61, 'https://evil.example']:
        assert c.get('/v1/weather/locations',params={'q':value}).status_code==422
    assert c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':-1}).status_code==422
    weather.place=AsyncMock(side_effect=WeatherError('invalid_response'))
    assert c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':123}).status_code==503
    assert not c.get('/v1/weather/settings').json()['enabled']


def test_clarification_ambiguity_destination_and_prompt(tmp_path):
    model=AsyncMock();model.generate=AsyncMock(return_value='合成回复')
    weather=MockWeatherProvider();weather.search=AsyncMock(return_value=[OSAKA]);weather.place=AsyncMock(return_value=TOKYO)
    c,h,_,_=connected(tmp_path,weather,model)
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True})
    assert send(c,h,'明天天气')['weather']['status']=='location_required'
    result=send(c,h,'大阪')['weather']
    assert result['location']==OSAKA.label
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1})
    result=send(c,h,'明天去大阪，天气怎么样？')['weather']
    assert result['location']==OSAKA.label
    assert c.get('/v1/weather/settings').json()['place']['id']==TOKYO.id
    prompt=model.generate.call_args.args[1]
    assert '本轮天气工具数据' in prompt and 'forecast' in prompt and '角色卡' in prompt
    assert '降水概率不是降水量' in prompt and '心情' in prompt
    weather.search=AsyncMock(return_value=[TOKYO,OSAKA])
    assert send(c,h,'东京天气')['weather']['status']=='ambiguous'
    weather.search=AsyncMock(return_value=[])
    assert send(c,h,'不存在城天气')['weather']['status']=='not_found'
    weather.search=AsyncMock(side_effect=WeatherError('timeout'))
    data=send(c,h,'东京天气');assert data['weather']['status']=='timeout'
    assert 'temperature' not in str(data['weather'])
    assert send(c,h,'下周天气')['weather']['status']=='date_unsupported'


def test_settings_change_during_generation_revokes_reply(tmp_path):
    from threading import Event, Thread
    started,finish=Event(),Event()
    class SlowModel:
        async def generate(self,history,prompt):
            started.set()
            while not finish.is_set(): await asyncio.sleep(.01)
            return '旧地点天气回复'
    c,h,_,_=connected(tmp_path,model=SlowModel())
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1})
    results=[]
    thread=Thread(target=lambda:results.append(c.post('/v1/chat',headers=h,json={'message':'明天天气'})))
    thread.start();assert started.wait(3)
    try:
        assert c.delete('/v1/weather/settings',headers=h).status_code==200
    finally:
        finish.set();thread.join(3)
    assert results[0].status_code==409 and results[0].json()['code']=='memory_changed'
    assert c.get('/v1/session').json()['messages']==[]


def test_schema_upgrade_keeps_identity_and_memory_settings(tmp_path):
    url=f'sqlite:///{tmp_path}/old.sqlite3'
    store=MemoryStore(url);uid,token=store.identity(None);store.configure(uid,True,'UTC')
    with store.engine.begin() as db:
        from sqlalchemy import text
        db.execute(text('DROP TABLE weather_profiles'))
        db.execute(text('DELETE FROM schema_versions WHERE version=3'))
    new=MemoryStore(url)
    assert new.identity(token)[0]==uid and new.settings(uid)['memory_enabled']
    assert new.weather_settings(uid)=={'enabled':False,'place':None}


def test_activity_is_not_sent_to_geocoding():
    intent=weather_intent('明天去大阪参加面试，天气怎么样？')
    assert intent.city=='大阪'
    provider=OpenMeteoProvider(httpx.MockTransport(lambda r:pytest.fail('invalid private query must not leave process')))
    for city in ['大阪参加面试','我明天去东京','电话123456','https://evil.example']:
        with pytest.raises(WeatherError): run(provider.search(city))


def test_pending_does_not_geocode_emotional_reply():
    provider=MockWeatherProvider();provider.search=AsyncMock()
    profile={'enabled':True,'place':None}
    result,pending=run(query_weather(provider,'明天天气',profile))
    assert pending and result['status']=='location_required'
    result,pending=run(query_weather(provider,'我心里下雨了',profile,pending))
    assert result is None and pending is None
    provider.search.assert_not_called()


def test_confirmed_personal_context_is_passed_alongside_weather(tmp_path):
    model=AsyncMock();model.generate=AsyncMock(return_value='出门前给自己留点时间。')
    c,h,_,_=connected(tmp_path,model=model)
    c.patch('/v1/settings',headers=h,json={'memory_enabled':True,'timezone':'Asia/Tokyo'})
    item=c.post('/v1/memories',headers=h,json={'fact':'我明天有设计师面试'}).json()['item']
    c.patch('/v1/memories/'+item['id'],headers=h,json={'version':item['version'],'confirm':True})
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1})
    data=send(c,h,'明天面试，天气怎么样？')
    assert item['id'] in data['retrieved_memory_ids']
    prompt=model.generate.call_args.args[1]
    assert '我明天有设计师面试' in prompt and '本轮天气工具数据' in prompt
    assert '角色卡和正史优先' in prompt and '不要猜测玩家位置、心情' in prompt


def test_pg_weather_profile_crud_when_enabled(tmp_path):
    import os
    url=os.environ.get('TEST_POSTGRES_URL')
    if not url: pytest.skip('Set TEST_POSTGRES_URL for disposable PostgreSQL integration')
    store=MemoryStore(url);uid,token=store.identity(None)
    assert store.weather_settings(uid)=={'enabled':False,'place':None}
    initial=store.settings(uid)['epoch']
    store.configure_weather(uid,True,TOKYO.model_dump())
    restarted=MemoryStore(url)
    assert restarted.identity(token)[0]==uid
    assert restarted.weather_settings(uid)['place']['id']==1
    assert restarted.settings(uid)['epoch']==initial+1
    restarted.configure_weather(uid,False,OSAKA.model_dump())
    assert restarted.weather_settings(uid)['place']['id']==2
    restarted.configure_weather(uid,remove=True)
    assert restarted.weather_settings(uid)=={'enabled':False,'place':None}


def test_current_cache_rechecks_valid_time(monkeypatch):
    monkeypatch.setattr('app.weather.clock',lambda:NOW)
    provider=OpenMeteoProvider();provider._json=AsyncMock(return_value=payload())
    run(provider.forecast(TOKYO,WeatherIntent(kind='current')))
    key=next(iter(provider.cache));stamp,data=provider.cache[key]
    data['valid_at']=(NOW-timedelta(minutes=91)).isoformat()
    provider.cache[key]=(stamp,data)
    run(provider.forecast(TOKYO,WeatherIntent(kind='current')))
    assert provider._json.await_count==2


def test_reset_cancels_pending_city_clarification(tmp_path):
    c,h,weather,_=connected(tmp_path)
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True})
    assert send(c,h,'明天天气')['weather']['status']=='location_required'
    c.delete('/v1/session',headers=h)
    weather.search=AsyncMock()
    assert send(c,h,'东京')['weather'] is None
    weather.search.assert_not_called()


def test_revocation_during_weather_fetch_never_sends_old_evidence_to_model(tmp_path):
    from threading import Event,Thread
    started,finish=Event(),Event()
    class SlowWeather(MockWeatherProvider):
        async def forecast(self,place,intent):
            started.set()
            while not finish.is_set(): await asyncio.sleep(.01)
            return await super().forecast(place,intent)
    model=AsyncMock();model.generate=AsyncMock(return_value='旧证据')
    c,h,_,_=connected(tmp_path,SlowWeather(),model)
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1})
    results=[];thread=Thread(target=lambda:results.append(c.post('/v1/chat',headers=h,json={'message':'明天天气'})))
    thread.start();assert started.wait(3)
    try: assert c.delete('/v1/weather/settings',headers=h).status_code==200
    finally: finish.set();thread.join(3)
    assert results[0].status_code==409
    model.generate.assert_not_called()
    assert c.get('/v1/session').json()['messages']==[]


def test_opt_out_with_saved_city_works_offline(tmp_path):
    c,h,weather,_=connected(tmp_path)
    c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1})
    weather.place=AsyncMock(side_effect=WeatherError('unavailable'))
    response=c.patch('/v1/weather/settings',headers=h,json={'enabled':False,'city_id':1})
    assert response.status_code==200 and not response.json()['settings']['enabled']
    weather.place.assert_not_called()
    assert send(c,h,'明天天气')['weather']['status']=='disabled'


def test_delete_cannot_be_undone_by_an_older_inflight_save(tmp_path):
    from threading import Event,Thread
    started,finish=Event(),Event()
    class SlowWeather(MockWeatherProvider):
        async def place(self,city_id):
            started.set()
            while not finish.is_set(): await asyncio.sleep(.01)
            return await super().place(city_id)
    c,h,_,_=connected(tmp_path,SlowWeather())
    results=[];thread=Thread(target=lambda:results.append(c.patch('/v1/weather/settings',headers=h,json={'enabled':True,'city_id':1})))
    thread.start();assert started.wait(3)
    try: assert c.delete('/v1/weather/settings',headers=h).status_code==200
    finally: finish.set();thread.join(3)
    assert results[0].status_code==409
    assert c.get('/v1/weather/settings').json()=={'enabled':False,'place':None}

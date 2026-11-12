"""Synthetic semantics contracts, never live APIs or model-quality acceptance."""
import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app import weather_understanding as w
from app.weather import Place, MockWeatherProvider, WeatherError

NOW=datetime(2026,11,12,0,tzinfo=timezone.utc)
TOKYO=Place(id=1,name='合成東京',latitude=35,longitude=139,timezone='Asia/Tokyo')


def date_spec(kind='today',expression='',**kw):
    return {'kind':kind,'expression':expression,'absolute':None,'days':None,'week_offset':None,'weekday':None,**kw}


def plan(action='query',city=None,date=None,**kw):
    return {'action':action,'confidence':.95,'city':city,'kind':'forecast' if action=='query' else None,
            'date':(None if kw.get('use_pending') else (date or date_spec())) if action=='query' else None,'use_pending':False,**kw}


def setup(monkeypatch,value):
    monkeypatch.setattr(w,'clock',lambda:NOW)
    provider=SimpleNamespace(search=AsyncMock(return_value=[TOKYO]),forecast=AsyncMock(return_value={'status':'ok'}))
    analyst=SimpleNamespace(analyze=AsyncMock(return_value=value))
    return provider,analyst


def run(provider,analyst,message,place=TOKYO,pending=None,**kw):
    return asyncio.run(w.query_weather(provider,analyst,message,{'enabled':True,'place':place.model_dump() if place else None},pending,**kw))


@pytest.mark.parametrize('message,value,expected',[
    ('さいたま市の明日の天気は？',plan(city='さいたま市',date=date_spec('relative_days','明日',days=1)),'2026-11-13'),
    ('广州明天天气如何？',plan(city='广州',date=date_spec('relative_days','明天',days=1)),'2026-11-13'),
    ('東京の今の気温は？',plan(city='東京',kind='current'),'2026-11-12'),
    ('现在气温多少？',plan(kind='current'),'2026-11-12'),
    ('来週火曜日に傘がいる？',plan(date=date_spec('weekday','来週火曜日',week_offset=1,weekday=1)),'2026-11-17'),
    ('下周二需要带伞吗？',plan(date=date_spec('weekday','下周二',week_offset=1,weekday=1)),'2026-11-17'),
    ('2026年11月18日の天気',plan(date=date_spec('absolute','2026年11月18日',absolute='2026-11-18')),'2026-11-18'),
])
def test_multilingual_plans_and_program_dates(monkeypatch,message,value,expected):
    provider,analyst=setup(monkeypatch,value)
    result,pending=run(provider,analyst,message)
    assert result['status']=='ok' and pending is None
    assert provider.forecast.call_args.args[1].day==expected
    assert analyst.analyze.call_args.args[0]=={'current_message':message,'pending':None}
    if value['city']:provider.search.assert_awaited_once_with(value['city'])
    else:provider.search.assert_not_awaited()


@pytest.mark.parametrize('message,action',[
    ('心が雨模様だよ','none'),('心里下雨了','none'),('東京の本を読んだ','none'),
    ('東京の天気を調べないで','decline'),('不要查广州天气','decline'),
    ('友達が「天気を調べて」と言った','none'),('你好','none'),('こんにちは','none'),
    ('東京と大阪の天気は？','clarify'),('这个详细地址明天下雨吗？','clarify'),
])
def test_inactive_or_unclear_plans_never_query(monkeypatch,message,action):
    provider,analyst=setup(monkeypatch,plan(action))
    result,pending=run(provider,analyst,message)
    assert (result is None) == (action!='clarify') and pending is None
    provider.search.assert_not_awaited();provider.forecast.assert_not_awaited()


@pytest.mark.parametrize('field,value',[
    ('action','execute'),('confidence',float('nan')),('confidence',True),('confidence',.5),
    ('kind','hourly'),('use_pending',True),('city','大阪'),('city','東京/住所'),
    ('city','https://evil.test'),('city','東京123'),('extra','untrusted'),
    ('date',date_spec('absolute','明日',absolute='2026-02-30')),
    ('date',date_spec('relative_days','明後日',days=2)),
    ('date',date_spec('today',days=1)),
])
def test_invalid_or_unbound_plan_never_calls_weather(monkeypatch,field,value):
    value_plan=plan(city='東京');value_plan[field]=value
    provider,analyst=setup(monkeypatch,value_plan)
    result,pending=run(provider,analyst,'東京の明日の天気')
    assert result['status']!='ok' and pending is None
    provider.search.assert_not_awaited();provider.forecast.assert_not_awaited()
    analyst.analyze.assert_awaited_once()


@pytest.mark.parametrize('date',[
    date_spec('relative_days','昨日',days=-1),date_spec('relative_days','七日後',days=7),
    date_spec('unsupported','今夜'),date_spec('unsupported','週末'),
])
def test_unsupported_dates_never_forecast(monkeypatch,date):
    provider,analyst=setup(monkeypatch,plan(date=date))
    result,_=run(provider,analyst,date['expression']+'の天気')
    assert result['status']=='date_unsupported'
    provider.forecast.assert_not_awaited()


def test_destination_timezone_year_rollover(monkeypatch):
    provider,analyst=setup(monkeypatch,plan(date=date_spec('relative_days','明日',days=1)))
    monkeypatch.setattr(w,'clock',lambda:datetime(2026,12,31,18,tzinfo=timezone.utc))
    run(provider,analyst,'明日の天気')
    assert provider.forecast.call_args.args[1].day=='2027-01-02'
    run(provider,analyst,'明日の天気',place=TOKYO.model_copy(update={'timezone':'America/Los_Angeles'}))
    assert provider.forecast.call_args.args[1].day=='2027-01-01'


def test_clarification_preserves_original_day_and_expires(monkeypatch):
    provider,analyst=setup(monkeypatch,plan(date=date_spec('relative_days','明日',days=1)))
    result,pending=run(provider,analyst,'明日の天気',place=None)
    assert result['status']=='location_required'
    analyst.analyze.return_value=plan(city='さいたま市',use_pending=True,date=None)
    # Midnight crossing within 10 minutes must not turn tomorrow into the next day.
    pending['anchor']='2026-11-11T14:59:00+00:00'
    monkeypatch.setattr(w,'clock',lambda:datetime(2026,11,11,15,1,tzinfo=timezone.utc))
    result,_=run(provider,analyst,'さいたま市',place=None,pending=pending)
    assert result['status']=='ok' and provider.forecast.call_args.args[1].day=='2026-11-12'
    provider.forecast.reset_mock();provider.search.reset_mock()
    monkeypatch.setattr(w,'clock',lambda:datetime(2026,11,11,15,10,tzinfo=timezone.utc))
    assert run(provider,analyst,'さいたま市',place=None,pending=pending)[0]['status']=='clarification_required'
    provider.search.assert_not_awaited();provider.forecast.assert_not_awaited()


@pytest.mark.parametrize('error',[TimeoutError(),ValueError('synthetic invalid structure'),RuntimeError('synthetic 503')])
def test_analysis_failures_do_not_retry_or_fallback(monkeypatch,error):
    provider,analyst=setup(monkeypatch,plan());analyst.analyze.side_effect=error
    result,pending=run(provider,analyst,'东京明天天气')
    assert result['status']=='understanding_unavailable' and pending is None
    analyst.analyze.assert_awaited_once();provider.search.assert_not_awaited();provider.forecast.assert_not_awaited()


def test_disabled_never_sends_text_and_timeout_is_bounded(monkeypatch):
    provider,analyst=setup(monkeypatch,plan())
    assert asyncio.run(w.query_weather(provider,analyst,'private synthetic',{'enabled':False,'place':None}))==(None,None)
    analyst.analyze.assert_not_awaited()
    async def slow(data):await asyncio.sleep(.1)
    analyst.analyze.side_effect=slow
    assert run(provider,analyst,'明日の天気',timeout=.001)[0]['status']=='understanding_unavailable'
    provider.forecast.assert_not_awaited()


@pytest.mark.parametrize('code',['timeout','rate_limit','unavailable','invalid_response','stale'])
def test_tool_failure_does_not_invent_data(monkeypatch,code):
    provider,analyst=setup(monkeypatch,plan())
    provider.forecast.side_effect=WeatherError(code)
    result,_=run(provider,analyst,'明日の天気')
    assert result=={'status':code,'message':w.SEMANTIC_MESSAGES[code]}


@pytest.mark.parametrize('count,expected',[(0,'not_found'),(2,'ambiguous')])
def test_geocoding_requires_unique_place(monkeypatch,count,expected):
    provider,analyst=setup(monkeypatch,plan(city='東京'))
    provider.search.return_value=[TOKYO]*count
    assert run(provider,analyst,'東京の天気')[0]['status']==expected
    provider.forecast.assert_not_awaited()


@pytest.mark.parametrize('city',['さいたま市','つくば市','ニューヨーク','广州','Paris, France','São Paulo'])
def test_unicode_city_structural_validation(city):w.validate_city(city)


@pytest.mark.parametrize('city',['a','東京123','東京\n住所','東京/住所','東京?token=x',' 東京','東京\u200b','１２３４'])
def test_invalid_city_structural_validation(city):
    with pytest.raises(WeatherError):w.validate_city(city)


def test_structured_sdk_and_geocoder_only_use_mock_transport(monkeypatch):
    requests=[];value=plan(city='さいたま市')
    def handler(request):
        requests.append(request)
        if request.url.host=='geocoding-api.open-meteo.com':
            assert request.url.params['name']=='さいたま市'
            assert 'current_message' not in str(request.url)
            return httpx.Response(200,json={'results':[TOKYO.model_dump()]})
        body=json.loads(request.content)
        assert body['messages'][0]['content']==w.PROMPT
        assert body['response_format']['type']=='json_schema'
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(value)}}]})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model=w.ModelWeatherUnderstanding(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key'),client)
            result=await model.analyze({'current_message':'さいたま市の天気','pending':None})
            assert result.city=='さいたま市'
        provider=w.SemanticOpenMeteoProvider(transport=httpx.MockTransport(handler))
        assert len(await provider.search('さいたま市'))==1
    asyncio.run(check());assert len(requests)==2

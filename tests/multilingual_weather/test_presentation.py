"""Synthetic reply/judge contracts; no claims of real language understanding."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.reply_pipeline import generate_checked
from app.semantic_review import review_units, review_reply, evidence_bundle
from app.weather import weather_reply_conflicts, weather_fallback
from app import weather_presentation as voice


FORECAST={'status':'ok','source':'mock（合成）','kind':'forecast','location':'合成東京','timezone':'Asia/Tokyo',
          'date':'2026-11-13','min_c':12,'max_c':18,'rain_probability_pct':70}
CURRENT={**FORECAST,'kind':'current','temperature_c':15,'feels_like_c':14,'humidity_pct':65}
for key in ('min_c','max_c','rain_probability_pct'):CURRENT.pop(key)


def verdict(text,decision='accept',role=False):
    return {'decision':decision,'confidence':.95,'role_issues':[0] if role else [],'segments':[
        {'text':text,'kind':'assertion','verdict':'supported' if decision=='accept' or role else 'unsupported',
         'evidence_ids':['weather_current'] if decision=='accept' or role else [],
         'reason':'evidence_supports' if decision=='accept' or role else 'missing_evidence'}]}


def generate(replies,weather=FORECAST,judge=None,locale='ja-JP',user_text='明日の天気は？',**kw):
    provider=SimpleNamespace(generate=AsyncMock(side_effect=replies))
    result=asyncio.run(generate_checked(provider,[{'role':'user','content':user_text}],voice.ANSWER_PROMPT,
        '明日の天気は？',[],weather,{'status':'disabled','assessment':None},{},judge=judge,locale=locale,
        multilingual_weather=True,companion=True,**kw))
    return result,provider


@pytest.mark.parametrize('reply,weather',[
    ('これはオフラインの合成デモの天気だよ。',FORECAST),
    ('これはデモの天気だよ。予報では12〜18度くらい。',FORECAST),
    ('これはデモの天気だよ。今はだいたい15度くらい。',CURRENT),
    ('これは合成の天気だよ。推定では今15℃。',CURRENT),
])
def test_natural_japanese_not_blocked_by_chinese_word_requirements(reply,weather):
    assert weather_reply_conflicts(reply,weather)  # Exact old failure remains reproducible.
    assert weather_fallback(weather).startswith('这是演示天气。')
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(reply)))
    (actual,guarded,status),provider=generate([reply],weather,judge)
    assert actual==reply and not guarded and status['status']=='accepted'
    provider.generate.assert_awaited_once();judge.review.assert_awaited_once()
    weather_data=next(x['data'] for x in judge.review.call_args.args[2] if x['id']=='weather_current')
    assert weather_data['demo'] is True
    assert weather_data['reply_locale']=='ja-JP'


@pytest.mark.parametrize('reply,weather',[
    ('予報では13〜18度。',FORECAST),('予報では12から25度。',FORECAST),
    ('予報では25℃。',FORECAST),('今は80度くらい。',CURRENT),('湿度99％。',CURRENT),
    ('明日は湿度65%。',FORECAST),('今は12〜18度。',CURRENT),
    ('今日は15度。',{'status':'timeout','message':'synthetic failure'}),
])
def test_numeric_conflicts_cannot_be_overridden_by_accept(reply,weather):
    assert voice.numeric_conflicts(reply,weather)
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(reply)))
    (actual,guarded,status),provider=generate([reply,reply],weather,judge)
    assert guarded and status['status']=='fallback' and actual==voice.fallback(weather,'ja-JP')
    assert provider.generate.await_count==2 and judge.review.await_count==2


@pytest.mark.parametrize('reply,weather',[
    ('预计12到18度。',FORECAST),('予報では12〜18℃。',FORECAST),('予報では12から18度。',FORECAST),
    ('今は15℃、体感は14度くらい。湿度65％。',CURRENT),
    ('今は-4.6度くらい。',{**CURRENT,'temperature_c':-4.6}),
    ('予報では14〜20度。',{**FORECAST,'min_c':13.6,'max_c':20}),
])
def test_numeric_syntax_does_not_require_a_language(reply,weather):
    assert not voice.numeric_conflicts(reply,weather)


@pytest.mark.parametrize('bad',[
    'これは実測で15度だよ。', '明日は湿度80％で蒸し暑いよ。',
    '明日の予報だから今も雨だよ。', '天気が取れたよ。君は今そこにいるんだね。',
])
def test_semantic_rewrite_preserves_language_and_uses_one_budget(bad):
    good='これはデモの天気だよ。予報では12〜18度くらい。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(bad,'revise'),verdict(good)]))
    (actual,guarded,status),provider=generate([bad,good],judge=judge)
    assert actual==good and guarded and status['calls']==2
    assert provider.generate.await_count==2
    assert voice.REWRITE in provider.generate.call_args.args[1]


def test_supported_fact_with_presentation_issue_still_rewrites():
    bad='今は15度だよ。';good='これはデモの天気だよ。今は15度くらいかな。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(bad,'revise',role=True),verdict(good)]))
    (actual,guarded,_),_=generate([bad,good],CURRENT,judge)
    assert actual==good and guarded


def test_user_score_is_not_checked_as_weather_percentage():
    reply='試験で90％取れたんだね。'
    accepted=verdict(reply)
    accepted['segments'][0]['evidence_ids']=['user_0']
    judge=SimpleNamespace(review=AsyncMock(return_value=accepted))
    (actual,guarded,_),_=generate([reply],CURRENT,judge,user_text='試験で90％取ったよ。今の天気は？')
    assert actual==reply and not guarded


def test_mixed_user_score_and_weather_scope_uses_semantic_verdict():
    reply='90％取れたんだね、これはデモだけど今は15度くらいだよ。'
    accepted=verdict(reply)
    accepted['segments'][0]['evidence_ids']=['user_0','weather_current']
    judge=SimpleNamespace(review=AsyncMock(return_value=accepted))
    (actual,guarded,_),_=generate([reply],CURRENT,judge,user_text='試験で90％取ったよ。今の天気は？')
    assert actual==reply and not guarded


@pytest.mark.parametrize('locale,prefix',[('ja-JP','これはデモの天気だよ。'),('zh-CN','这是演示天气。')])
@pytest.mark.parametrize('enabled',[True,False])
def test_no_judge_or_disabled_review_uses_language_safe_tool_facts(locale,prefix,enabled):
    judge=None if enabled else SimpleNamespace(review=AsyncMock())
    (actual,guarded,status),provider=generate(['synthetic unreviewed claim'],locale=locale,judge=judge,review_enabled=enabled)
    assert actual.startswith(prefix) and guarded and status['status']=='weather_safe_fallback'
    provider.generate.assert_awaited_once()
    if judge is not None:judge.review.assert_not_awaited()


@pytest.mark.parametrize('code',['disabled','location_required','ambiguous','not_found','date_unsupported',
    'timeout','rate_limit','unavailable','invalid_response','stale','invalid_city','understanding_unavailable','clarification_required'])
def test_failures_have_japanese_fallback_without_weather_values(code):
    result=voice.fallback({'status':code,'message':'private synthetic original'},'ja-JP')
    assert result and 'private' not in result and '度' not in result


def test_live_data_fallback_never_calls_it_demo():
    assert 'デモ' not in voice.fallback({**CURRENT,'source':'Open-Meteo'},'ja-JP')
    assert '推定で15' in voice.fallback({**CURRENT,'source':'Open-Meteo'},'ja-JP')


@pytest.mark.parametrize('mode',['companion','audit'])
def test_structured_review_sdk_gets_versioned_prompt_and_validated_evidence(mode):
    reply='これはデモの天気だよ。今は15度くらい。'
    calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        prompt=body['messages'][0]['content']
        assert voice.REVIEW_PROMPT_EXTRA in prompt
        data=json.loads(body['messages'][1]['content'])
        assert next(e['data'] for e in data['evidence'] if e['id']=='weather_current')['demo'] is True
        assert next(e['data'] for e in data['evidence'] if e['id']=='weather_current')['reply_locale']=='ja-JP'
        result={'confidence':.95,'role_issues':[], 'units':[{'id':u['id'],'kind':'assertion','verdict':'supported',
            'evidence_ids':['weather_current']} for u in data['units']]}
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(result)}}]})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            judge=voice.WeatherAnalysisProvider(Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key',dialogue_mode=mode),client)
            evidence=evidence_bundle([{'role':'user','content':'今の天気は？'}],[],CURRENT,{'assessment':None})
            next(x['data'] for x in evidence if x['id']=='weather_current').update(demo=True,reply_locale='ja-JP')
            return await review_reply(judge,reply,[],evidence)
    assert asyncio.run(check()).status=='accept' and len(calls)==1

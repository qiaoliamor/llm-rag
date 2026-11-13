"""Bilingual care pipeline contracts with scripted judges, never quality scores."""
import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.emotion import DEFAULTS,emotion_reply_conflicts,emotion_fallback
from app.reply_pipeline import generate_checked
from app.semantic_review import evidence_bundle,review_reply
from app import emotion_presentation as voice

SETTINGS={**DEFAULTS,'enabled':True,'preference':'listen'}
MOOD={'status':'analyzed','assessment':{'labels':['sadness'],'intensity':.6,'confidence':.9,
    'source':'model','response_strategy':'listen','evidence_message_ids':['u1'],'observed_at':'private synthetic timestamp','turn':1}}


def verdict(text,decision='accept',role=False,ids=None,kind='assertion'):
    good=decision=='accept' or role
    return {'decision':decision,'confidence':.95,'role_issues':[0] if role else [],'segments':[
        {'text':text,'kind':kind,'verdict':('not_applicable' if kind=='nonfactual' else 'supported') if good else 'unsupported',
         'evidence_ids':[] if kind=='nonfactual' else (ids if ids is not None else ['emotion_current']) if good else [],
         'reason':'nonfactual' if kind=='nonfactual' else 'evidence_supports' if good else 'missing_evidence'}]}


def generate(replies,judge=None,mood=MOOD,settings=None,locale='ja-JP',weather=None,user_text='合成の相談',**kw):
    model=SimpleNamespace(generate=AsyncMock(side_effect=replies))
    args=dict(judge=judge,companion=True,locale=locale,multilingual_emotion=True,multilingual_weather=bool(weather),**kw)
    result=asyncio.run(generate_checked(model,[{'role':'user','content':user_text,'id':'u1'}],voice.ANSWER_PROMPT,
        user_text,[],weather,mood,settings or SETTINGS,**args))
    return result,model


@pytest.mark.parametrize('text',[
    '「你其实」と決めつけず、話を聞かせて。',
    '我不会断定“你其实很焦虑”，先听你说。',
    'うつ病だと決めつけることはしないよ。話したいことから聞かせて。',
])
def test_quoted_or_denied_phrases_not_lexically_blocked(text):
    if '你其实' in text:assert emotion_reply_conflicts(text,MOOD)
    assert not emotion_fallback(MOOD,SETTINGS).startswith('うん')
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text,kind='nonfactual')))
    (reply,guarded,status),model=generate([text],judge)
    assert reply==text and not guarded and status['status']=='accepted'
    model.generate.assert_awaited_once();judge.review.assert_awaited_once()


@pytest.mark.parametrize('text',[
    '君はうつ病だよ。','あなたは本当は絶対に悲しい。','君の不安は信頼度90％だよ。',
    '你其实就是焦虑症。','アドバイスを十個あげるね。','你有抑郁症，天气就说明了。',
])
def test_semantic_fact_or_presentation_issue_rewrites_once(text):
    good='うん、話したいことから聞かせて。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(text,'revise',role='信頼度' in text or 'アドバイス' in text),
        verdict(good,kind='nonfactual')]))
    (reply,guarded,status),model=generate([text,good],judge)
    assert reply==good and guarded and model.generate.await_count==2 and status['calls']==2
    assert voice.REWRITE in model.generate.call_args.args[1]


@pytest.mark.parametrize('locale,text',[('ja-JP','君はうつ病だよ。'),('zh-CN','你有抑郁症。')])
def test_repeated_invalid_replies_fallback_in_current_language(locale,text):
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text,'revise')))
    (reply,guarded,status),model=generate([text,text],judge,locale=locale)
    assert reply==voice.fallback(MOOD,SETTINGS,locale) and guarded and status['status']=='fallback'
    assert model.generate.await_count==2 and judge.review.await_count==2


@pytest.mark.parametrize('choice',['ask','listen','encourage','practical'])
@pytest.mark.parametrize('locale',['ja-JP','zh-CN'])
def test_all_preferences_have_non_diagnostic_language_fallback(choice,locale):
    config={**SETTINGS,'preference':choice}
    (reply,guarded,status),model=generate(['unreviewed synthetic claim'],settings=config,locale=locale)
    assert reply==voice.fallback(MOOD,config,locale) and guarded and status['status']=='emotion_safe_fallback'
    assert not any(word in reply for word in ('诊断','抑郁','焦虑症','うつ病','信頼度','置信'))
    model.generate.assert_awaited_once()


@pytest.mark.parametrize('status',['unavailable','uncertain','declined','waiting'])
def test_absent_assessment_not_invented_or_old_reference_exposed(status):
    mood={'status':status,'assessment':None}
    good='うん、聞いているよ。'
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(good,kind='nonfactual')))
    (reply,guarded,_),_=generate([good],judge,mood=mood)
    assert reply==good and not guarded
    if status=='waiting':judge.review.assert_not_awaited()
    else:
        evidence=judge.review.call_args.args[2]
        assert 'emotion_current' not in [x['id'] for x in evidence]
        assert next(x['data'] for x in evidence if x['id']=='emotion_policy')['status']==status


def test_manual_source_and_transient_preference_stay_separate_in_review():
    mood={**MOOD,'assessment':{**MOOD['assessment'],'source':'user','response_strategy':'practical'},'support_preference':'listen'}
    text='うん、聞いているよ。';judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text,kind='nonfactual')))
    generate([text],judge,mood=mood)
    evidence=judge.review.call_args.args[2]
    current=next(x['data'] for x in evidence if x['id']=='emotion_current')
    policy=next(x['data'] for x in evidence if x['id']=='emotion_policy')
    assert current=={'labels':['sadness'],'source':'user'}
    assert policy['player_preference']=='listen' and policy['reply_locale']=='ja-JP'
    assert 'private synthetic' not in json.dumps(evidence)
    assert mood['assessment']['response_strategy']=='practical'


def test_interpreted_self_report_does_not_expose_placeholder_intensity():
    mood={**MOOD,'assessment':{**MOOD['assessment'],'basis':'self_report'}}
    view=voice.assessment_view(mood)
    assert view['source']=='model' and view['basis']=='self_report' and 'intensity' not in view


def test_control_policy_is_not_accepted_as_emotion_fact_evidence():
    text='君は悲しいんだよ。'
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text,ids=['emotion_policy'])))
    (reply,guarded,status),model=generate([text],judge)
    assert guarded and reply==voice.fallback(MOOD,SETTINGS,'ja-JP')
    assert status['status']=='unavailable' and status['failure']=='unknown_evidence'
    model.generate.assert_awaited_once()


def test_attributed_doctor_history_is_not_the_character_diagnosing():
    text='医師にそう診断されたことがあるんだね。'
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text,ids=['user_0'])))
    (reply,guarded,_),model=generate([text],judge,user_text='以前、医師にうつ病と診断されたことがあります。')
    assert reply==text and not guarded;model.generate.assert_awaited_once()


def test_latest_denial_not_overridden_by_old_emotion_reference():
    bad='君は本当は悲しいんだよ。';good='わかった、決めつけないよ。話したいことを聞かせて。'
    judge=SimpleNamespace(review=AsyncMock(side_effect=[verdict(bad,'revise'),verdict(good,kind='nonfactual')]))
    (reply,guarded,_),_=generate([bad,good],judge,user_text='悲しくないよ。')
    assert reply==good and guarded


@pytest.mark.parametrize('failure',['timeout','invalid','low_confidence','unknown_evidence'])
def test_failed_review_returns_safe_language_without_retry(failure):
    text='うん、聞いているよ。'
    value=verdict(text,kind='nonfactual')
    if failure=='invalid':value={'invalid':'synthetic'}
    if failure=='low_confidence':value['confidence']=.2
    if failure=='unknown_evidence':value=verdict(text,ids=['foreign'])
    judge=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()) if failure=='timeout' else AsyncMock(return_value=value))
    (reply,guarded,status),model=generate([text],judge)
    assert reply==voice.fallback(MOOD,SETTINGS,'ja-JP') and guarded
    assert status['status'] in ('unavailable','uncertain')
    model.generate.assert_awaited_once();judge.review.assert_awaited_once()


def test_disabled_review_uses_safe_language_and_never_calls_judge():
    judge=SimpleNamespace(review=AsyncMock())
    (reply,_,status),_=generate(['unreviewed'],judge,review_enabled=False)
    assert reply==voice.fallback(MOOD,SETTINGS,'ja-JP') and status['status']=='emotion_safe_fallback'
    judge.review.assert_not_awaited()


def test_disabled_emotion_never_sends_a_stale_reference_to_review():
    text='こんにちは。';judge=SimpleNamespace(review=AsyncMock())
    (reply,guarded,_),_=generate([text],judge,settings={**SETTINGS,'enabled':False})
    assert reply==text and not guarded
    judge.review.assert_not_awaited()


def test_combined_weather_listen_fallback_retains_facts_without_new_advice():
    weather={'status':'ok','source':'mock','kind':'current','temperature_c':15}
    (reply,_,status),_=generate(['unreviewed'],weather=weather)
    assert reply.startswith('これはデモの天気だよ。そちらは今、推定で15度くらい。')
    assert reply.endswith(voice.fallback(MOOD,SETTINGS,'ja-JP'))
    assert '上着' not in reply and status['status']=='weather_safe_fallback'


def test_combined_care_does_not_allow_accept_to_override_weather_numeric_checks():
    text='今は80度くらいだよ。'
    weather={'status':'ok','source':'mock','kind':'current','temperature_c':15}
    judge=SimpleNamespace(review=AsyncMock(return_value=verdict(text,ids=['weather_current'])))
    (reply,guarded,status),_=generate([text,text],judge,weather=weather)
    assert guarded and status['status']=='fallback' and '15度' in reply and '80度' not in reply


@pytest.mark.parametrize('mode',['companion','audit'])
@pytest.mark.parametrize('weather_mode',['semantic','legacy'])
def test_sdk_review_prompt_composition_only_mock_transport(mode,weather_mode):
    text='うん、話を聞かせて。';calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        prompt=body['messages'][0]['content'];data=json.loads(body['messages'][1]['content'])
        assert voice.REVIEW_PROMPT_EXTRA in prompt
        assert (voice.WEATHER_REVIEW in prompt)==(weather_mode=='semantic')
        assert next(x['data'] for x in data['evidence'] if x['id']=='emotion_policy')['reply_locale']=='ja-JP'
        result={'confidence':.95,'role_issues':[],'units':[{'id':u['id'],'kind':'nonfactual','verdict':'not_applicable',
            'evidence_ids':[]} for u in data['units']]}
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(result)}}]})
    async def check():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key',dialogue_mode=mode,
                weather_understanding_mode=weather_mode,emotion_understanding_mode='semantic')
            p=voice.EmotionAnalysisProvider(settings,client)
            evidence=evidence_bundle([{'role':'user','content':'合成相談'}],[],None,None)
            evidence.append({'id':'emotion_policy','kind':'emotion_policy','data':voice.policy(MOOD,SETTINGS,'ja-JP')})
            return await review_reply(p,text,[],evidence)
    assert asyncio.run(check()).status=='accept' and len(calls)==1

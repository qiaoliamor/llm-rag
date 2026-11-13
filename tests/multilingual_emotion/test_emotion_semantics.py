"""Synthetic semantic contracts, not measured emotion-recognition quality."""
import asyncio
import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.config import Settings
from app.emotion import DEFAULTS, EmotionState, Estimate, decorate
from app import emotion_understanding as e

CONFIG={**DEFAULTS,'enabled':True}


def plan(report=None,**kw):
    return {'use_emotion':'allow','confidence':.95,'report':report,'shift':False,'request_analysis':False,
            'preference':None,'preference_source':None,**kw}


def report(text,labels):return {'source_text':text,'labels':labels}
def estimate(labels=None,ids=None,**kw):
    return {'labels':labels or ['sadness'],'intensity':.7,'confidence':.9,'evidence_message_ids':ids if ids is not None else ['u1'],
            'response_strategy':'listen',**kw}


def provider(value=None):
    return SimpleNamespace(decide=AsyncMock(return_value=value or plan()),analyze=AsyncMock(return_value=estimate()))


def run(p,message='合成の会話',state=None,config=None,history=None,**kw):
    return asyncio.run(e.assess(p,state or EmotionState(),config or CONFIG,
        history or [{'role':'user','content':message,'id':'u1'}],**kw))


@pytest.mark.parametrize('text,labels',[
    ('悲しいです',['sadness']),('我很难过',['sadness']),('うれしいけど緊張もしてる',['joy','anxiety']),
    ('我很开心也很紧张',['joy','anxiety']),('悲しくない',['unknown']),('我并不难过',['unknown']),
    ('悲しくない、ただ疲れてる',['tired']),('我不是难过，只是累了',['tired']),
])
def test_exact_reports_remain_model_interpretations(text,labels):
    p=provider(plan(report(text,labels)));r=run(p,text)
    assert r['status']=='self_report' and r['assessment']['labels']==labels
    assert r['assessment']['source']=='model' and r['assessment']['basis']=='self_report'
    assert r['assessment']['confidence']==.95 and r['assessment']['evidence_message_ids']==['u1']
    assert '"intensity"' not in e.emotion_prompt(r,CONFIG)
    p.analyze.assert_not_awaited()


@pytest.mark.parametrize('text',['こんにちは','你好','友達が悲しいと言った','朋友说很难过','「悲しい」と歌っていた','もし失敗したら悲しいだろうね'])
def test_no_signal_before_interval_never_runs_estimation(text):
    p=provider();assert run(p,text)['status']=='waiting';p.analyze.assert_not_awaited()


@pytest.mark.parametrize('updates',[
    {'confidence':float('nan')},{'confidence':True},{'extra':'unexpected'},
    {'report':report('invented',['sadness'])},{'report':report('合成',['unknown','joy'])},
    {'report':report('合成',['tired','tired'])},{'preference':'listen'},
    {'preference':'listen','preference_source':'invented'},
    {'use_emotion':'decline','request_analysis':True},{'shift':'yes'},
])
def test_invalid_plan_no_analysis_or_regex_fallback(updates):
    p=provider(plan(**updates));assert run(p)['status']=='unavailable';p.analyze.assert_not_awaited()


def test_blank_self_report_source_is_not_evidence():
    p=provider(plan(report(' ',['sadness'])))
    assert run(p,'合成 の会話')['status']=='unavailable'
    p.analyze.assert_not_awaited()


def test_schedule_interval_cooldown_and_shift_stays_program_controlled():
    state=EmotionState();p=provider()
    assert run(p,state=state)['status']=='waiting'
    state.turn=2
    assert run(p,state=state)['status']=='analyzed' and state.last_attempt==3
    state.remember(decorate(Estimate(**estimate()),'model',3),3)
    state.turn=3;p.decide.return_value=plan(shift=True,request_analysis=True)
    assert run(p,state=state)['assessment'] is None  # cooldown cannot be overridden
    assert state.assessment is None and p.analyze.await_count==1
    state.turn=4
    assert run(p,state=state)['status']=='analyzed' and p.analyze.await_count==2


def test_failed_estimation_still_consumes_cooldown_without_retry():
    state=EmotionState();p=provider(plan(request_analysis=True));p.analyze.side_effect=TimeoutError()
    assert run(p,state=state)['status']=='unavailable' and state.last_attempt==1
    assert run(p,state=state)['status']=='waiting'
    assert p.decide.await_count==2 and p.analyze.await_count==1


def test_manual_correction_protected_and_transient_preference_does_not_mutate():
    state=EmotionState();manual=decorate(Estimate(**estimate(['neutral'],[],response_strategy='practical')), 'user',0);state.remember(manual,0)
    p=provider(plan(preference='listen',preference_source='話だけ聞いて'))
    r=run(p,'話だけ聞いて',state=state)
    assert r['status']=='user_override' and r['assessment']['labels']==['neutral']
    assert r['support_preference']=='listen' and r['assessment']['response_strategy']=='practical' and manual['response_strategy']=='practical'
    assert '"player_preference": "listen"' in e.emotion_prompt(r,CONFIG)
    p.analyze.assert_not_awaited()
    p.decide.return_value=plan(report('今は疲れた',['tired']))
    r=run(p,'今は疲れた',state=state)
    assert r['status']=='self_report' and r['assessment']['source']=='model'
    assert state.assessment is None


@pytest.mark.parametrize('source',['user','model'])
def test_decision_failure_no_stale_context_but_manual_correction_retained(source):
    state=EmotionState();state.remember(decorate(Estimate(**estimate()),source,0),0)
    p=provider();p.decide.side_effect=TimeoutError()
    r=run(p,state=state)
    assert r=={'status':'unavailable','assessment':None}
    assert (state.assessment is not None)==(source=='user')
    p.decide.assert_awaited_once();p.analyze.assert_not_awaited()


@pytest.mark.parametrize('use',['decline','uncertain'])
def test_decline_or_uncertain_never_analyzes(use):
    state=EmotionState();state.remember(decorate(Estimate(**estimate()),'model',0),0)
    p=provider(plan(use_emotion=use));r=run(p,state=state)
    assert r['assessment'] is None and state.assessment is None;p.analyze.assert_not_awaited()


@pytest.mark.parametrize('updates',[
    {'extra':'unexpected'},{'evidence_message_ids':['assistant']},{'evidence_message_ids':['u1','u1']},
    {'evidence_message_ids':[]},{'labels':['neutral','anger']},{'confidence':True},{'intensity':float('inf')},
])
def test_analysis_schema_and_user_evidence_validation(updates):
    p=provider(plan(request_analysis=True));p.analyze.return_value=estimate(**updates)
    r=run(p)
    assert r['status']=='unavailable' and r['assessment'] is None
    p.analyze.assert_awaited_once()


def test_low_confidence_unknown_and_preference_projection():
    p=provider(plan(request_analysis=True,preference='listen',preference_source='先听我说'))
    p.analyze.return_value=estimate(confidence=.3)
    r=run(p,'先听我说')
    assert r['assessment']['labels']==['unknown']
    text=e.emotion_prompt(r,CONFIG)
    assert '"player_preference": "listen"' in text and '不是玩家按钮确认' in text
    assert 'evidence_message_ids' not in text and 'observed_at' not in text
    assert CONFIG['preference']=='ask'


def test_disabled_and_bounded_shared_deadline():
    p=provider(plan(request_analysis=True))
    assert run(p,config={**CONFIG,'enabled':False})['status']=='disabled';p.decide.assert_not_awaited()
    async def slow(data):await asyncio.sleep(.05)
    p.decide.side_effect=slow
    assert run(p,timeout=.001)['status']=='unavailable';p.analyze.assert_not_awaited()


def test_exhausted_decision_budget_never_starts_estimation(monkeypatch):
    ticks=iter([0,0,7]);monkeypatch.setattr(e,'monotonic',lambda:next(ticks))
    p=provider(plan(request_analysis=True))
    assert run(p,timeout=6)['status']=='unavailable'
    p.analyze.assert_not_awaited()


def test_window_projects_text_only_and_self_report_uses_full_current_source():
    p=provider()
    history=[{'role':'user','content':'合成'+str(i),'id':'u'+str(i),'weather':{'secret':'not sent'}} for i in range(20)]
    run(p,history=history)
    data=p.decide.call_args.args[0]
    assert len(data['recent_dialogue'])==6 and 'secret' not in json.dumps(data)
    assert data['current_message']=='合成19' and data['current_message_id']=='u19'


def test_cache_expiry_not_extended_by_reuse():
    state=EmotionState();a={**decorate(Estimate(**estimate()),'model',0),'basis':'self_report'};state.remember(a,0)
    p=provider();assert run(p,state=state)['status']=='cached'
    state.expires=time.monotonic()-1
    assert run(p,state=state)['status']=='waiting'
    state.expires=time.monotonic()+600;state.turn=5
    assert run(p,state=state)['status']=='analyzed'  # six turns old, not protected


def test_sdk_only_mock_transport_for_decision_and_estimate():
    calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        prompt=body['messages'][0]['content']
        value=plan(request_analysis=True) if prompt==e.DECISION_PROMPT else estimate()
        assert prompt in (e.DECISION_PROMPT,e.ANALYSIS_PROMPT)
        assert body['response_format']['type']=='json_schema'
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(value)}}]})
    async def check():
        settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key')
        # The SDK owns/closes each supplied client, as in production's per-call
        # clients. Do not reuse a closed MockTransport client across two parses.
        class TransportProvider:
            async def invoke(self,method,data):
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    return await getattr(e.ModelEmotionUnderstanding(settings,client),method)(data)
            async def decide(self,data):return await self.invoke('decide',data)
            async def analyze(self,data):return await self.invoke('analyze',data)
        return await e.assess(TransportProvider(),EmotionState(),CONFIG,[{'role':'user','content':'一緒に話して','id':'u1'}])
    assert asyncio.run(check())['status']=='analyzed' and len(calls)==2

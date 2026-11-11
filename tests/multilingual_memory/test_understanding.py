"""Synthetic provider contracts, not measurements of model understanding accuracy."""
import asyncio
import copy
import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from app.config import Settings
from app.memory_understanding import (
    DateMeaning, MemoryPlan, ModelMemoryUnderstanding, PLAN_PROMPT,
    SELECT_PROMPT, understand, select_evidence,
)

NOW=datetime(2026,11,11,0,0,tzinfo=timezone.utc)


def date_spec(kind='unknown',expression='',**kw):
    return {'kind':kind,'expression':expression,'absolute':None,'days':None,'week_offset':None,'weekday':None,**kw}


def proposal(text,date=None,**kw):
    return {'source_text':text,'subject':'user','actuality':'asserted','category':'event','slot':'appointment',
            'confidence':.95,'date':date or date_spec(),**kw}


def plan(*items,need=False,query='',reason=None,**kw):
    return {'memory_use':'allow','need_memory':need,'query':query,'target_slots':[],
            'reason':reason or ('personal_history_needed' if need else 'no_cross_session_need'),
            'confidence':.95,'candidates':list(items),**kw}


def analyze(message,value,**kw):
    provider=SimpleNamespace(analyze=AsyncMock(return_value=value))
    return asyncio.run(understand(provider,message,[],enabled=True,tz='Asia/Tokyo',now=NOW,**kw)),provider


@pytest.mark.parametrize('message,meaning,expected',[
    ('我明天有面试。',date_spec('relative_days','明天',days=1),'2026-11-12'),
    ('明日、面接があります。',date_spec('relative_days','明日',days=1),'2026-11-12'),
    ('あした面接があります。',date_spec('relative_days','あした',days=1),'2026-11-12'),
    ('明後日、面接があります。',date_spec('relative_days','明後日',days=2),'2026-11-13'),
    ('我后天有面试。',date_spec('relative_days','后天',days=2),'2026-11-13'),
    ('昨日は面接でした。',date_spec('relative_days','昨日',days=-1),'2026-11-10'),
    ('来週火曜日に面接があります。',date_spec('weekday','来週火曜日',week_offset=1,weekday=1),'2026-11-17'),
    ('我下周二有面试。',date_spec('weekday','下周二',week_offset=1,weekday=1),'2026-11-17'),
    ('再来週の月曜日に面接があります。',date_spec('weekday','再来週の月曜日',week_offset=2,weekday=0),'2026-11-23'),
    ('今週金曜日に面接があります。',date_spec('weekday','今週金曜日',week_offset=0,weekday=4),'2026-11-13'),
    ('2027年1月2日に面接があります。',date_spec('absolute','2027年1月2日',absolute='2027-01-02'),'2027-01-02'),
    ('来月、面接があります。',date_spec('unknown','来月'),None),
    ('火曜日に面接があります。',date_spec('unknown','火曜日'),None),
    ('我周末有面试。',date_spec('unknown','周末'),None),
])
def test_exact_source_and_program_date_arithmetic(message,meaning,expected):
    result,provider=analyze(message,plan(proposal(message,meaning)))
    assert result.status=='ready' and result.candidates[0].fact==message
    assert result.candidates[0].metadata.event_date==expected
    assert provider.analyze.await_count==1
    assert provider.analyze.call_args.args[0]['today']=='2026-11-11'


@pytest.mark.parametrize('tz,expected',[('Asia/Tokyo','2027-01-02'),('UTC','2027-01-01')])
def test_timezone_anchor_and_year_rollover(tz,expected):
    provider=SimpleNamespace(analyze=AsyncMock(return_value=plan(proposal('明日、面接です。',date_spec('relative_days','明日',days=1)))))
    r=asyncio.run(understand(provider,'明日、面接です。',[],enabled=True,tz=tz,now=datetime(2026,12,31,18,tzinfo=timezone.utc)))
    assert r.candidates[0].metadata.event_date==expected


@pytest.mark.parametrize('meaning,expected',[
    (date_spec('relative_days','明日',days=1),'2028-02-29'),
    (date_spec('relative_days','明後日',days=2),'2028-03-01'),
])
def test_leap_year(meaning,expected):
    assert DateMeaning.model_validate(meaning).resolve(datetime(2028,2,28).date())==expected


@pytest.mark.parametrize('mutation',[
    lambda p:p.update(confidence=True),lambda p:p.update(confidence=float('nan')),
    lambda p:p.update(unknown_field='bad'),lambda p:p.update(query='unused'),
    lambda p:p.update(need_memory=True,query='x',reason='uncertain'),
    lambda p:p.update(memory_use='decline'),lambda p:p['candidates'][0].update(source_text='勝手に変更した文'),
    lambda p:p['candidates'][0].update(category='profile'),
    lambda p:p['candidates'][0]['date'].update(kind='absolute',expression='明日',absolute='2026-02-30'),
    lambda p:p['candidates'][0]['date'].update(kind='relative_days',expression='明後日',days=2),
    lambda p:p['candidates'][0]['date'].update(days=1),
    lambda p:p['candidates'].append(copy.deepcopy(p['candidates'][0])),
])
def test_invalid_structure_source_date_and_permission_fail_closed(mutation):
    value=plan(proposal('明日、面接です。'));mutation(value)
    result,provider=analyze('明日、面接です。',value)
    assert result.status=='unavailable' and result.plan is None and not result.candidates
    provider.analyze.assert_awaited_once()


@pytest.mark.parametrize('subject,actuality',[('other','asserted'),('user','quoted'),('user','hypothetical'),('uncertain','asserted')])
def test_other_people_quotes_hypotheticals_and_unknown_subject_are_not_auto_candidates(subject,actuality):
    r,_=analyze('友人が「明日は面接」と言いました。',plan(proposal('友人が「明日は面接」と言いました。',subject=subject,actuality=actuality)))
    assert r.status=='ready' and not r.candidates


@pytest.mark.parametrize('permission,status',[('decline','declined'),('uncertain','uncertain')])
def test_semantic_decline_or_uncertainty_cannot_read_or_propose(permission,status):
    r,_=analyze('前の話は使わず、覚えないで。',plan(memory_use=permission,reason='declined' if permission=='decline' else 'uncertain'))
    assert r.status==status and r.plan is None and not r.candidates


def test_disabled_never_calls_provider_and_failure_does_not_retry():
    provider=SimpleNamespace(analyze=AsyncMock(side_effect=TimeoutError('synthetic')))
    r=asyncio.run(understand(provider,'我明天有面试',[],enabled=False,tz='Asia/Tokyo'))
    assert r.status=='disabled';provider.analyze.assert_not_awaited()
    r=asyncio.run(understand(provider,'明日、面接です。',[],enabled=True,tz='Asia/Tokyo'))
    assert r.status=='unavailable';provider.analyze.assert_awaited_once()


@pytest.mark.parametrize('ids,confidence,expected',[
    (['m1'],.95,['m1']),([], .95,[]),(['foreign'],.95,[]),(['m1','m1'],.95,[]),(['m1'],.4,[]),
])
def test_semantic_selection_whitelist_confidence_no_answer_and_duplicates(ids,confidence,expected):
    provider=SimpleNamespace(select=AsyncMock(return_value={'ids':ids,'confidence':confidence}))
    candidates=[{'id':'m1','fact':'来週、東京で面接。','event_date':'2026-11-17'}]
    items,status=asyncio.run(select_evidence(provider,'面接',[],candidates))
    assert [m['id'] for m in items]==expected
    provider.select.assert_awaited_once()


def test_manual_metadata_requires_whole_source_and_cannot_retrieve():
    r,_=analyze('昨日、面接に合格しました。',plan(proposal('面接に合格しました。')),operation='manual_metadata')
    assert r.status=='unavailable'
    r,_=analyze('明日、面接です。',plan(proposal('明日、面接です。'),need=True,query='面接'),operation='manual_metadata')
    assert r.status=='unavailable'


def test_actual_structured_sdk_contract_uses_fixed_prompt_and_mock_transport():
    value=plan(proposal('明日、面接です。',date_spec('relative_days','明日',days=1)))
    requests=[]
    def handler(request):
        body=json.loads(request.content);requests.append(body)
        assert body['messages'][0]['content']==PLAN_PROMPT
        assert json.loads(body['messages'][1]['content'])['current_message']=='明日、面接です。'
        assert body['response_format']['type']=='json_schema'
        return httpx.Response(200,json={'id':'synthetic','object':'chat.completion','created':0,'model':'synthetic',
            'choices':[{'index':0,'finish_reason':'stop','message':{'role':'assistant','content':json.dumps(value,ensure_ascii=False)}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key='synthetic-not-a-key')
            provider=ModelMemoryUnderstanding(settings,client)
            return await understand(provider,'明日、面接です。',[],enabled=True,tz='Asia/Tokyo',now=NOW)
    result=asyncio.run(run())
    assert result.status=='ready' and result.candidates[0].metadata.event_date=='2026-11-12'
    assert len(requests)==1
    assert '日本語' in PLAN_PROMPT and '中文' in PLAN_PROMPT
    assert '没有答案' in SELECT_PROMPT


def test_only_recent_text_is_sent_not_tool_snapshots_or_private_extensions():
    history=[{'role':'assistant','content':'合成の短い会話','weather':{'location':'synthetic hidden place'},'private':'synthetic hidden extension'}]
    provider=SimpleNamespace(analyze=AsyncMock(return_value=plan()),select=AsyncMock(return_value={'ids':[],'confidence':.95}))
    asyncio.run(understand(provider,'こんにちは',history,enabled=True,tz='Asia/Tokyo',now=NOW))
    assert provider.analyze.call_args.args[0]['recent_dialogue']==[{'role':'assistant','content':'合成の短い会話'}]
    asyncio.run(select_evidence(provider,'面接',history,[{'id':'m1','fact':'面接','event_date':None}]))
    assert provider.select.call_args.args[0]['recent_dialogue']==[{'role':'assistant','content':'合成の短い会話'}]


def test_date_outside_representable_retention_range_is_rejected():
    result,_=analyze('9999年12月31日に面接。',plan(proposal('9999年12月31日に面接。',date_spec('absolute','9999年12月31日',absolute='9999-12-31'))))
    assert result.status=='unavailable' and not result.candidates

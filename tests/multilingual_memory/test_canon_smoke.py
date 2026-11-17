"""Offline runner contracts; all model judgments here are authored, not predictions."""
import asyncio
import json
import os
import subprocess
import sys
import pytest
from app.config import Settings
from scripts import retest_memory_canon as smoke


def setup(monkeypatch,failed=False):
    class Analyst:
        def __init__(self,settings):pass
        async def analyze(self,data):
            return {'memory_use':'allow','need_memory':True,'query':'妹 面接','target_slots':['history'],
                'reason':'personal_history_needed','confidence':.95,'candidates':[]}
        async def select(self,data):
            return {'ids':[m['id'] for m in data['candidates'] if m['fact'].startswith('妹')],'confidence':.95}
    class Judge:
        def __init__(self,settings):pass
        async def review(self,reply,history,evidence):
            if failed:
                error=RuntimeError('private-provider-detail');error.status_code=503;raise error
            factual=reply.startswith('僕は30') or reply.startswith('妹さん')
            return {'decision':'revise' if factual else 'accept','confidence':.95,'role_issues':[],
                'segments':[{'text':reply,'kind':'assertion' if factual else 'nonfactual',
                    'verdict':'contradicted' if factual else 'not_applicable','evidence_ids':[],
                    'reason':'contradiction' if factual else 'nonfactual'}]}
    monkeypatch.setattr(smoke,'ModelMemoryUnderstanding',Analyst)
    monkeypatch.setattr(smoke,'FactAnalysisProvider',Judge)
    return Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///must-not-open.sqlite3')


def test_fixed_prior_failures_use_five_calls_no_generation_or_repeated_cn_selection(monkeypatch):
    r=asyncio.run(smoke.run(setup(monkeypatch)))
    assert r['attempted_calls']==r['max_calls']==5 and not r['unattempted_ids']
    assert [c['stage'] for c in r['calls']]==['plan','selection','review','review','review']
    ja,canon,zh=r['results']
    assert ja['selected_ids']==['sister'] and ja['selection_reference_match']
    assert ja['review_status']==canon['review_status']=='revise' and zh['review_status']=='accept'
    assert zh['selection_status']=='prior_selection_reused'
    assert r['assessment']=='not_assessed'
    assert 'must-not-open.sqlite3' not in json.dumps(r)


def test_503_is_recorded_once_and_remaining_cases_not_attempted(monkeypatch):
    r=asyncio.run(smoke.run(setup(monkeypatch,failed=True)))
    assert r['attempted_calls']==3 and len(r['results'])==1
    assert r['results'][0]['review_failure']=='upstream_unavailable'
    assert r['unattempted_ids']==['ja-canon-conflict','zh-review-503']
    assert 'private-provider-detail' not in str(r)


def test_focus_ledger_does_not_start_sixth_call():
    async def run():
        ledger=smoke.FocusLedger();seen=[]
        async def op():seen.append(True)
        for n in range(5):await ledger.call(str(n),'review',op)
        with pytest.raises(ValueError):await ledger.call('sixth','review',op)
        assert len(seen)==5
    asyncio.run(run())


def test_selection_timeout_is_unavailable_not_successful_empty_selection(monkeypatch):
    settings=setup(monkeypatch)
    original=smoke.ModelMemoryUnderstanding
    class TimedOutSelector(original):
        async def select(self,data):raise TimeoutError('private-synthetic-timeout')
    monkeypatch.setattr(smoke,'ModelMemoryUnderstanding',TimedOutSelector)
    r=asyncio.run(smoke.run(settings,('ja-memory-subject',)))
    row=r['results'][0]
    assert r['attempted_calls']==2 and row['status']=='selection_failed'
    assert row['selection_status']=='unavailable' and row['selected_ids'] is None
    assert row['review_status']=='not_reached'
    assert r['memory_budget']=={'plan_seconds':8,'selection_seconds':8,'total_seconds':16}
    assert 'private-synthetic-timeout' not in str(r)


def test_selection_only_reuses_plan_and_never_calls_successful_query_or_review(monkeypatch):
    settings=setup(monkeypatch);original=smoke.ModelMemoryUnderstanding
    class SelectorOnly(original):
        async def analyze(self,*a):raise AssertionError('must not repeat successful query')
    class NoJudge:
        def __init__(self,*a):raise AssertionError('selection-only must not add review')
    monkeypatch.setattr(smoke,'ModelMemoryUnderstanding',SelectorOnly)
    monkeypatch.setattr(smoke,'FactAnalysisProvider',NoJudge)
    r=asyncio.run(smoke.run(settings,('ja-memory-subject',),selection_only=True))
    assert r['attempted_calls']==r['max_calls']==1
    assert [c['stage'] for c in r['calls']]==['selection']
    row=r['results'][0]
    assert row['selected_ids']==['sister'] and row['selection_reference_match']
    assert row['understanding_status']=='prior_plan_reused' and row['review_status']=='not_reached'


def test_selection_only_cannot_be_used_for_unrelated_cases(monkeypatch):
    with pytest.raises(ValueError):asyncio.run(smoke.run(setup(monkeypatch),('zh-review-503',),selection_only=True))


def test_chinese_503_case_can_be_selected_without_repeating_understanding_or_selection(monkeypatch):
    settings=setup(monkeypatch)
    class Forbidden:
        def __init__(self,*a):raise AssertionError('successful analysis must not be repeated')
    monkeypatch.setattr(smoke,'ModelMemoryUnderstanding',Forbidden)
    r=asyncio.run(smoke.run(settings,('zh-review-503',)))
    assert r['max_calls']==r['attempted_calls']==1 and not r['unattempted_ids']
    assert r['calls'][0]['stage']=='review' and r['results'][0]['review_status']=='accept'


@pytest.mark.parametrize('ids',[(),('unknown',),('zh-review-503','zh-review-503')])
def test_unbounded_or_repeated_cases_rejected_before_calls(monkeypatch,ids):
    with pytest.raises(ValueError):asyncio.run(smoke.run(setup(monkeypatch),ids))


def test_cli_without_live_never_reads_env_or_connects(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    r=subprocess.run([sys.executable,'scripts/retest_memory_canon.py'],env={**os.environ,'PYTHONPATH':str(tmp_path)},capture_output=True,text=True)
    assert r.returncode==2 and '--live required' in r.stderr


@pytest.mark.parametrize('output,expected_status,expected_schema',[
    ({'ids':[],'confidence':.95},'selection_completed','validated'),
    ({'ids':['foreign-secret-id'],'confidence':.95},'selection_failed','validated'),
    ({'ids':[],'confidence':.2},'selection_failed','validated'),
    ({'ids':[],'confidence':'high'},'selection_failed','invalid_structure'),
])
def test_selection_only_preserves_empty_invalid_foreign_and_uncertain_results(monkeypatch,output,expected_status,expected_schema):
    settings=setup(monkeypatch);original=smoke.ModelMemoryUnderstanding
    class Selector(original):
        async def analyze(self,*a):raise AssertionError('must not repeat plan')
        async def select(self,data):return output
    monkeypatch.setattr(smoke,'ModelMemoryUnderstanding',Selector)
    r=asyncio.run(smoke.run(settings,('ja-memory-subject',),selection_only=True))
    row=r['results'][0]
    assert r['attempted_calls']==r['max_calls']==1
    assert row['status']==expected_status and row['selection_schema_status']==expected_schema
    assert row['review_status']=='not_reached' and row.get('injected_memories',[])==[]
    assert row.get('selection_reference_match') is not True
    if expected_status=='selection_failed':assert row['selected_ids'] is None
    else:assert row['selected_ids']==[]  # Valid empty result is distinct from timeout/null.
    assert 'foreign-secret-id' not in json.dumps(r)

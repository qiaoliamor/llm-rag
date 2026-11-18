"""Bounded live runner contracts use synthetic scripted providers, never network."""
import asyncio
import json
import os
import subprocess
import sys
import pytest
from app.config import Settings
from scripts import retest_memory_generalization as live


def setup(monkeypatch,fail_plan=False):
    class Analyst:
        def __init__(self,*a):pass
        async def analyze(self,data):
            if fail_plan:raise TimeoutError('private-error')
            zh='哪里' in data['current_message']
            return {'memory_use':'allow','need_memory':True,'query':'住址' if zh else '犬 名前',
                'target_slots':['residence'] if zh else ['history'],'reason':'personal_history_needed','confidence':.95,'candidates':[]}
        async def select(self,data):
            zh=data['query']=='住址'
            return {'ids':[d['id'] for d in data['candidates'] if zh and d['fact']=='现在住在合成桔梗市。'],'confidence':.95}
    class Generator:
        async def generate(self,history,prompt):
            if '哪里' in history[-1]['content']:
                assert '现在住在合成桔梗市。' in prompt and '以前住在合成青梧市。' not in prompt
                return '记得，现在住在合成桔梗市。'
            return '名前を教えてくれる？'
    class Judge:
        def __init__(self,*a):pass
        async def review(self,text,history,evidence):
            zh=text.startswith('记得')
            return {'decision':'accept','confidence':.95,'role_issues':[],
                'segments':[{'text':text,'kind':'assertion' if zh else 'nonfactual','verdict':'supported' if zh else 'not_applicable',
                    'evidence_ids':[e['id'] for e in evidence if e['id'].startswith('memory_')] if zh else [],
                    'reason':'evidence_supports' if zh else 'nonfactual'}]}
    monkeypatch.setattr(live,'ModelMemoryUnderstanding',Analyst)
    monkeypatch.setattr(live,'build_provider',lambda s:Generator());monkeypatch.setattr(live,'FactAnalysisProvider',Judge)
    return Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///must-not-open.sqlite3')


def test_actual_memory_provider_hooks_and_all_stage_accounting(monkeypatch):
    r=live.run(setup(monkeypatch));assert not r['unattempted_ids'] and not r['blocked']
    assert 6<=r['attempted_calls']<=r['max_calls']==8
    for row in r['results']:
        assert row['memory_stage_source']=='live_model' and row['technical_complete']
        assert row['observations']['plans'] and row['observations']['memory_understanding']['status']=='ready'
        assert row['reply']['assessment_basis']=='unrated'
        assert all(c['stage'] in ('plan','selection','generation','review') for c in r['calls'])
    assert r['results'][0]['candidate']['ids']==r['results'][0]['context']['ids']==['new']
    assert r['results'][1]['context']['ids']==[]
    assert r['assessment']=='not_assessed' and 'must-not-open.sqlite3' not in json.dumps(r)


def test_plan_timeout_stops_real_calls_before_generation_and_next_case(monkeypatch):
    r=live.run(setup(monkeypatch,True));assert r['attempted_calls']==1
    assert r['calls'][0]['failure']=='timeout_or_cancelled' and r['blocked']
    assert r['unattempted_ids']==['ja-no-answer'] and not r['results'][0]['technical_complete']
    assert r['results'][0]['http_status']==503 and r['results'][0]['state']['saved_messages']==0
    assert 'private-error' not in json.dumps(r)


def test_no_automatic_rewrite_even_if_case_has_unused_budget():
    async def run():
        b=live.Budget(('ja-no-answer',));seen=[]
        async def op():seen.append(1)
        await b.call('ja-no-answer','generation',op)
        with pytest.raises(live.ProviderFailure):await b.call('ja-no-answer','generation',op)
        assert len(seen)==len(b.calls)==1 and b.blocked
    asyncio.run(run())


@pytest.mark.parametrize('ids',[(),('unknown',),('ja-no-answer','ja-no-answer')])
def test_fixed_failure_categories_only_before_any_model_call(monkeypatch,ids):
    with pytest.raises(ValueError):live.run(setup(monkeypatch),ids)


def test_runner_without_live_never_reads_env_or_connects(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    p=subprocess.run([sys.executable,'scripts/retest_memory_generalization.py'],capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(tmp_path)})
    assert p.returncode==2 and '--live required' in p.stderr

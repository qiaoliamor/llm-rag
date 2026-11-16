"""The live CLI is tested with fake providers only; no local credentials."""
import asyncio
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.config import Settings
from scripts import retest_same_language_memory as smoke


def setup(monkeypatch,fail=None):
    class Analyst:
        def __init__(self,settings):pass
        async def analyze(self,data):
            if fail=='plan':raise TimeoutError('synthetic-private-error')
            zh=data['current_message'].startswith('妹妹')
            return {'memory_use':'allow','need_memory':True,'query':'妹妹 面试' if zh else '犬 名前',
                'target_slots':[],'reason':'personal_history_needed','confidence':.95,'candidates':[]}
        async def select(self,data):
            return {'ids':[m['id'] for m in data['candidates'] if m['fact'].startswith('妹妹')],'confidence':.95}
    class Judge:
        def __init__(self,settings):pass
        async def review(self,reply,history,evidence):
            return {'decision':'accept','confidence':.95,'role_issues':[],
                'segments':[{'text':reply,'kind':'nonfactual','verdict':'not_applicable','evidence_ids':[],'reason':'nonfactual'}]}
    async def generate(history,prompt):
        if fail=='generation':raise TimeoutError('synthetic-private-error')
        return '名前を聞かせて。' if not history[-1]['content'].startswith('妹妹') else '妹妹面试的是合成桔梗社。'
    monkeypatch.setattr(smoke,'ModelMemoryUnderstanding',Analyst)
    monkeypatch.setattr(smoke,'FactAnalysisProvider',Judge)
    monkeypatch.setattr(smoke,'build_provider',lambda settings:SimpleNamespace(generate=generate))
    return Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///must-not-open.sqlite3')


def test_bounded_smoke_uses_synthetic_confirmed_memories_and_aliases_only(monkeypatch):
    r=asyncio.run(smoke.run(setup(monkeypatch)))
    assert r['attempted_cases']==2 and r['attempted_calls']<=8
    assert all(x['status']=='completed' and x['reference_selection_match'] for x in r['results'])
    assert r['results'][0]['selected_ids']==[]
    assert r['results'][1]['selected_ids']==['sister']
    assert [m['id'] for m in r['results'][1]['injected_memories']]==['sister']
    assert r['assessment']=='not_assessed'


@pytest.mark.parametrize('failure',['plan','generation'])
def test_service_failure_stops_all_later_real_attempts_and_preserves_elapsed(monkeypatch,failure):
    r=asyncio.run(smoke.run(setup(monkeypatch,failure)))
    assert r['attempted_cases']==1 and r['results'][0]['status']!='completed'
    assert any(x['status']=='failed' for x in r['calls'])
    assert all('elapsed_seconds' in x for x in r['calls'])
    assert 'synthetic-private-error' not in str(r)


def test_ledger_refuses_budget_before_invoking_provider():
    async def run():
        ledger=smoke.Ledger();operation=AsyncMock()
        for _ in range(4):await ledger.call('one','synthetic',operation)
        with pytest.raises(ValueError):await ledger.call('one','synthetic',operation)
        for _ in range(4):await ledger.call('two','synthetic',operation)
        with pytest.raises(ValueError):await ledger.call('three','synthetic',operation)
        assert operation.await_count==8
    asyncio.run(run())


def test_without_explicit_live_flag_cli_never_reads_configuration(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    import os
    env={**os.environ,'PYTHONPATH':str(tmp_path)}
    r=subprocess.run([sys.executable,'scripts/retest_same_language_memory.py'],env=env,capture_output=True,text=True)
    assert r.returncode==2 and '--live required' in r.stderr

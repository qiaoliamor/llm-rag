"""Frozen empty-selection review tail; all providers scripted, no real network."""
import json
import os
import subprocess
import sys
from unittest.mock import patch
import pytest
from pydantic import BaseModel,ValidationError
from app.config import Settings
from app.dialogue import ProviderFailure
from app.semantic_review import ModelAnalysisProvider
from scripts import retest_japanese_review as tail


def setup(monkeypatch,mode='accept'):
    class Generator:
        async def generate(self,history,prompt):
            if mode=='generation_failure':raise ProviderFailure('timeout','synthetic',504)
            assert '本轮没有选中' in prompt
            return '名前を聞かせてくれる？'
    class Judge:
        diagnostics=[];prompt_lengths=[123]
        def __init__(self,*a):pass
        async def review(self,text,history,evidence):
            assert not any(e['id'].startswith('memory_') for e in evidence)
            if mode=='invalid_output':raise ValueError('private-invalid')
            if mode=='timeout':raise TimeoutError('private-timeout')
            bad=mode=='revise'
            return {'decision':'revise' if bad else 'accept','confidence':.95,'role_issues':[],
                'segments':[{'text':text,'kind':'assertion' if bad else 'nonfactual','verdict':'unsupported' if bad else 'not_applicable',
                    'evidence_ids':[],'reason':'missing_evidence' if bad else 'nonfactual'}]}
    monkeypatch.setattr(tail,'build_provider',lambda s:Generator());monkeypatch.setattr(tail,'DiagnosticJudge',Judge)
    return Settings(_env_file=None,chat_provider='mock')


def test_v5_empty_tail_replays_only_successful_plan_and_empty_selection(monkeypatch):
    r=tail.run(setup(monkeypatch));row=r['result']
    assert r['attempted_calls']==r['max_calls']==2 and not r['blocked']
    assert [c['stage'] for c in r['calls']]==['generation','review']
    assert row['memory_stage_source']=='replayed_reference_not_current_prediction'
    assert row['selection']['reference_match'] is True and row['context']['ids']==[]
    assert row['observations']['plans']==[] and row['technical_complete']
    assert row['observations']['published_reply']=='名前を聞かせてくれる？'
    assert row['reply']['assessment_basis']=='unrated' and r['assessment']=='not_assessed'


@pytest.mark.parametrize('mode,count,status',[('generation_failure',1,504),('invalid_output',2,200),('timeout',2,503),('revise',2,503)])
def test_failed_tail_never_retries_or_rewrites(monkeypatch,mode,count,status):
    r=tail.run(setup(monkeypatch,mode));row=r['result']
    assert r['attempted_calls']==count and not row['technical_complete']
    assert row['http_status']==status
    assert len([c for c in r['calls'] if c['stage']=='generation'])==1
    if mode=='invalid_output':
        assert row['semantic_review']['status']=='unavailable'
        assert row['observations']['published_reply']!='名前を聞かせてくれる？'
        assert row['state']['saved_messages']==2
    else:assert row['state']['saved_messages']==0
    assert ('private-' not in json.dumps(r))


def test_diagnostics_export_codes_without_invalid_input(monkeypatch):
    class Data(BaseModel):required:int
    async def fail(*args,**kwargs):return Data.model_validate({'required':'private-synthetic-value'})
    monkeypatch.setattr(ModelAnalysisProvider,'parse',fail)
    judge=tail.DiagnosticJudge(Settings(_env_file=None,chat_provider='mock'))
    import asyncio
    with pytest.raises(ValidationError):asyncio.run(judge.parse(Data,'',{'evidence':[]},1,100))
    assert judge.diagnostics==[{'stage':'schema','codes':['int_parsing']}]
    assert 'private-synthetic-value' not in json.dumps(judge.diagnostics)


def test_no_live_does_not_read_env_or_connect(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    result=subprocess.run([sys.executable,'scripts/retest_japanese_review.py'],capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(tmp_path)})
    assert result.returncode==2 and '--live required' in result.stderr

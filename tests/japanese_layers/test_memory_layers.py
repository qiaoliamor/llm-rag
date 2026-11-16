"""Four-layer observations and deliberate semantic false accepts, not model scores."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from app import japanese_memory_layers as e


@pytest.fixture(scope='module')
def report():return e.evaluate()


def row(report,case,probe='reference'):
    return next(r for r in report['per_probe'] if r['case']==case and r['probe']==probe)


def test_all_attempts_and_injected_semantic_failures_remain_in_report(report):
    assert report['cases']==8 and report['attempted']==31
    assert report['model_calls']==0 and report['assessment']=='not_assessed'
    assert report['configuration']['reply']=='semantic' and report['configuration']['growth_enabled']
    assert report['reference_probes']=={'attempted':8,'reference_answer_complete':7,'candidate_misses':1}
    assert report['published_with_unsupported_claims']==5
    assert report['projection_mismatches']==0 and report['published_unrated']==0
    assert report['http_status_counts']=={'200':27,'504':1,'503':1,'409':2}


def test_no_answer_candidates_do_not_mean_injection_but_wrong_known_id_can_pass(report):
    correct=row(report,'no-answer')
    assert correct['candidate']['ids'] and correct['selection']['ids']==[]
    assert correct['context']['ids']==[] and correct['reply']['unsupported_claims']==0
    wrong=row(report,'no-answer','wrong-known-accept')
    assert wrong['selection']['ids']==['cat'] and wrong['selection']['reference_match'] is False
    assert wrong['context']['projection_match'] is True and wrong['context']['reference_compatible'] is False
    assert wrong['reply']['unsupported_claims']==1 and wrong['http_status']==200


@pytest.mark.parametrize('case',['no-answer','subject-sister','current-correction','childhood-vs-current'])
def test_rewrite_protects_reply_without_rewriting_bad_selection_history(report,case):
    wrong=row(report,case,'wrong-known-rewrite')
    assert wrong['selection']['reference_match'] is False
    assert wrong['reply']['fixture_id']=='safe' and wrong['reply']['unsupported_claims']==0
    assert wrong['calls']['generation_calls']==wrong['calls']['review_calls']==2


def test_current_and_persisted_corrections_have_distinct_observed_paths(report):
    current=row(report,'current-correction')
    assert current['candidate']['ids'] is None and current['selection']['status']=='not_requested'
    assert current['context']['ids']==[] and current['reply']['reference_answer_complete']
    persisted=row(report,'persisted-correction')
    assert persisted['candidate']['ids']==['new'] and persisted['context']['ids']==['new']
    assert 'old' not in persisted['selection']['ids']
    assert row(report,'persisted-correction','old-id-after-correction')['selection']['status']=='unavailable'


def test_cross_language_candidate_miss_is_not_hidden_by_safe_fallback(report):
    miss=row(report,'ja-query-zh-memory')
    assert miss['candidate']['ids']==[] and miss['candidate']['recall_at_5']==0
    assert miss['selection']['status']=='empty' and miss['context']['ids']==[]
    assert miss['reply']['assessment_basis']=='fixed_nonfactual_fallback'
    assert miss['reply']['reference_answer_complete'] is False
    positive=row(report,'zh-query-ja-memory')
    assert positive['selection']['ids']==['tea'] and positive['reply']['reference_answer_complete']


def test_source_time_is_reply_error_even_with_correct_selection_and_projection(report):
    r=row(report,'source-time','unsupported-time-accept')
    assert r['selection']['reference_match'] and r['context']['reference_compatible']
    assert r['context']['projection_match'] and r['reply']['unsupported_claims']==1
    assert row(report,'source-time','unsupported-time-rewrite')['reply']['fixture_id']=='safe'


@pytest.mark.parametrize('fault,status',[('outside_id','unavailable'),('duplicate','unavailable'),('malformed','unavailable'),('low_confidence','uncertain'),('timeout','unavailable'),('empty','selected')])
def test_selector_failures_are_empty_context_not_semantic_success(report,fault,status):
    r=row(report,'source-time','selector-'+fault)
    assert r['selection']['status']==status and r['selection']['ids']==[]
    assert r['context']['ids']==[] and r['selection']['reference_match'] is False


@pytest.mark.parametrize('probe,status',[('generation-timeout',504),('review-timeout',503),('revoke-in-flight',409),('delete-in-flight',409)])
def test_failed_turns_not_published_or_saved(report,probe,status):
    r=row(report,'source-time',probe)
    assert r['http_status']==status and r['reply']['published'] is False
    assert r['reply']['unsupported_claims'] is None and r['state']['saved_messages']==0
    if probe=='delete-in-flight':assert r['state']['remaining_ids']==[]
    if status==409:assert r['context']['status']=='not_reached' and r['calls']['generation_calls']==0


@pytest.mark.parametrize('probe',['memory-off','memory-locked'])
def test_permission_checks_precede_understanding_and_database_read(report,probe):
    r=row(report,'source-time',probe)
    assert r['calls']['analysis_calls']==0 and r['candidate']['ids'] is None
    assert r['selection']['requested_ids'] is None and r['context']['ids']==[]


@pytest.mark.parametrize('mutation',[
    lambda d:d['cases'].append(d['cases'][0]),
    lambda d:d['cases'][0]['responses'][0]['claims'][0].update(text='incomplete'),
    lambda d:d['cases'][0].update(relevant=['foreign']),
    lambda d:d['cases'][0]['responses'][0]['claims'][0].update(support='supported',required_sources=['invented']),
    lambda d:d['cases'][0]['probes'].append(d['cases'][0]['probes'][0]),
])
def test_invalid_references_fail_before_worker(mutation,tmp_path):
    d=json.loads(e.DATASET.read_bytes());mutation(d)
    p=tmp_path/'invalid.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError):e.evaluate(p)


def test_worker_never_reads_env_or_connects_to_network(tmp_path):
    # The hook is inherited by the child interpreter too; any .env or network use fails the replay.
    (tmp_path/'sitecustomize.py').write_text('''import sys,os
def guard(event,args):
    if event=="open" and isinstance(args[0],(str,bytes)) and os.fsdecode(args[0]).endswith("/.env"):
        raise RuntimeError("dotenv forbidden in offline replay")
    if event=="socket.connect":raise RuntimeError("network forbidden in offline replay")
sys.addaudithook(guard)
''')
    env={**os.environ,'PYTHONPATH':str(tmp_path),'MEMORY_DATABASE_URL':'sqlite:///'+str(tmp_path/'must-not-open.sqlite3'),
         'GEMINI_API_KEY':'private-test-sentinel'}
    p=subprocess.run([sys.executable,'scripts/evaluate_japanese.py','--memory-layers'],cwd=e.ROOT,env=env,capture_output=True,text=True,timeout=120)
    assert p.returncode==0,p.stderr
    result=json.loads(p.stdout)
    assert result['attempted']==31 and not (tmp_path/'must-not-open.sqlite3').exists()
    assert 'private-test-sentinel' not in p.stdout+p.stderr


def test_cli_rejects_mixed_export_and_replay_before_writing(tmp_path):
    target=tmp_path/'must-not-exist'
    r=subprocess.run([sys.executable,'scripts/evaluate_japanese.py','--memory-layers','--prepare-annotation',str(target)],cwd=e.ROOT,capture_output=True)
    assert r.returncode==2 and not target.exists()


@pytest.mark.parametrize('backend',['sqlite','postgres'])
@pytest.mark.parametrize('case_id,probe_id',[('subject-sister','wrong-known-accept'),('no-answer','reference'),
    ('persisted-correction','reference'),('ja-query-zh-memory','reference'),('zh-query-ja-memory','reference'),
    ('source-time','delete-in-flight'),('source-time','revoke-in-flight'),('source-time','selector-outside_id'),
    ('source-time','generation-timeout'),('source-time','review-timeout'),('current-correction','reference')])
def test_actual_api_replay_with_script_created_database(backend,case_id,probe_id,tmp_path,report):
    url=os.environ.get('TEST_POSTGRES_URL') if backend=='postgres' else 'sqlite:///'+str(tmp_path/'replay.sqlite3')
    if not url:pytest.skip('requires script-created temporary PostgreSQL')
    case=next(c for c in e.load().cases if c.id==case_id)
    probe=next(p for p in case.probes if p.id==probe_id)
    r=e._run_probe(case,probe,url)
    expected=row(report,case_id,probe_id)
    assert r==expected


def test_existing_or_production_database_cannot_be_used(tmp_path):
    path=tmp_path/'existing.sqlite3';path.touch()
    for url in ('sqlite:///'+str(path),'sqlite:///'+str(e.ROOT/'data/memory.sqlite3'),'postgresql://localhost/real_player'):
        with pytest.raises(ValueError):e._test_destination(url)


def test_context_same_id_with_changed_fact_is_not_valid_support(tmp_path,monkeypatch):
    from app import main as web
    original=web.fact_voice.memory_context
    def altered(memories):
        return original([{**m,'fact':'同じIDでも中身が改変された合成データ。'} for m in memories])
    monkeypatch.setattr(web.fact_voice,'memory_context',altered)
    case=next(c for c in e.load().cases if c.id=='source-time')
    r=e._run_probe(case,case.probes[0],'sqlite:///'+str(tmp_path/'projection.sqlite3'))
    assert r['context']['projection_match'] is False
    assert r['reply']['unsupported_claims']==1 and r['reply']['reference_answer_complete'] is False



def test_unfamiliar_published_reply_is_unrated_not_automatically_supported(tmp_path,monkeypatch):
    from app import main as web
    monkeypatch.setattr(web,'fixed_reply',lambda *a:'合成葵だよ。未知の追記があるよ。')
    case=next(c for c in e.load().cases if c.id=='source-time')
    r=e._run_probe(case,case.probes[0],'sqlite:///'+str(tmp_path/'unrated.sqlite3'))
    assert r['reply']['assessment_basis']=='unrated' and r['reply']['unsupported_claims'] is None
    assert r['reply']['reference_answer_complete'] is False

"""Public synthetic packets and recall; no genuine human/model ratings."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app import japanese_evaluation as j
from scripts.score_annotations import write_report


def test_actual_candidate_recall_and_no_answer_failures_are_reported_not_hidden():
    r=j.evaluate_recall();v=r['variants']
    assert r['assessment']=='not_assessed' and r['model_calls']==0
    assert v['raw_query']['positive_queries']==9
    assert v['raw_query']['macro_candidate_recall_at_5']==pytest.approx(1/9)
    assert v['authored_query']['macro_candidate_recall_at_5']==pytest.approx(8/9)
    assert v['authored_query_and_slots']['macro_candidate_recall_at_5']==1
    assert v['authored_query_and_slots']['no_answer_with_candidates']==3
    for variant in v.values():
        for row in variant['per_query']:assert set(row['candidate_ids'])<={'j1','j2','j3','j4','j5','j6','j7'}
    assert any('authored oracle' in s for s in r['limits'])


def test_evaluation_ignores_configured_player_database_and_keys(monkeypatch):
    monkeypatch.setenv('MEMORY_DATABASE_URL','postgresql://must-not-connect.invalid/player')
    monkeypatch.setenv('GEMINI_API_KEY','private-synthetic-sentinel')
    assert 'private-synthetic-sentinel' not in json.dumps(j.evaluate_recall())


@pytest.mark.parametrize('mutation',[
    lambda d:d['documents'].append(d['documents'][0]),
    lambda d:d['queries'].append(d['queries'][0]),
    lambda d:d['queries'][0].update(relevant=['j8']),
    lambda d:d['queries'][0].update(relevant=['j1','j1']),
    lambda d:d['queries'][0].update(target_slots=['invented']),
])
def test_invalid_dev_labels_and_scope_fail_before_database(mutation,tmp_path):
    data=json.loads(j.MEMORY.read_bytes());mutation(data)
    p=tmp_path/'bad.json';p.write_text(json.dumps(data))
    with pytest.raises(ValueError):j.evaluate_recall(p)


@pytest.fixture
def prepared(tmp_path):
    folder=tmp_path/'private';result=j.prepare(folder)
    assert result['assessment']=='not_assessed' and result['ratings']=='pending'
    return folder


def test_label_blind_preparation_preserves_raw_text_and_blank_scores(prepared):
    corpus=j.CareSet.model_validate_json(j.CARE.read_bytes())
    mapping=json.loads((prepared/'custodian_mapping.json').read_bytes())
    for name in ('rater_a','rater_b'):
        p=json.loads((prepared/(name+'.json')).read_bytes())
        assert p['reviewer'] is None and len(p['tasks'])==12
        assert all(r['claims'] is None and r['naturalness'] is None for r in p['ratings'])
        assert all(set(t)=={'task_id','history','evidence','candidate'} for t in p['tasks'])
        assert {t['candidate'] for t in p['tasks']}=={c.candidate for c in corpus.cases}
        assert 'family' not in json.dumps(p) and 'author_reference' not in json.dumps(p)
        assert set(mapping['mapping'])=={t['task_id'] for t in p['tasks']}
    assert (prepared/'README.ja.md').exists()
    with pytest.raises(ValueError):j.prepare(prepared)
    with pytest.raises(ValueError):j.prepare(j.ROOT/'do-not-create-annotation')
    with pytest.raises(ValueError):j.score_files(prepared/'custodian_mapping.json',[prepared/'rater_a.json'])


@pytest.fixture
def rated(prepared):
    paths=[prepared/'rater_a.json',prepared/'rater_b.json']
    for i,path in enumerate(paths):
        p=json.loads(path.read_bytes());p['reviewer']={'id':f'synthetic-rater-{i}','declared_independent':False,'declared_japanese_native':False}
        tasks={t['task_id']:t for t in p['tasks']}
        for r in p['ratings']:
            text=tasks[r['task_id']]['candidate']
            r.update(claims=[{'start':0,'end':len(text),'text':text,'kind':'assertion','verdict':'unsupported','evidence_ids':[],
                'proposition':'合成テストの命題','rationale':'採点器の合成テストです。'}],fact_issue=True,role_issue=False,role_issue_spans=[],
                naturalness=3,character_voice=3,care_fit=3,care_fit_na_reason=None,answered=True,unresolved=False,comment='PRIVATE-TEST-COMMENT')
        path.write_text(json.dumps(p,ensure_ascii=False))
    return prepared/'custodian_mapping.json',paths


def test_two_fake_submissions_are_only_statistics_never_independent_acceptance(rated):
    mapping,paths=rated;r=j.score_files(mapping,paths)
    assert r['tasks']==12 and r['submissions']==2 and r['model_calls']==0
    assert r['assessment']['status']=='not_assessed'
    assert r['agreement']['fact_issue']['kappa'] is None
    assert 'native_or_independence_not_declared' in r['assessment']['reasons']
    assert all(word not in json.dumps(r) for word in ('PRIVATE-TEST-COMMENT','synthetic-rater-','僕は','candidate'))
    assert j.score_files(mapping,paths[:1])['agreement']=={}


@pytest.mark.parametrize('mutation',[
    lambda p:p['ratings'].pop(),
    lambda p:p['tasks'].append(p['tasks'][0]),
    lambda p:p['tasks'][0].update(candidate='altered reply'),
    lambda p:p['profiles'].update(ja_reference_draft='altered role'),
    lambda p:p['ratings'][0]['claims'][0].update(end=1),
    lambda p:p['ratings'][0]['claims'][0].update(evidence_ids=['invented']),
    lambda p:p['reviewer'].update(declared_japanese_native='true'),
])
def test_submission_coverage_scope_role_and_strict_declarations(rated,mutation):
    mapping,paths=rated;p=json.loads(paths[0].read_bytes());mutation(p);paths[0].write_text(json.dumps(p))
    with pytest.raises(ValueError):j.score_files(mapping,paths)


def test_duplicate_json_and_changed_binding_rejected(rated,monkeypatch):
    mapping,paths=rated
    raw=mapping.read_text();mapping.write_text(raw.replace('"mapping":','"mapping":{},"mapping":',1))
    with pytest.raises(ValueError):j.score_files(mapping,paths)
    mapping.write_text(raw)
    monkeypatch.setattr(j,'binding',lambda:{'changed':'policy'})
    with pytest.raises(ValueError):j.score_files(mapping,paths)


def test_disagreements_and_claimed_native_independence_cannot_formally_pass(rated):
    mapping,paths=rated
    for path in paths:
        p=json.loads(path.read_bytes());p['reviewer'].update(declared_japanese_native=True,declared_independent=True)
        if path==paths[1]:p['ratings'][0]['naturalness']=1
        path.write_text(json.dumps(p))
    r=j.score_files(mapping,paths)
    assert r['disagreement_count']==1 and r['assessment']['status']=='not_assessed'
    assert 'reviewer_native_and_independence_not_verified' in r['assessment']['reasons']
    assert 'adjudication_pending' in r['assessment']['reasons']


def test_report_boundary_and_cli_acceptance_exit(rated,tmp_path):
    mapping,paths=rated;out=tmp_path/'summary.json'
    command=[sys.executable,'scripts/score_annotations.py','--japanese','--mapping',str(mapping),'--rater-a',str(paths[0]),'--rater-b',str(paths[1]),'--output',str(out),'--require-acceptance']
    r=subprocess.run(command,cwd=j.ROOT,capture_output=True,text=True)
    assert r.returncode==3 and json.loads(out.read_bytes())['assessment']['status']=='not_assessed'
    assert 'PRIVATE-TEST-COMMENT' not in r.stdout+r.stderr
    assert subprocess.run(command,cwd=j.ROOT,capture_output=True).returncode==2
    with pytest.raises(ValueError):write_report(j.ROOT/'do-not-create-scores.json',{})

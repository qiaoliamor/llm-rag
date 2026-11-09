import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
from pydantic import ValidationError
from app import sealed_evaluation as seal


@pytest.fixture
def bundle(tmp_path):
    target=tmp_path/'bundle';shutil.copytree(seal.BUNDLE,target)
    return target


def update_manifest(bundle,edit):
    path=bundle/'manifest.json';data=json.loads(path.read_text());edit(data)
    path.write_text(json.dumps(data))


def reseal_artifact(bundle,name):
    update_manifest(bundle,lambda d:d['artifacts'].update({name:hashlib.sha256((bundle/name).read_bytes()).hexdigest()}))


def test_real_manifest_integrity_only_is_not_acceptance():
    result=seal.verify()
    assert result.case_count==24
    assert result.acceptance=='not_assessed' and result.independent_annotation=='pending'
    assert result.status=='frozen_public_candidate_not_independent'


@pytest.mark.parametrize('change',[
    lambda d:d.update(acceptance='met'),
    lambda d:d.update(blind_review='completed'),
    lambda d:d.update(independent_annotation='completed'),
    lambda d:d.update(status='independent'),
    lambda d:d.update(model_execution='completed'),
    lambda d:d.update(frozen_on='bad-date'),
    lambda d:d.update(baseline_commit='bad-commit'),
    lambda d:d['artifacts'].update({'../.env':'0'*64}),
    lambda d:d['policy_artifacts'].update({'/tmp/private':'0'*64}),
    lambda d:d['artifacts'].update({'cases.json':'z'*64}),
    lambda d:d['strata'].update(memory=0),
    lambda d:d.update(case_count=1),
])
def test_invalid_manifest_cannot_claim_quality_or_read_external_paths(bundle,change):
    update_manifest(bundle,change)
    with pytest.raises(ValueError):seal.verify(bundle)


@pytest.mark.parametrize('name',['cases.json','author_reference.json'])
def test_changed_frozen_bytes_fail(bundle,name):
    path=bundle/name;path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='artifact drift'):seal.verify(bundle)


def test_policy_drift_is_not_silently_accepted(bundle):
    update_manifest(bundle,lambda d:d['policy_artifacts'].update({'app/dialogue.py':'0'*64}))
    with pytest.raises(ValueError,match='policy drift'):seal.verify(bundle)


@pytest.mark.parametrize('mutation',[
    lambda d:d['cases'].append(d['cases'][0]),
    lambda d:d['cases'][0].update(history=[{'role':'assistant','content':'hello'}]),
    lambda d:d.update(visibility='independent_unseen'),
    lambda d:d['cases'][0].update(candidate=''),
])
def test_resealed_invalid_content_still_fails(bundle,mutation):
    path=bundle/'cases.json';data=json.loads(path.read_text());mutation(data);path.write_text(json.dumps(data))
    reseal_artifact(bundle,'cases.json')
    with pytest.raises(ValueError):seal.verify(bundle,content=True)


@pytest.mark.parametrize('mutation',[
    lambda d:d['references'].pop(),
    lambda d:d['references'][0].update(id='unknown-case'),
    lambda d:d.update(independent=True),
    lambda d:d['references'][0].update(annotation_status='independent'),
])
def test_reference_draft_lineage_and_coverage(bundle,mutation):
    path=bundle/'author_reference.json';data=json.loads(path.read_text());mutation(data);path.write_text(json.dumps(data))
    reseal_artifact(bundle,'author_reference.json')
    with pytest.raises(ValueError):seal.verify(bundle,content=True)


def test_prepare_blinds_labels_preserves_evidence_and_empty_ratings(tmp_path,bundle):
    output=tmp_path/'packet'
    report=seal.prepare(output,bundle=bundle,seed=7)
    assert report['model_calls']==0 and not report['reference_labels_exported']
    packets=[json.loads((output/(r+'.json')).read_text()) for r in ['rater_a','rater_b']]
    assert len(packets[0]['tasks'])==len(packets[1]['tasks'])==24
    a,b=[[t['task_id'] for t in p['tasks']] for p in packets]
    assert set(a)==set(b) and a!=b
    for packet in packets:
        assert packet['purpose']=='synthetic_process_calibration_not_independent_trial'
        assert len(packet['profiles'])==2
        for task in packet['tasks']:
            assert set(task)=={'task_id','history','evidence','candidate'}
        for rating in packet['ratings']:
            assert all(v is None for k,v in rating.items() if k!='task_id')
    mapping=json.loads((output/'custodian_mapping.json').read_text())
    assert len(mapping['mapping'])==24
    originals={c['id']:c for c in json.loads((bundle/'cases.json').read_text())['cases']}
    for task in packets[0]['tasks']:
        original=originals[mapping['mapping'][task['task_id']]]
        assert original['candidate']==task['candidate'] and original['evidence']==task['evidence']


def test_refuse_overwrite_preserves_existing_data(tmp_path,bundle):
    output=tmp_path/'packet';output.mkdir();marker=output/'keep.txt';marker.write_text('keep')
    with pytest.raises(ValueError,match='overwrite'):seal.prepare(output,bundle=bundle)
    assert marker.read_text()=='keep'


def test_refuse_repository_export(bundle):
    with pytest.raises(ValueError,match='outside repository'):
        seal.prepare(seal.ROOT/'data'/'annotation-test',bundle=bundle)


def test_failed_export_removes_partial_files(tmp_path,bundle,monkeypatch):
    original=Path.write_text
    def fail(path,*args,**kwargs):
        if path.name=='rater_b.json':raise OSError('synthetic write failure')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'write_text',fail)
    with pytest.raises(OSError):seal.prepare(tmp_path/'packet',bundle=bundle)
    assert not (tmp_path/'packet').exists()
    assert not list(tmp_path.glob('annotation-*'))


def test_cli_is_offline_without_reading_model_config():
    run=subprocess.run([sys.executable,'scripts/check_sealed_evaluation.py'],
        env={**os.environ,'CHAT_PROVIDER':'invalid-provider'},capture_output=True,text=True,check=True)
    report=json.loads(run.stdout)
    assert report['check']=='integrity_only' and report['model_calls']==0
    assert report['acceptance']=='not_assessed' and 'cases' not in report

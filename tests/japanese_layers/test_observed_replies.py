"""Offline development references never turn the model's own accept into gold."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from app import observed_reply_evaluation as e


def reference(tmp_path,change):
    data=json.loads(e.REFERENCE.read_text());change(data)
    p=tmp_path/'reference.json';p.write_text(json.dumps(data,ensure_ascii=False));return p


def test_saved_model_outputs_without_annotations_are_unrated():
    r=e.evaluate();assert r['unrated']==2 and r['annotated']==0 and r['model_calls']==0
    assert all(x['model_accept_is_reference'] is False for x in r['results'])
    assert r['assessment']['status']=='not_assessed'


def test_author_annotations_reuse_scoring_partition_and_expose_chinese_question_disagreement():
    r=e.evaluate(reference=e.REFERENCE)
    assert r['tasks']==r['annotated']==2 and r['unrated']==0 and r['assessment']['status']=='not_assessed'
    zh=next(x for x in r['results'] if x['locale']=='zh-CN')
    assert zh['verdict_counts']['not_applicable']==1
    assert {'kind','verdict','evidence'}<=set(zh['model_comparison']['disagreements'][0]['axes'])
    assert all(set(x['missing_scopes'])=={'voice','independence'} for x in r['results'])
    encoded=json.dumps(r,ensure_ascii=False)
    assert '她后来情况怎么样' not in encoded and '自然度与角色距离感' not in encoded


@pytest.mark.parametrize('fault',['tail','overlap','foreign_id','missing_fact','missing_answer','snapshot','duplicate'])
def test_bad_annotation_is_not_scored(tmp_path,fault):
    def change(d):
        a=d['annotations'][0]
        if fault=='tail':a['claims'].pop()
        elif fault=='overlap':a['claims'][1]['start']=0
        elif fault=='foreign_id':a['claims'][0]['evidence_ids']=['reply_policy']
        elif fault=='missing_fact':a['claims'][0].update(verdict='unresolved',evidence_ids=[])
        elif fault=='missing_answer':a['answered']='partial'
        elif fault=='snapshot':d['observations_sha256']='0'*64
        else:d['annotations'].append(a)
    with pytest.raises(ValueError):e.evaluate(reference=reference(tmp_path,change))


@pytest.mark.parametrize('field',['reply','history','evidence','anchor'])
def test_original_reply_and_selected_context_cannot_drift(tmp_path,field):
    d=json.loads(e.OBSERVATIONS.read_text());o=d['observations'][0]
    if field=='reply':o['reply']+='追記'
    elif field=='history':o['history'][0]['content']='别的问题'
    elif field=='evidence':o['evidence'][0]['text']='私は合成葵社の面接を受けました。'
    else:o['provenance']['anchor']='nonexistent-snapshot-anchor'
    p=tmp_path/'observations.json';p.write_text(json.dumps(d,ensure_ascii=False))
    with pytest.raises(ValueError):e.evaluate(p)


def test_missing_reference_remains_unrated_and_does_not_use_model_accept(tmp_path):
    p=reference(tmp_path,lambda d:d['annotations'].pop())
    r=e.evaluate(reference=p);assert r['unrated']==1 and r['assessment']['status']=='not_assessed'


def test_empty_packet_is_external_new_and_not_a_valid_rating(tmp_path):
    output=tmp_path/'blank.json';r=e.prepare(e.OBSERVATIONS,output)
    assert r['ratings']=='empty_no_subjective_scores'
    assert all(a['claims'] is None for a in json.loads(output.read_text())['annotations'])
    with pytest.raises(ValueError):e.evaluate(reference=output)
    with pytest.raises(FileExistsError):e.prepare(e.OBSERVATIONS,output)
    with pytest.raises(ValueError):e.prepare(e.OBSERVATIONS,e.ROOT/'must-not-create.json')


def test_duplicate_json_field_rejected(tmp_path):
    p=tmp_path/'dup.json';p.write_text(e.REFERENCE.read_text().replace('"annotations":','"annotations":[], "annotations":',1))
    with pytest.raises(ValueError):e.evaluate(reference=p)


def test_cli_is_offline_and_cannot_claim_acceptance(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    p=subprocess.run([sys.executable,'scripts/evaluate_observed_replies.py','--reference',str(e.REFERENCE),'--require-acceptance'],capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(tmp_path)},timeout=30)
    assert p.returncode==3 and json.loads(p.stdout)['assessment']['status']=='not_assessed'

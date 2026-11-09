"""Synthetic submitted labels exercise validation/statistics, not model quality."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from pydantic import ValidationError
from app.annotation_scoring import agreement,score_files
from app.sealed_evaluation import prepare,ROOT
from scripts.score_annotations import write_report


def claim(text,*,start=0,bad=True):
    return {'start':start,'end':start+len(text),'text':text,'kind':'assertion',
            'verdict':'unsupported' if bad else 'supported','evidence_ids':[] if bad else ['C01'],
            'proposition':'合成技术标注命题','rationale':'测试用人为标注，不代表真实语义判断。'}


@pytest.fixture
def submissions(tmp_path):
    output=tmp_path/'packets';prepare(output,seed=3)
    paths=[output/'rater_a.json',output/'rater_b.json']
    for i,path in enumerate(paths):
        packet=json.loads(path.read_text());packet['reviewer']={'id':f'synthetic-rater-{i}','declared_independent':False}
        tasks={t['task_id']:t for t in packet['tasks']}
        for rating in packet['ratings']:
            rating.update(claims=[claim(tasks[rating['task_id']]['candidate'])],fact_issue=True,
                role_issue=False,role_issue_spans=[],naturalness=4,character_voice=4,care_fit=4,
                care_fit_na_reason=None,answered=True,unresolved=False,comment='private-comment-do-not-export')
        path.write_text(json.dumps(packet,ensure_ascii=False))
    return output/'custodian_mapping.json',paths


def edit(path,fn):
    data=json.loads(path.read_text());fn(data);path.write_text(json.dumps(data,ensure_ascii=False))


def test_two_complete_submissions_summary_privacy_and_not_assessed(submissions):
    mapping,paths=submissions;report=score_files(mapping,paths)
    assert report['tasks']==24 and report['submissions']==2
    assert report['agreement']['fact_issue']['agreement']==1
    assert report['agreement']['fact_issue']['kappa'] is None
    assert report['agreement']['fact_issue']['reason']=='degenerate_marginals'
    assert report['disagreement_count']==0 and report['assessment']['status']=='not_assessed'
    assert 'insufficient_formal_sample' in report['assessment']['reasons']
    assert report['rater_summaries'][0]['naturalness']['mean']==4
    assert sum(s['tasks'] for s in report['per_stratum'].values())==24
    assert report['model_calls']==0
    assert 'private-comment' not in json.dumps(report) and 'synthetic-rater' not in json.dumps(report)


@pytest.mark.parametrize('mutation',[
    lambda d:d['ratings'].pop(),
    lambda d:d['ratings'].append(d['ratings'][0]),
    lambda d:d['tasks'].append(d['tasks'][0]),
    lambda d:d['ratings'][0].update(task_id='T9999'),
    lambda d:d['tasks'][0].update(candidate='tampered candidate'),
    lambda d:d['tasks'][0]['history'][-1].update(content='tampered user'),
    lambda d:d['tasks'][0].update(evidence=[] if d['tasks'][0]['evidence'] else [{'id':'private','kind':'memory','text':'foreign'}]),
    lambda d:d['profiles'].clear(),
    lambda d:d['ratings'][0].update(naturalness=6),
    lambda d:d['ratings'][0].update(naturalness=True),
    lambda d:d['ratings'][0].update(claims=None),
    lambda d:d['ratings'][0].update(fact_issue=False),
    lambda d:d['ratings'][0].update(role_issue=True),
    lambda d:d['ratings'][0].update(role_issue_spans=[0,0],role_issue=True),
    lambda d:d['ratings'][0].update(role_issue_spans=[99],role_issue=True),
    lambda d:d['ratings'][0].update(care_fit=None),
])
def test_invalid_second_submission_never_partially_scores(submissions,mutation):
    mapping,paths=submissions;edit(paths[1],mutation)
    with pytest.raises(ValueError):score_files(mapping,paths)


@pytest.mark.parametrize('mutation',[
    lambda c:c.update(start=1),
    lambda c:c.update(end=c['end']-1),
    lambda c:c.update(text='not the candidate'),
    lambda c:c.update(evidence_ids=['other_player_memory']),
    lambda c:c.update(evidence_ids=['assistant_1']),
    lambda c:c.update(evidence_ids=['C01','C01']),
    lambda c:c.update(verdict='supported',evidence_ids=[]),
    lambda c:c.update(kind='question'),
])
def test_claim_coverage_and_known_evidence(submissions,mutation):
    mapping,paths=submissions
    edit(paths[0],lambda d:mutation(d['ratings'][0]['claims'][0]))
    with pytest.raises(ValueError):score_files(mapping,paths)


@pytest.mark.parametrize('mutation',[
    lambda d:d.update(manifest_sha256='0'*64),
    lambda d:d['mapping'].pop(next(iter(d['mapping']))),
    lambda d:d['mapping'].update({next(iter(d['mapping'])):'s99'}),
])
def test_manifest_binding_and_mapping_bijection(submissions,mutation):
    mapping,paths=submissions;edit(mapping,mutation)
    with pytest.raises(ValueError):score_files(mapping,paths)


def test_disagreements_labels_boundaries_evidence_and_scores(submissions):
    mapping,paths=submissions
    def change(d):
        rating=d['ratings'][0];text=rating['claims'][0]['text']
        rating.update(claims=[claim(text,bad=False)],fact_issue=False,naturalness=1,role_issue=True,role_issue_spans=[0])
        other=d['ratings'][1];text=other['claims'][0]['text']
        other['claims']=[claim(text[:2]),claim(text[2:],start=2)]
    edit(paths[1],change)
    r=score_files(mapping,paths)
    fields={f for row in r['disagreements'] for f in row['fields']}
    assert fields>={'fact_issue','role_issue','role_issue_spans','naturalness_gap','claim_boundaries','claim_labels_or_evidence'}
    assert r['disagreement_count']==2 and 'adjudication_pending' in r['assessment']['reasons']


@pytest.mark.parametrize('reviewer',[None,{'id':'synthetic-rater-0','declared_independent':True}])
def test_missing_or_same_reviewer_is_not_dual_independent_review(submissions,reviewer):
    mapping,paths=submissions;edit(paths[1],lambda d:d.update(reviewer=reviewer))
    r=score_files(mapping,paths)
    assert not r['distinct_submitted_ids'] and r['assessment']['status']=='not_assessed'
    assert r['agreement']['fact_issue']['kappa'] is None
    assert r['agreement']['fact_issue']['reason']=='reviewer_identity_missing_or_same'


def test_one_reviewer_and_self_declarations_cannot_pass(submissions):
    mapping,paths=submissions
    r=score_files(mapping,paths[:1]);assert 'second_reviewer_missing' in r['assessment']['reasons']
    for p in paths:edit(p,lambda d:d['reviewer'].update(declared_independent=True))
    r=score_files(mapping,paths)
    assert r['assessment']['status']=='not_assessed'
    assert 'reviewer_independence_not_verified' in r['assessment']['reasons']
    assert 'public_author_exposed_candidates' in r['assessment']['reasons']


def test_unresolved_and_care_na_are_explicit_not_hidden_success(submissions):
    mapping,paths=submissions
    def change(d):
        rating=d['ratings'][0];rating['claims'][0].update(verdict='unresolved')
        rating.update(unresolved=True,fact_issue=None,care_fit=None,care_fit_na_reason='此例不要求关怀评分。')
    edit(paths[0],change)
    r=score_files(mapping,paths)
    assert r['agreement']['fact_issue']['n']==23 and r['agreement']['fact_issue']['excluded']==1
    assert r['rater_summaries'][0]['care_fit']['na']==1
    assert 'unresolved_annotations' in r['assessment']['reasons'] and len(r['unresolved_tasks'])==1
    assert any('care_fit_applicability' in d['fields'] for d in r['disagreements'])


def test_nominal_kappa_and_linear_weighted_kappa_hand_calculated():
    r=agreement([False,False,True,True],[False,True,True,True])
    assert r['agreement']==.75 and r['kappa']==.5 and r['matches']==3
    assert r['expected_agreement']==.5
    r=agreement([1,5],[2,4],weighted=True)
    assert r['agreement']==0 and r['kappa']==.5
    assert agreement([1,5],[5,1],weighted=True)['kappa']==-1
    assert agreement([],[])['kappa'] is None
    with pytest.raises(ValueError):agreement([1],[])


def test_export_refuses_repository_and_overwrite(tmp_path):
    report={'assessment':{'status':'not_assessed'}}
    with pytest.raises(ValueError):write_report(ROOT/'data'/'annotation.json',report)
    output=tmp_path/'summary.json';write_report(output,report)
    assert json.loads(output.read_text())==report
    with pytest.raises(FileExistsError):write_report(output,{'replacement':True})
    assert json.loads(output.read_text())==report


def test_cli_offline_summary_and_acceptance_exit_code(submissions,tmp_path):
    mapping,paths=submissions
    base=[sys.executable,'scripts/score_annotations.py','--mapping',str(mapping),'--rater-a',str(paths[0]),'--rater-b',str(paths[1])]
    env={**os.environ,'CHAT_PROVIDER':'invalid-provider'}
    output=tmp_path/'summary.json'
    result=subprocess.run(base+['--output',str(output)],capture_output=True,text=True,env=env)
    assert result.returncode==0 and json.loads(result.stdout)['assessment']=='not_assessed'
    assert 'private-comment' not in result.stdout and json.loads(output.read_text())['model_calls']==0
    result=subprocess.run(base+['--output',str(tmp_path/'gate.json'),'--require-acceptance'],capture_output=True,text=True,env=env)
    assert result.returncode==3
    edit(paths[1],lambda d:d['ratings'].clear())
    result=subprocess.run(base+['--output',str(tmp_path/'invalid.json')],capture_output=True,text=True,env=env)
    assert result.returncode==2 and not (tmp_path/'invalid.json').exists()


def test_exact_tail_and_overlap_rejected(submissions):
    mapping,paths=submissions
    original=paths[0].read_text()
    def truncate(d):
        c=d['ratings'][0]['claims'][0];c['end']-=1;c['text']=c['text'][:-1]
    edit(paths[0],truncate)
    with pytest.raises(ValueError,match='tail'):score_files(mapping,paths)
    paths[0].write_text(original)
    def overlap(d):
        r=d['ratings'][0];text=r['claims'][0]['text']
        r['claims']=[claim(text[:3]),claim(text[2:],start=2)]
    edit(paths[0],overlap)
    with pytest.raises(ValueError,match='partition'):score_files(mapping,paths)


def test_unicode_offsets_are_codepoints_not_utf16(submissions):
    from app.annotation_scoring import Rating,Task,check_claims
    _,paths=submissions
    data=json.loads(paths[0].read_text())['ratings'][0]
    data['claims']=[claim('🙂好。')]
    rating=Rating.model_validate(data)
    task=Task(task_id=rating.task_id,history=[{'role':'user','content':'合成测试'}],evidence=[],candidate='🙂好。')
    check_claims(rating,task,set())
    rating.claims[0].end=4
    with pytest.raises(ValueError):check_claims(rating,task,set())


def test_failed_output_is_cleaned(tmp_path,monkeypatch):
    output=tmp_path/'summary.json';original=Path.open
    class Broken:
        def __enter__(self):
            self.stream=original(output,'x',encoding='utf-8');return self
        def write(self,text):
            self.stream.write('partial');raise OSError('synthetic disk failure')
        def __exit__(self,*args):self.stream.close()
    def replace(path,*args,**kwargs):
        if path==output and args and args[0]=='x':return Broken()
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',replace)
    with pytest.raises(OSError):write_report(output,{'safe':'summary'})
    assert not output.exists()


def test_independent_axes_role_flag_must_have_span_even_unresolved(submissions):
    mapping,paths=submissions
    edit(paths[0],lambda d:d['ratings'][0].update(unresolved=True,role_issue=True))
    with pytest.raises(ValueError,match='role flag'):score_files(mapping,paths)


@pytest.mark.parametrize('where',['mapping','packet','rating'])
def test_raw_duplicate_json_fields_are_rejected(submissions,where):
    mapping,paths=submissions
    path=mapping if where=='mapping' else paths[0]
    raw=path.read_text()
    if where=='mapping':
        digest=json.loads(raw)['manifest_sha256']
        raw='{"manifest_sha256": '+json.dumps(digest)+','+raw[1:]
    elif where=='packet':
        raw='{"purpose": "synthetic_process_calibration_not_independent_trial",'+raw[1:]
    else:
        raw=raw.replace('"fact_issue": true','"fact_issue": true, "fact_issue": true',1)
    path.write_text(raw)
    with pytest.raises(ValueError,match='duplicate JSON field'):
        score_files(mapping,paths)

"""Public author references; scripted replay is not independent semantic accuracy."""
import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from app import japanese_memory_layers as e
from app.config import Settings
from scripts import retest_bilingual_acceptance as live


@pytest.fixture(scope='module')
def report():return e.evaluate(e.CURRENT_POLICY_DATASET)


def test_current_matrix_has_both_languages_full_layers_and_keeps_false_accepts(report):
    assert report['cases']==16 and report['attempted']==50 and report['model_calls']==0
    assert report['assessment']=='not_assessed' and report['scope']=='current_policy_bilingual'
    assert report['reference_probes']=={'attempted':16,'reference_answer_complete':16,'candidate_misses':0}
    assert report['published_with_unsupported_claims']==14 and report['projection_mismatches']==0
    for locale in ('ja-JP','zh-CN'):
        rows=[r for r in report['acceptance_matrix'] if r['locale']==locale]
        assert len(rows)==8 and {r['group'] for r in rows}=={'subject','correction','no_answer','canon','atmosphere','scene_abuse'}
        assert all(r['reply_layer']['reference_answer_complete'] for r in rows)
        assert all(r['independent_semantic_quality']=='not_assessed' and r['native_blind_review']=='pending' for r in rows)
        for r in rows:assert r['reference_note'] and r['origin']
        scene=next(r for r in rows if r['group']=='atmosphere')
        assert scene['reference_responses'][0]['segments'][0]['support']=='permitted_scene'
    blocked=[r for r in report['per_probe'] if r['probe']=='allowed-overblock']
    assert len(blocked)==2 and all(r['reply']['fixture_id']=='safe' and not r['reply']['reference_answer_complete'] for r in blocked)


@pytest.mark.parametrize('case',e.load(e.CURRENT_POLICY_DATASET).cases,ids=lambda c:c.id)
@pytest.mark.parametrize('backend',['sqlite','postgres'])
def test_reference_actual_api_and_storage(case,backend,tmp_path):
    url=os.environ.get('TEST_POSTGRES_URL') if backend=='postgres' else 'sqlite:///'+str(tmp_path/'current.sqlite3')
    if not url:pytest.skip('requires script-created temporary PostgreSQL')
    row=e._run_probe(case,e.Probe(id='reference'),url)
    assert row['http_status']==200 and row['reply']['reference_answer_complete']
    assert row['reply']['unsupported_claims']==0 and row['context']['projection_match']
    assert row['state']['saved_messages']==len(case.prior_dialogue)+2
    if case.id.endswith('persisted-correction'):assert row['candidate']['ids']==['new']
    if case.id.endswith('current-correction'):
        assert row['candidate']['ids'] is None and row['context']['ids']==[]
        assert case.responses[0].claims[0].required_sources==['user_prior_0','user_current']
        assert '合成旧町' in case.prior_dialogue[0].content and '合成新町' in case.responses[0].text


@pytest.mark.parametrize('fault',['scene','contradiction','source','coverage','missing_note','missing_language'])
def test_annotation_protocol_rejects_invalid_data_before_replay(fault):
    data=json.loads(e.CURRENT_POLICY_DATASET.read_text());c=next(c for c in data['cases'] if c['group']=='atmosphere')
    claim=c['responses'][0]['claims'][0]
    if fault=='scene':claim['required_sources']=['C01']
    elif fault=='contradiction':claim.update(support='contradicted',required_sources=[])
    elif fault=='source':claim.update(support='supported',required_sources=['reply_policy'])
    elif fault=='coverage':claim['text']='incomplete'
    elif fault=='missing_note':c['reference_note']=''
    else:data['cases']=[c for c in data['cases'] if c['locale']=='ja-JP']
    with pytest.raises(ValueError):e.Suite.model_validate(data)


def test_live_tail_uses_real_api_pipeline_with_scripted_sdk_no_plan_or_selection_call(monkeypatch):
    class Generator:
        async def generate(self,history,prompt):
            assert '妹は合成桔梗社の面接を受けました。' in prompt
            assert '私は合成葵社の面接を受けました。' not in prompt
            return '妹さんは合成桔梗社の面接だったね。'
    class Judge:
        def __init__(self,*a):pass
        async def review(self,text,history,evidence):
            canon=text=='僕は30歳の医師だよ。'
            ids=['C01','C02'] if canon else [e['id'] for e in evidence if e['id'].startswith('memory_')]
            return {'decision':'revise' if canon else 'accept','confidence':.95,'role_issues':[],
                'segments':[{'text':text,'kind':'assertion','verdict':'contradicted' if canon else 'supported','evidence_ids':ids,'reason':'contradiction' if canon else 'evidence_supports'}]}
    monkeypatch.setattr(live,'build_provider',lambda s:Generator());monkeypatch.setattr(live,'FactAnalysisProvider',Judge)
    r=live.run(Settings(_env_file=None,chat_provider='mock',memory_database_url='sqlite:///must-not-open.sqlite3'))
    assert r['max_calls']==r['attempted_calls']==3 and not r['blocked'] and not r['unattempted_ids']
    assert [c['stage'] for c in r['calls']]==['generation','review','review']
    row=r['results'][0]
    assert row['selection']['ids']==row['context']['ids']==['sister']
    assert row['reply']['assessment_basis']=='unrated'  # Do not grade an unfamiliar generated reply from the model judge's accept.
    assert r['results'][1]['authored_reference_match']
    assert 'must-not-open.sqlite3' not in json.dumps(r)


def test_live_budget_blocks_extra_rewrite_without_calling_operation():
    async def run():
        b=live.Budget(('ja-subject-tail',));seen=[]
        async def op():seen.append(1)
        await b.call('ja-subject-tail','generation',op);await b.call('ja-subject-tail','review',op)
        with pytest.raises(live.ProviderFailure):await b.call('ja-subject-tail','generation',op)
        assert len(seen)==len(b.calls)==2 and b.blocked
    asyncio.run(run())


def test_cli_without_live_does_not_read_env_or_connect(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    p=subprocess.run([sys.executable,'scripts/retest_bilingual_acceptance.py'],capture_output=True,text=True,env={**os.environ,'PYTHONPATH':str(tmp_path)})
    assert p.returncode==2 and '--live required' in p.stderr


def test_live_tail_review_failure_stops_without_retry_or_canon_call(monkeypatch):
    class Generator:
        async def generate(self,*args):return '妹さんは合成桔梗社の面接だったね。'
    class Judge:
        def __init__(self,*a):pass
        async def review(self,*a):
            error=RuntimeError('private-synthetic-error');error.status_code=503;raise error
    monkeypatch.setattr(live,'build_provider',lambda s:Generator());monkeypatch.setattr(live,'FactAnalysisProvider',Judge)
    r=live.run(Settings(_env_file=None,chat_provider='mock'))
    assert r['attempted_calls']==2 and r['unattempted_ids']==['ja-canon-review']
    assert r['calls'][-1]['failure']=='upstream_unavailable'
    assert r['results'][0]['http_status']==503 and r['results'][0]['state']['saved_messages']==0
    assert 'private-synthetic-error' not in json.dumps(r)


def test_current_cli_is_offline_with_private_env_sentinel(tmp_path):
    (tmp_path/'sitecustomize.py').write_text('import sys,os\ndef guard(e,a):\n if e=="open" and isinstance(a[0],(str,bytes)) and os.fsdecode(a[0]).endswith("/.env"):raise RuntimeError("forbidden")\n if e=="socket.connect":raise RuntimeError("forbidden")\nsys.addaudithook(guard)\n')
    env={**os.environ,'PYTHONPATH':str(tmp_path),'GEMINI_API_KEY':'private-sentinel','MEMORY_DATABASE_URL':'sqlite:///'+str(tmp_path/'must-not-open.sqlite3')}
    p=subprocess.run([sys.executable,'scripts/evaluate_japanese.py','--current-policy-matrix'],capture_output=True,text=True,env=env,timeout=120)
    assert p.returncode==0 and json.loads(p.stdout)['attempted']==50
    assert 'private-sentinel' not in p.stdout+p.stderr and not (tmp_path/'must-not-open.sqlite3').exists()


@pytest.mark.parametrize('status',['unavailable','uncertain','mock_or_unavailable','accepted'])
def test_single_tail_cli_rejects_http_200_when_review_incomplete(monkeypatch,capsys,status):
    import dotenv
    monkeypatch.setattr(dotenv,'dotenv_values',lambda *a,**k:{})
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-not-a-key')
    monkeypatch.setattr(sys,'argv',['retest_bilingual_acceptance.py','--live','--case','ja-subject-tail'])
    monkeypatch.setattr(live,'run',lambda *a,**k:{'unattempted_ids':[],'blocked':[],
        'results':[{'test_id':'ja-subject-tail','http_status':200,'semantic_review':{'status':status},
                    'observations':{'reviews':[]}}]})
    assert live.main()==1
    capsys.readouterr()


def test_single_tail_cli_success_is_technical_only_not_semantic_acceptance(monkeypatch,capsys):
    import dotenv
    monkeypatch.setattr(dotenv,'dotenv_values',lambda *a,**k:{})
    monkeypatch.setenv('GEMINI_API_KEY','synthetic-not-a-key')
    monkeypatch.setattr(sys,'argv',['retest_bilingual_acceptance.py','--live','--case','ja-subject-tail'])
    report={'unattempted_ids':[],'blocked':[],'assessment':'not_assessed',
        'results':[{'test_id':'ja-subject-tail','http_status':200,'semantic_review':{'status':'accepted'},
                    'observations':{'reviews':[{'decision':'accept'}]},'reply':{'assessment_basis':'unrated'}}]}
    monkeypatch.setattr(live,'run',lambda *a,**k:report)
    assert live.main()==0
    assert json.loads(capsys.readouterr().out)['results'][0]['reply']['assessment_basis']=='unrated'

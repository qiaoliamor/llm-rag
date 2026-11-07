import asyncio
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError
from app import reference_audit as audit
from app.narrative_calibration import load_dataset, score
from app.semantic_review import ModelAnalysisProvider, review_reply
from scripts.audit_narrative_references import retest


def test_snapshot_coverage_and_legacy_preservation():
    data,manifest,texts=audit.load_audit()
    original,digest=load_dataset()
    assert digest=='f4391fc9b27e170c5ceea37c1d289ce78ec102ddc452f0faae6cbbaff61d5f5b'
    assert len(data.cases)==38 and len(manifest.reviews)==38
    assert [c.model_dump() for c in data.cases[:23]]==[c.model_dump() for c in original.cases]
    assert set(texts)==set(audit.source_inventory())
    assert hashlib.sha256(Path('evaluations/fact_support_dev.json').read_bytes()).hexdigest()=='f3a2f1d8c4a7559598464479147e007df02031d23074bb952a6bb8134bf4ad19'


@pytest.mark.parametrize('case',audit.load_audit()[0].cases[23:],ids=lambda c:c.id)
def test_new_references_keep_history_and_reference_separate(case):
    history,evidence=case.context()
    assert history[-1]['role']=='user'
    users=[e for e in evidence if e['kind']=='user']
    assert users[-1]['text']==history[-1]['content'] and users[-1]['current']
    assert not any(e['current'] for e in users[:-1])
    assert not any('rationale' in e or 'fact_issue' in e or 'role_issue' in e for e in evidence)
    assert not any(e['kind']=='assistant' for e in evidence)


@pytest.mark.parametrize('change,match',[
    (lambda d:d['reviews'].pop(),'incomplete'),
    (lambda d:d['reviews'].append(d['reviews'][0]),'duplicate'),
    (lambda d:d['reviews'][0].update(fact_issue=False),'disagreement'),
    (lambda d:d['reviews'][0].update(conclusion='new'),'lineage'),
    (lambda d:d['reviews'][0]['references'][0].update(anchor='unfindable-anchor-here'),'stale'),
    (lambda d:d['reviews'][0]['references'][0].update(path='not-in-snapshot.json'),'snapshot'),
    (lambda d:d['sources'][0].update(sha256='0'*64),'source drift'),
    (lambda d:d.update(target_sha256='0'*64),'target drift'),
    (lambda d:d['sources'].pop(),'inventory'),
])
def test_audit_fails_on_stale_or_incomplete_review(tmp_path,monkeypatch,change,match):
    raw=json.loads(audit.AUDIT.read_text());change(raw)
    path=tmp_path/'synthetic-audit.json';path.write_text(json.dumps(raw))
    monkeypatch.setattr(audit,'AUDIT',path)
    with pytest.raises(ValueError,match=match):audit.load_audit()


@pytest.mark.parametrize('path',['../.env','/tmp/outside.py','tests/../.env','tests/../../outside.py'])
def test_private_or_external_source_rejected(path):
    with pytest.raises(ValueError):audit.Source(path=path,sha256='0'*64)


def test_surface_similarity_is_not_semantic_labels():
    # Similar strings can have opposite polarity; unrelated wording can be equivalent.
    assert audit.similarity('今天店里非常安静','今天店里不是非常安静')>0
    a=audit.candidate_matches('店里安静',[('x','店里不安静'),('y','店里安静')])
    assert a[0]['source']=='y' and 'fact_issue' not in a[0]
    assert audit.normalize('New Willow City。')==audit.normalize('new willow city')
    assert audit.similarity('','')==0


def test_literals_only_never_executes_sources():
    units=audit.source_units('tests/fake.py',"raise RuntimeError('must not execute')\ntext='低风险的虚构窗外氛围描写'\n")
    assert any('窗外' in text for _,text in units)


def test_report_does_not_claim_independent_quality():
    report=audit.evaluate_audit()
    assert report['api_calls']==0 and report['independent_samples'] is None
    assert report['retained']==23 and report['added']==15
    assert sum(report['family_counts'].values())==38
    assert len(report['family_counts'])<38
    assert all(r['semantic_links'] for r in report['results'])


def test_english_probe_is_same_old_failure_not_recent_success():
    from scripts.compare_semantic_review import cases
    old,_=cases();prior=next(c for c in old if c['id']=='place-english-changed')
    data,_,_=audit.load_audit();case=next(c for c in data.cases if c.id==prior['id'])
    assert case.reply==prior['candidate']
    assert case.history[0].content==prior['query']
    assert [m.model_dump() for m in case.memories]==prior['memories']


def test_live_failure_is_one_call_no_retry():
    provider=SimpleNamespace(review=AsyncMock(side_effect=TimeoutError()))
    row=asyncio.run(retest(provider,audit.load_audit()[0]))
    assert provider.review.await_count==1 and row['failure']=='timeout'
    assert not row['axes_match']


@pytest.mark.parametrize('id',['arrival-retracted','assistant-self-proof','scene-continuity','fiction-not-player-memory','multi-source-correction'])
def test_multi_turn_context_reaches_provider_without_labels(id):
    case=next(c for c in audit.load_audit()[0].cases if c.id==id)
    class Capture(ModelAnalysisProvider):
        async def parse(self,schema,prompt,payload,*args):
            assert 'fact_issue' not in payload and 'rationale' not in payload
            users=[e for e in payload['evidence'] if e['kind']=='user']
            assert users[-1]['text']==case.history[-1].content and users[-1]['current']
            assert payload['fictional_dialogue_context']==[m.model_dump() for m in case.history if m.role=='assistant']
            bad=case.fact_issue
            # Labels injected solely to verify transport/scoring, not semantic accuracy.
            return schema.model_validate({'confidence':.9,'role_issues':[], 'units':[
                {'id':u['id'],'kind':'assertion','verdict':'unsupported' if bad else 'supported',
                 'evidence_ids':[] if bad else ['scene_profile']} for u in payload['units']]})
    provider=Capture(SimpleNamespace(semantic_review_timeout_seconds=8))
    history,evidence=case.context()
    outcome=asyncio.run(review_reply(provider,case.reply,history,evidence))
    assert score(case,outcome)['axes_match']


def test_offline_cli_stays_offline():
    result=subprocess.run([sys.executable,'scripts/audit_narrative_references.py'],capture_output=True,text=True,check=True)
    report=json.loads(result.stdout)
    assert report['api_calls']==report['max_live_calls']==0
    assert 'live_result' not in report

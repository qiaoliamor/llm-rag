import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
from pydantic import ValidationError
from app import fact_support_evaluation as audit
from scripts.evaluate_fact_support import markdown


def raw_data():
    return json.loads(audit.DATASET.read_text())


def test_complete_claim_coverage_and_historical_replies_are_exact():
    data,digest=audit.load_dataset()
    assert len(digest)==64 and len(data.cases)==52
    for case in data.cases:
        assert ''.join(c.text for c in case.claims)==case.reply
        assert case.claims[0].start==0 and case.claims[-1].end==len(case.reply)
    blocks=re.findall(r'((?:^>.*\n)+)',(audit.ROOT/'docs/SCENE_PLACE_GROUNDING.md').read_text(),re.M)
    expected=['\n'.join(line[2:] if line.startswith('> ') else '' for line in b.rstrip('\n').splitlines()) for b in blocks]
    assert [c.reply for c in data.cases if c.origin=='historical_gemini']==expected
    from scripts.evaluate_grounding import CASES,evidence_for
    by_id={e.id:e for e in data.evidence}
    for case in data.cases:
        if case.origin!='historical_gemini': continue
        key={'history-pet':'pet','history-place':'when','history-scene':'shop'}[case.family]
        original=next(c for c in CASES if c['id']==key)
        assert case.query==original['query']
        actual={(by_id[id].text,by_id[id].event_date) for id in case.evidence_ids if by_id[id].kind=='memory'}
        assert actual=={(e['fact'],e['event_date']) for e in evidence_for(original)}


@pytest.mark.parametrize('mutation',[
    'gap','overlap','wrong_text','missing_tail','duplicate_case','duplicate_claim',
    'duplicate_evidence','unknown_context','outside_basis','missing_basis',
    'wrong_kind','nonfactual_basis','empty_rationale','unreviewed','unknown_field',
    'unknown_verdict','empty_cases','invalid_date','canon_drift','user_evidence_mismatch',
    'form_without_reason',
])
def test_invalid_or_partial_annotations_fail_closed(mutation):
    d=raw_data();case=d['cases'][0];claim=case['claims'][0]
    if mutation=='gap':claim['start']=1
    elif mutation=='overlap':case['claims'].append(copy.deepcopy(claim));case['claims'][-1]['id']='overlap'
    elif mutation=='wrong_text':claim['text']='不匹配的片段'
    elif mutation=='missing_tail':case['reply']+='遗漏的事实。'
    elif mutation=='duplicate_case':d['cases'].append(copy.deepcopy(case))
    elif mutation=='duplicate_claim':case['claims'].append(copy.deepcopy(claim))
    elif mutation=='duplicate_evidence':d['evidence'].append(copy.deepcopy(d['evidence'][0]))
    elif mutation=='unknown_context':case['evidence_ids'].append('missing')
    elif mutation=='outside_basis':claim['basis_ids']=['place']
    elif mutation=='missing_basis':claim['basis_ids']=[]
    elif mutation=='wrong_kind':claim['kind']='question'
    elif mutation=='nonfactual_basis':claim.update(kind='question',verdict='not_applicable')
    elif mutation=='empty_rationale':claim['rationale']=''
    elif mutation=='unreviewed':case['coverage_reviewed']=False
    elif mutation=='unknown_field':d['automatic_verdict']='safe'
    elif mutation=='unknown_verdict':claim['verdict']='probably_true'
    elif mutation=='empty_cases':d['cases']=[]
    elif mutation=='invalid_date':d['evidence'][-1]['event_date']='2026-99-99'
    elif mutation=='canon_drift':d['evidence'][0]['text']='角色今年19岁'
    elif mutation=='user_evidence_mismatch':d['evidence'][-1]['text']='并非当前原话'
    elif mutation=='form_without_reason':claim['form_violation']=True
    with pytest.raises(ValidationError):audit.Dataset.model_validate(d)


def test_character_file_drift_requires_reference_review(tmp_path):
    d=raw_data();d['character_sha256']='0'*64
    p=tmp_path/'synthetic.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError,match='canon drift'):audit.load_dataset(p)


def test_bad_fact_is_not_hidden_by_correct_name_or_complete_place():
    report=audit.evaluate();rows={r['id']:r for r in report['results']}
    partial=rows['paraphrase-place-inference']
    assert [c['verdict'] for c in partial['claims']]==['supported','unsupported']
    assert partial['semantic_unsafe'] and partial['finding']=='miss'
    mixed=rows['mixed-supported-and-invented']
    assert [c['verdict'] for c in mixed['claims']]==['supported','contradicted','unsupported']
    assert mixed['obligation_hits']==1 and mixed['obligation_count']==2


def test_evasion_and_uncertain_labels_do_not_earn_fact_support_passes():
    report=audit.evaluate();rows={r['id']:r for r in report['results']}
    evasion=rows['obligation-evasion']
    assert evasion['factual_claim_count']==0 and evasion['obligation_hits']==0
    assert evasion['obligation_count']==1 and not evasion['guarded']
    unknown=rows['ambiguous-reference']
    assert unknown['policy_unsafe'] is None and unknown['finding']=='unresolved'
    s=audit.summarize([evasion,unknown])
    assert s['fully_supported_responses']==0
    assert s['policy_confusion']['eligible']==1 and s['policy_confusion']['unresolved_excluded']==1
    assert s['nonfactual_only_responses']==1


def test_form_policy_is_separate_from_semantic_entailment():
    row=next(r for r in audit.evaluate()['results'] if r['id']=='place-alias-two-axes')
    assert row['semantic_unsafe'] is False
    assert row['form_violation'] and row['policy_unsafe'] and row['guarded']
    assert row['finding'] is None
    assert audit.summarize([row])['semantic_confusion']['fp']==1
    assert audit.summarize([row])['policy_confusion']['tp']==1


def test_supported_paraphrases_quotes_and_conditionals_expose_overblocks():
    rows={r['id']:r for r in audit.evaluate()['results']}
    for id in ('scene-conditional-expanded','scene-quotation-safe','place-correction-quote',
               'source-current-paraphrase','source-quotation-safe'):
        assert rows[id]['semantic_unsafe'] is False and rows[id]['finding']=='overblock'
    for id in ('place-english-changed','place-friend-attribution','source-event-date','scene-current-paraphrase'):
        assert rows[id]['semantic_unsafe'] and rows[id]['finding']=='miss'


def test_gold_support_scores_do_not_depend_on_guard_predictions(monkeypatch):
    before=audit.evaluate()
    monkeypatch.setattr(audit,'guard_predictions',lambda reply,query,evidence:{'forced':True})
    after=audit.evaluate()
    for key in ('claim_verdicts','factual_claims','fully_supported_responses','obligation_hits'):
        assert before['summary'][key]==after['summary'][key]
    assert all(r['guarded'] for r in after['results'])
    assert before['summary']['policy_confusion']!=after['summary']['policy_confusion']


def test_json_markdown_and_default_cli_do_not_load_config_or_network():
    env={**os.environ,'CHAT_PROVIDER':'not-a-provider','MEMORY_DATABASE_URL':'invalid-no-database',
         'GEMINI_API_KEY':'test-must-not-be-read','OPENAI_API_KEY':'test-must-not-be-read'}
    result=subprocess.run([sys.executable,'scripts/evaluate_fact_support.py'],cwd=audit.ROOT,
                          env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    report=json.loads(result.stdout)
    assert report['model_calls']==report['database_calls']==0
    assert report['summary']['policy_confusion']['fn']>0 and report['summary']['policy_confusion']['fp']>0
    assert 'test-must-not-be-read' not in result.stdout
    text=markdown(report)
    assert 'place-english-changed' in text and 'source-current-paraphrase' in text
    assert '不是自动语义裁判' in text
    gated=subprocess.run([sys.executable,'scripts/evaluate_fact_support.py','--fail-on-findings'],
                         cwd=audit.ROOT,env=env,capture_output=True,text=True)
    assert gated.returncode==1  # Expected quality findings, NOT a broken evaluator.


def test_empty_fact_denominators_are_null_instead_of_perfect_scores():
    row=next(r for r in audit.evaluate()['results'] if r['id']=='obligation-evasion')
    summary=audit.summarize([row])
    assert summary['supported_claim_fraction'] is None
    assert summary['fully_supported_response_fraction'] is None
    assert summary['required_evidence_coverage']==0
    assert audit.summarize([])['policy_confusion']['precision'] is None

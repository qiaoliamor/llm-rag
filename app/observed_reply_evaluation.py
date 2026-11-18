"""Offline, evidence-bound development annotations for unfamiliar synthetic outputs.

No model calls, automatic semantic truth, native scores or formal acceptance.
"""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
from types import SimpleNamespace
from typing import Literal
from pydantic import Field,model_validator
from .sealed_evaluation import ROOT,Record,Message
from .annotation_scoring import Claim,check_claims,parse_submission
from .semantic_review import Review

OBSERVATIONS=ROOT/'evaluations/current_policy/gemini_observations_v1.json'
REFERENCE=ROOT/'evaluations/current_policy/observed_reply_reference_dev_v1.json'


class Evidence(Record):
    id: str=Field(min_length=1,max_length=100)
    kind: Literal['memory','user','canon','scene']
    text: str=Field(min_length=1,max_length=5000)


class Provenance(Record):
    commit: str=Field(pattern=r'^[0-9a-f]{40}$')
    path: Literal['docs/TEST_HISTORY.md']
    anchor: str=Field(min_length=5,max_length=300)
    context_path: Literal['scripts/retest_memory_canon.py','evaluations/current_policy/bilingual_memory_acceptance_v1.json']
    context_case: str=Field(pattern=r'^[a-z0-9_-]{1,80}$')
    selected_memory_ids: list[str]=Field(default_factory=list,max_length=20)
    reply_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    note: str=Field(min_length=10)


class Observation(Record):
    id: str=Field(pattern=r'^[a-z0-9_-]{1,80}$')
    locale: Literal['zh-CN','ja-JP']
    model: str
    delivery: Literal['published','unpublished_draft','not_observed']
    history: list[Message]=Field(min_length=1)
    evidence: list[Evidence]
    reply: str=Field(min_length=1,max_length=4000)
    provenance: Provenance
    model_review_observation: dict | None=None

    @model_validator(mode='after')
    def bound(self):
        if self.history[-1].role!='user':raise ValueError('last message must be user')
        if len({e.id for e in self.evidence})!=len(self.evidence):raise ValueError('duplicate evidence')
        if len(set(self.provenance.selected_memory_ids))!=len(self.provenance.selected_memory_ids):raise ValueError('duplicate selected evidence')
        if hashlib.sha256(self.reply.encode()).hexdigest()!=self.provenance.reply_sha256:raise ValueError('reply hash drift')
        return self


class Observations(Record):
    version: Literal['gemini-synthetic-observations-v1']
    source: Literal['public_synthetic_document_transcription_not_signed_provider_log']
    observations: list[Observation]=Field(min_length=1,max_length=50)
    @model_validator(mode='after')
    def unique(self):
        if len({o.id for o in self.observations})!=len(self.observations):raise ValueError('duplicate observation')
        return self


class Missing(Record):
    scope: Literal['fact','answer','voice','independence']
    claim_index: int | None=Field(default=None,ge=0)
    detail: str=Field(min_length=6)


class Annotation(Record):
    observation_id: str
    claims: list[Claim]=Field(min_length=1)
    answered: Literal['yes','partial','no','unresolved']
    missing: list[Missing]
    @model_validator(mode='after')
    def missing_locations(self):
        if any(m.claim_index is not None and m.claim_index>=len(self.claims) for m in self.missing):raise ValueError('missing claim index outside annotation')
        for i,c in enumerate(self.claims):
            if c.verdict in ('unsupported','unresolved') and not any(m.scope=='fact' and m.claim_index==i for m in self.missing):raise ValueError('missing fact must locate its claim')
        return self


class References(Record):
    version: Literal['observed-reply-development-reference-v1']
    basis: Literal['author_development_review_not_independent']
    observations_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    annotations: list[Annotation]
    @model_validator(mode='after')
    def unique(self):
        if len({a.observation_id for a in self.annotations})!=len(self.annotations):raise ValueError('duplicate annotation')
        return self


def load(path=OBSERVATIONS):
    return parse_submission(Path(path).read_bytes(),Observations)


def verify_provenance(o):
    # An immutable local Git document proves transcription only, not semantic truth.
    blob=subprocess.check_output(['git','show',o.provenance.commit+':'+o.provenance.path],cwd=ROOT,stderr=subprocess.DEVNULL).decode()
    if o.provenance.anchor not in blob:raise ValueError('missing source anchor')
    section=blob.split(o.provenance.anchor,1)[1]
    if o.reply not in section and json.dumps(o.reply,ensure_ascii=False)[1:-1] not in section:
        raise ValueError('source does not contain original reply')
    context=subprocess.check_output(['git','show',o.provenance.commit+':'+o.provenance.context_path],cwd=ROOT,stderr=subprocess.DEVNULL).decode()
    selected=o.provenance.selected_memory_ids
    if o.provenance.context_path.endswith('.json'):
        c=next(c for c in json.loads(context)['cases'] if c['id']==o.provenance.context_case)
        if c['locale']!=o.locale:raise ValueError('locale drift')
        expected_history=c.get('prior_dialogue',[])+[{'role':'user','content':c['message']}]
        docs={d['id']:d for d in c['documents']}
        if any(id not in docs or docs[id].get('status','confirmed')!='confirmed' or any(docs[id].get(k,False) for k in ('deleted','expired'))
               or docs[id].get('owner','self')!='self' or docs[id].get('character','self')!='self' for id in selected):raise ValueError('ineligible context source')
        expected_evidence=[{'id':'memory_'+id,'kind':'memory','text':docs[id]['fact']} for id in selected]
    else:
        node=next(n for n in ast.parse(context).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CASES' for t in n.targets))
        c=next(c for c in ast.literal_eval(node.value) if c['id']==o.provenance.context_case)
        if c['locale']!=o.locale:raise ValueError('locale drift')
        expected_history=[{'role':'user','content':c['query']}]
        docs=dict(c['documents'])
        if not set(selected)<=set(docs):raise ValueError('unknown selected context')
        expected_evidence=[{'id':'memory_'+id,'kind':'memory','text':docs[id]} for id in selected]
    actual_memories=[e.model_dump() for e in o.evidence if e.kind=='memory']
    if [m.model_dump() for m in o.history]!=expected_history or actual_memories!=expected_evidence:
        raise ValueError('selected context drift')
    # Optional role/scene evidence is checked against the same immutable commit.
    canon=json.loads(subprocess.check_output(['git','show',o.provenance.commit+':characters/shen_yan.json'],cwd=ROOT,stderr=subprocess.DEVNULL))
    canonical={c['id']:c['text'] for c in canon['canon']}
    scene=json.loads(subprocess.check_output(['git','show',o.provenance.commit+':characters/shen_yan_scene.json'],cwd=ROOT,stderr=subprocess.DEVNULL))
    for evidence in o.evidence:
        if evidence.kind=='canon' and canonical.get(evidence.id)!=evidence.text:raise ValueError('canon drift')
        if evidence.kind=='scene' and (evidence.id!='scene_profile' or json.loads(evidence.text)!=scene):raise ValueError('scene drift')
        if evidence.kind=='user':
            expected={f'user_{i}':m.content for i,m in enumerate(o.history) if m.role=='user'}
            if expected.get(evidence.id)!=evidence.text:raise ValueError('user context drift')



def prepare(path,output):
    data=load(path);output=Path(output).resolve()
    if output.is_relative_to(ROOT):raise ValueError('external packet required')
    for o in data.observations:verify_provenance(o)
    packet={'version':'observed-reply-development-reference-v1','basis':'author_development_review_not_independent',
        'observations_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'annotations':[{'observation_id':o.id,'claims':None,'answered':None,'missing':None} for o in data.observations]}
    from scripts.score_annotations import write_report
    write_report(output,packet)
    return {'tasks':len(data.observations),'assessment':'not_assessed','model_calls':0,'ratings':'empty_no_subjective_scores'}


def model_comparison(o,claims,known):
    if o.model_review_observation is None:return {'status':'absent','disagreements':None}
    try:
        review=Review.model_validate(o.model_review_observation)
        if ''.join(s.text for s in review.segments)!=o.reply:raise ValueError('review coverage')
        if any(not set(s.evidence_ids)<=known for s in review.segments):raise ValueError('review source')
    except ValueError:return {'status':'invalid_observation','disagreements':None}
    offsets=[];cursor=0
    for s in review.segments:
        offsets.append((cursor,cursor+len(s.text),s));cursor+=len(s.text)
    disputes=[]
    for c in claims:
        match=next((s for start,end,s in offsets if (start,end)==(c.start,c.end)),None)
        axes=['partition'] if match is None else [name for name,yes in (
            ('kind',match.kind!=c.kind),('verdict',match.verdict!=c.verdict),('evidence',set(match.evidence_ids)!=set(c.evidence_ids))) if yes]
        if axes:disputes.append({'start':c.start,'end':c.end,'axes':axes})
    return {'status':'compared_observation_only','model_decision':review.decision,'disagreements':disputes}


def evaluate(path=OBSERVATIONS,reference=None):
    raw=Path(path).read_bytes();data=load(path);by_id={o.id:o for o in data.observations};annotations={}
    if reference is not None:
        ref=parse_submission(Path(reference).read_bytes(),References)
        if ref.observations_sha256!=hashlib.sha256(raw).hexdigest():raise ValueError('annotation belongs to another observation snapshot')
        annotations={a.observation_id:a for a in ref.annotations}
        if not set(annotations)<=set(by_id):raise ValueError('foreign annotation')
    rows=[]
    for o in data.observations:
        verify_provenance(o);a=annotations.get(o.id)
        if a is None:
            rows.append({'id':o.id,'locale':o.locale,'delivery':o.delivery,'status':'unrated','missing':['complete_claim_annotation'],
                'model_accept_is_reference':False});continue
        known={e.id for e in o.evidence}|{f'user_{i}' for i,m in enumerate(o.history) if m.role=='user'}
        # Reuse exact Unicode partition/source checks from the existing scoring pipeline.
        check_claims(a,SimpleNamespace(candidate=o.reply),known)
        if any(c.verdict in ('unsupported','unresolved') for c in a.claims) and not any(m.scope=='fact' for m in a.missing):
            raise ValueError('missing/unresolved fact must be disclosed')
        if a.answered in ('partial','no','unresolved') and not any(m.scope=='answer' for m in a.missing):
            raise ValueError('missing answer must be disclosed')
        rows.append({'id':o.id,'locale':o.locale,'delivery':o.delivery,'status':'author_reference_checked_not_independent',
            'claim_count':len(a.claims),'verdict_counts':{v:sum(c.verdict==v for c in a.claims) for v in ('supported','contradicted','unsupported','not_applicable','unresolved')},
            'answered':a.answered,'missing_scopes':[m.scope for m in a.missing],
            'model_comparison':model_comparison(o,a.claims,known),'model_accept_is_reference':False})
    return {'tasks':len(rows),'annotated':len(annotations),'unrated':sum(r['status']=='unrated' for r in rows),
        'model_calls':0,'assessment':{'status':'not_assessed','reasons':['author_exposed_reference','independence_not_verified','native_blind_review_pending','insufficient_formal_coverage']},
        'observation_sha256':hashlib.sha256(raw).hexdigest(),'reference_sha256':hashlib.sha256(Path(reference).read_bytes()).hexdigest() if reference else None,
        'results':rows,'limits':'Checks annotation structure, exact spans, source whitelist and transcription. IDs do not prove semantic support. No raw reply, rationale, reviewer identity or subjective score exported. Model accept never supplies reference labels.'}

"""Offline submitted annotations: structural validation and descriptive agreement.

No model, database, gold-label inference or certification of reviewer independence.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field, field_validator, model_validator
from .sealed_evaluation import BUNDLE, ROOT, POLICIES, Record, Message, Evidence, Cases, verify

TaskID=Annotated[str,Field(pattern=r'^T[0-9]{4}$')]
Score=Annotated[int,Field(strict=True,ge=1,le=5)]
Index=Annotated[int,Field(strict=True,ge=0)]


class Claim(Record):
    start: int=Field(ge=0)
    end: int=Field(gt=0)
    text: str=Field(min_length=1)
    kind: Literal['assertion','epistemic','question','suggestion','conditional','quotation']
    verdict: Literal['supported','contradicted','unsupported','not_applicable','unresolved']
    evidence_ids: list[str]
    proposition: str=Field(min_length=1)
    rationale: str=Field(min_length=6)

    @model_validator(mode='after')
    def label_consistency(self):
        factual=self.kind in ('assertion','epistemic')
        if factual==(self.verdict=='not_applicable'):raise ValueError('kind/verdict mismatch')
        if len(set(self.evidence_ids))!=len(self.evidence_ids):raise ValueError('duplicate evidence')
        if self.verdict in ('supported','contradicted') and not self.evidence_ids:
            raise ValueError('supported/contradicted claim needs evidence')
        if not factual and self.evidence_ids:raise ValueError('speech act cannot claim evidence')
        return self


class Rating(Record):
    task_id: TaskID
    claims: list[Claim]=Field(min_length=1)
    fact_issue: bool | None
    role_issue: bool | None
    role_issue_spans: list[Index]
    naturalness: Score
    character_voice: Score
    care_fit: Score | None
    care_fit_na_reason: str | None=None
    answered: bool
    unresolved: bool
    comment: str | None=None

    @model_validator(mode='after')
    def derived_labels(self):
        spans=self.role_issue_spans
        if len(set(spans))!=len(spans) or any(i>=len(self.claims) for i in spans):
            raise ValueError('invalid role spans')
        bad=any(c.verdict in ('unsupported','contradicted') for c in self.claims)
        unknown=any(c.verdict=='unresolved' for c in self.claims)
        if unknown and not self.unresolved:raise ValueError('unresolved claim cannot be hidden')
        if bad and self.fact_issue is not True:raise ValueError('unsafe claim cannot be hidden')
        if self.fact_issue is True and not bad:raise ValueError('fact flag needs unsafe claim')
        if self.role_issue is True and not spans:raise ValueError('role flag needs located span')
        if not self.unresolved and (self.fact_issue!=bad or self.role_issue!=bool(spans)):
            raise ValueError('summary labels disagree with annotations')
        if spans and self.role_issue is not True:raise ValueError('role issue cannot be hidden')
        if not self.unresolved and (self.fact_issue is None or self.role_issue is None):
            raise ValueError('resolved task needs two axis labels')
        if self.care_fit is None and len((self.care_fit_na_reason or '').strip())<6:
            raise ValueError('care NA requires reason')
        if self.care_fit is not None and self.care_fit_na_reason:
            raise ValueError('orphan care NA reason')
        return self


class Reviewer(Record):
    id: str=Field(min_length=1,max_length=100)
    declared_independent: bool

    @field_validator('id')
    @classmethod
    def nonblank(cls,value):
        if not value.strip():raise ValueError('blank reviewer')
        return value.strip()


class Task(Record):
    task_id: TaskID
    history: list[Message]
    evidence: list[Evidence]
    candidate: str=Field(min_length=1)


class Packet(Record):
    annotation_schema: Literal['offline-ratings-v1']='offline-ratings-v1'
    purpose: Literal['synthetic_process_calibration_not_independent_trial']
    profiles: dict
    tasks: list[Task]=Field(min_length=1)
    ratings: list[Rating]=Field(min_length=1)
    reviewer: Reviewer | None=None


class Mapping(Record):
    mapping: dict[TaskID,str]
    manifest_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')


def check_claims(rating,task,known_ids):
    cursor=0
    for claim in rating.claims:
        if claim.start!=cursor or claim.end<=claim.start or task.candidate[claim.start:claim.end]!=claim.text:
            raise ValueError('claims must partition exact Unicode text')
        if not set(claim.evidence_ids)<=known_ids:raise ValueError('unknown or hidden evidence')
        cursor=claim.end
    if cursor!=len(task.candidate):raise ValueError('unannotated reply tail')


def load_inputs(mapping_path,packet_paths,*,bundle=BUNDLE):
    verify(bundle,content=True)
    mapping_bytes=Path(mapping_path).read_bytes()
    mapping=Mapping.model_validate_json(mapping_bytes)
    manifest_bytes=(Path(bundle)/'manifest.json').read_bytes()
    if mapping.manifest_sha256!=hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError('mapping belongs to another frozen bundle')
    cases=Cases.model_validate_json((Path(bundle)/'cases.json').read_bytes())
    by_id={c.id:c for c in cases.cases}
    if len(mapping.mapping)!=len(by_id) or set(mapping.mapping.values())!=set(by_id):
        raise ValueError('mapping must be a complete bijection')
    profiles={name:json.loads((ROOT/name).read_bytes()) for name in sorted(POLICIES) if name.endswith('.json')}
    canon_ids={row['id'] for row in profiles['characters/shen_yan.json']['canon']}
    packets=[];digests=[]
    if not 1<=len(packet_paths)<=2:raise ValueError('need one or two annotation submissions')
    for path in packet_paths:
        raw=Path(path).read_bytes();packet=Packet.model_validate_json(raw)
        tasks={t.task_id:t for t in packet.tasks};ratings={r.task_id:r for r in packet.ratings}
        if len(tasks)!=len(packet.tasks) or len(ratings)!=len(packet.ratings):raise ValueError('duplicate tasks or ratings')
        if set(tasks)!=set(mapping.mapping) or set(ratings)!=set(tasks):raise ValueError('incomplete/foreign submission')
        if packet.profiles!=profiles:raise ValueError('role/scene context changed')
        for task_id,task in tasks.items():
            case=by_id[mapping.mapping[task_id]]
            actual=task.model_dump(exclude={'task_id'})
            expected={'history':[m.model_dump() for m in case.history],
                      'evidence':[e.model_dump() for e in case.evidence],'candidate':case.candidate}
            if actual!=expected:raise ValueError('task text/history/evidence differs from frozen bundle')
            ids={e.id for e in task.evidence}|canon_ids|{'scene_profile','role_profile'}
            ids|={f'user_{i}' for i,m in enumerate(task.history) if m.role=='user'}
            check_claims(ratings[task_id],task,ids)
        packets.append(packet);digests.append(hashlib.sha256(raw).hexdigest())
    return mapping,by_id,packets,{'manifest':mapping.manifest_sha256,
        'mapping':hashlib.sha256(mapping_bytes).hexdigest(),'submissions':digests}


def agreement(left,right,*,weighted=False):
    if len(left)!=len(right):raise ValueError('unpaired ratings')
    n=len(left)
    if not n:return {'n':0,'matches':0,'agreement':None,'kappa':None,'reason':'no_comparable_pairs',
                     'marginals_a':{},'marginals_b':{},'expected_agreement':None}
    pa=Counter(left);pb=Counter(right)
    matches=sum(a==b for a,b in zip(left,right))
    po=matches/n
    if weighted:
        distance=lambda a,b:abs(a-b)/4
        observed=sum(distance(a,b) for a,b in zip(left,right))/n
        expected=sum(distance(a,b)*na*nb for a,na in pa.items() for b,nb in pb.items())/(n*n)
        kappa=1-observed/expected if expected else None
    else:
        chance=sum(pa[v]*pb[v] for v in set(pa)|set(pb))/(n*n)
        kappa=(po-chance)/(1-chance) if chance<1 else None
    return {'n':n,'matches':matches,'agreement':po,'kappa':kappa,
            'marginals_a':{str(v).lower():count for v,count in pa.items()},
            'marginals_b':{str(v).lower():count for v,count in pb.items()},
            'expected_agreement':1-expected if weighted else chance,
            'reason':None if kappa is not None else 'degenerate_marginals',
            'weighting':'linear_1_to_5' if weighted else 'unweighted'}


def rating_summary(ratings):
    result={}
    for name in ('naturalness','character_voice','care_fit'):
        values=[getattr(r,name) for r in ratings if getattr(r,name) is not None]
        result[name]={'n':len(values),'na':len(ratings)-len(values),
            'mean':sum(values)/len(values) if values else None,
            'histogram':{str(i):values.count(i) for i in range(1,6)}}
    result['answered']={'yes':sum(r.answered for r in ratings),'total':len(ratings)}
    result['unresolved']=sum(r.unresolved for r in ratings)
    return result


def compare_packets(a,b):
    left={r.task_id:r for r in a.ratings};right={r.task_id:r for r in b.ratings}
    disputes=[]
    for task_id,x in left.items():
        y=right[task_id];fields=[]
        for name in ('fact_issue','role_issue','unresolved','answered'):
            if getattr(x,name)!=getattr(y,name):fields.append(name)
        bounds=lambda r:[(c.start,c.end) for c in r.claims]
        if bounds(x)!=bounds(y):fields.append('claim_boundaries')
        elif [(c.kind,c.verdict,sorted(c.evidence_ids)) for c in x.claims]!=[(c.kind,c.verdict,sorted(c.evidence_ids)) for c in y.claims]:
            fields.append('claim_labels_or_evidence')
        role_bounds=lambda r:sorted((r.claims[i].start,r.claims[i].end) for i in r.role_issue_spans)
        if role_bounds(x)!=role_bounds(y):fields.append('role_issue_spans')
        for name in ('naturalness','character_voice','care_fit'):
            p,q=getattr(x,name),getattr(y,name)
            if (p is None)!=(q is None):fields.append(name+'_applicability')
            elif p is not None and abs(p-q)>=2:fields.append(name+'_gap')
        if fields:
            def compact(r):
                return {'fact_issue':r.fact_issue,'role_issue':r.role_issue,'answered':r.answered,'unresolved':r.unresolved,
                        'role_issue_spans':r.role_issue_spans,
                        'claims':[c.model_dump(exclude={'text','proposition','rationale'}) for c in r.claims],
                        'scores':{name:getattr(r,name) for name in ('naturalness','character_voice','care_fit')}}
            disputes.append({'task_id':task_id,'fields':fields,'a':compact(x),'b':compact(y)})
    distinct=bool(a.reviewer and b.reviewer and a.reviewer.id.casefold()!=b.reviewer.id.casefold())
    metrics={}
    for name in ('fact_issue','role_issue','answered','unresolved','naturalness','character_voice','care_fit'):
        pairs=[];excluded_reasons=Counter()
        if not distinct:excluded_reasons['reviewer_identity_missing_or_same']=len(left)
        if distinct:
            for task_id,x in left.items():
                y=right[task_id];p,q=getattr(x,name),getattr(y,name)
                if name in ('fact_issue','role_issue') and (x.unresolved or y.unresolved):
                    excluded_reasons['unresolved']+=1;continue
                if p is not None and q is not None:pairs.append((p,q))
                else:excluded_reasons['not_applicable_or_unknown']+=1
        metrics[name]={**agreement([p for p,q in pairs],[q for p,q in pairs],weighted=name in ('naturalness','character_voice','care_fit')),
                       'excluded':len(left)-len(pairs),'excluded_reasons':dict(excluded_reasons)}
        if not distinct:metrics[name]['reason']='reviewer_identity_missing_or_same'
    return disputes,metrics,distinct


def score_files(mapping_path,packet_paths,*,bundle=BUNDLE):
    mapping,cases,packets,hashes=load_inputs(mapping_path,packet_paths,bundle=bundle)
    disputes=[];metrics={};distinct=False
    if len(packets)==2:disputes,metrics,distinct=compare_packets(*packets)
    else:
        metrics={name:{**agreement([],[],weighted=name in ('naturalness','character_voice','care_fit')),
                      'excluded':len(cases),'reason':'second_reviewer_missing',
                      'excluded_reasons':{'second_reviewer_missing':len(cases)}}
                 for name in ('fact_issue','role_issue','answered','unresolved','naturalness','character_voice','care_fit')}
    reasons=['public_author_exposed_candidates','reviewer_independence_not_verified',
             'remaining_m5_metrics_not_assessed']
    if len(packets)<2:reasons.append('second_reviewer_missing')
    elif not distinct:reasons.append('reviewer_identity_missing_or_same')
    if not all(p.reviewer and p.reviewer.declared_independent for p in packets):reasons.append('independence_not_declared')
    if disputes:reasons.append('adjudication_pending')
    if any(r.unresolved for p in packets for r in p.ratings):reasons.append('unresolved_annotations')
    sample_counts={'formal_scenarios':len(cases)}
    for name in ('naturalness','character_voice','care_fit'):
        sample_counts[name+'_pairs']=metrics.get(name,{}).get('n',0)
    for axis in ('fact_issue','role_issue'):
        counts=Counter()
        if len(packets)==2 and distinct:
            right={r.task_id:r for r in packets[1].ratings}
            for x in packets[0].ratings:
                y=right[x.task_id]
                if not x.unresolved and not y.unresolved and getattr(x,axis) is not None and getattr(x,axis)==getattr(y,axis):
                    counts[getattr(x,axis)]+=1
        sample_counts[axis+'_positive']=counts[True]
        sample_counts[axis+'_negative']=counts[False]
    minimums={name:120 if name=='formal_scenarios' else 50 for name in sample_counts}
    if any(sample_counts[name]<minimum for name,minimum in minimums.items()):reasons.append('insufficient_formal_sample')
    per_stratum={}

    for stratum in sorted({c.stratum for c in cases.values()}):
        ids={task for task,case_id in mapping.mapping.items() if cases[case_id].stratum==stratum}
        per_stratum[stratum]={'tasks':len(ids),'rater_summaries':[
            rating_summary([r for r in p.ratings if r.task_id in ids]) for p in packets]}
        if len(packets)==2:
            subset=[p.model_copy(update={'ratings':[r for r in p.ratings if r.task_id in ids]}) for p in packets]
            per_stratum[stratum]['agreement']=compare_packets(*subset)[1]
    return {'mode':'offline_submitted_annotation_summary','model_calls':0,
        'tasks':len(mapping.mapping),'submissions':len(packets),'input_sha256':hashes,
        'rater_summaries':[rating_summary(p.ratings) for p in packets],
        'declared_independent':[bool(p.reviewer and p.reviewer.declared_independent) for p in packets],
        'distinct_submitted_ids':distinct,'agreement':metrics,'disagreements':disputes,
        'disagreement_count':len(disputes),
        'unresolved_tasks':sorted({r.task_id for p in packets for r in p.ratings if r.unresolved}),'per_stratum':per_stratum,
        'assessment':{'status':'not_assessed','reasons':reasons,
            'sample_counts_pre_adjudication':sample_counts,'minimums':minimums},
        'limits':'Structure and known evidence IDs are checked, not semantic entailment. Agreement is descriptive, not accuracy or verified independence. No adjudication, model execution or automatic M5 acceptance. Comments, reviewer IDs and candidate text omitted.'}

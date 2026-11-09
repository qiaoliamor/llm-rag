"""Offline freeze checks and label-blind annotation preparation, never model testing."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

ROOT=Path(__file__).resolve().parent.parent
BUNDLE=ROOT/'evaluations/sealed/v2'
STRATA=('memory','canon','weather','emotion','security','narrative')
ARTIFACTS={'cases.json','author_reference.json'}
POLICIES={'characters/shen_yan.json','characters/shen_yan_scene.json','app/dialogue.py','app/semantic_review.py'}


class Record(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)


class Message(Record):
    role: Literal['user','assistant']
    content: str=Field(min_length=1)


class Evidence(Record):
    id: str=Field(min_length=1)
    kind: Literal['memory','weather','emotion']
    text: str=Field(min_length=1)


class Case(Record):
    id: str=Field(min_length=1)
    stratum: Literal['memory','canon','weather','emotion','security','narrative']
    family: str=Field(min_length=1)
    history: list[Message]=Field(min_length=1)
    evidence: list[Evidence]
    candidate: str=Field(min_length=1)

    @model_validator(mode='after')
    def context(self):
        if self.history[-1].role!='user':raise ValueError('current user required')
        if len({e.id for e in self.evidence})!=len(self.evidence):raise ValueError('duplicate evidence')
        return self


class Cases(Record):
    version: Literal['sealed-candidate-v1','sealed-candidate-v2']
    source: Literal['synthetic']
    visibility: Literal['public_author_exposed']
    cases: list[Case]=Field(min_length=1)

    @model_validator(mode='after')
    def unique(self):
        if len({c.id for c in self.cases})!=len(self.cases):raise ValueError('duplicate case')
        return self


class Reference(Record):
    id: str
    fact_issue: bool
    role_issue: bool
    reason: str=Field(min_length=6)
    expected_tool: Literal['none','memory','weather','emotion']
    annotation_status: Literal['author_draft']


class References(Record):
    version: Literal['author-draft-v1','author-draft-v2']
    independent: Literal[False]
    references: list[Reference]


class Manifest(Record):
    version: Literal['sealed-manifest-v1','sealed-manifest-v2']
    status: Literal['frozen_public_candidate_not_independent']
    frozen_on: str
    baseline_commit: str=Field(pattern=r'^[0-9a-f]{40}$')
    parent_manifest_sha256: str | None=None
    revision_reason: str | None=None
    case_count: int=Field(gt=0)
    strata: dict[str,int]
    artifacts: dict[str,str]
    policy_artifacts: dict[str,str]
    independent_annotation: Literal['pending']
    blind_review: Literal['pending']
    model_execution: Literal['not_run']
    acceptance: Literal['not_assessed']

    @model_validator(mode='after')
    def paths_and_counts(self):
        from datetime import date
        date.fromisoformat(self.frozen_on)
        if self.version=='sealed-manifest-v2':
            parent=self.parent_manifest_sha256 or ''
            if len(parent)!=64 or any(c not in '0123456789abcdef' for c in parent) or not self.revision_reason:
                raise ValueError('v2 requires frozen parent and revision reason')
        if set(self.artifacts)!=ARTIFACTS or set(self.policy_artifacts)!=POLICIES:
            raise ValueError('unexpected artifact paths')
        for digest in [*self.artifacts.values(),*self.policy_artifacts.values()]:
            if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
                raise ValueError('invalid digest')
        if set(self.strata)!=set(STRATA) or any(n<=0 for n in self.strata.values()) or sum(self.strata.values())!=self.case_count:
            raise ValueError('invalid strata counts')
        return self


def verify(bundle=BUNDLE,*,content=False):
    bundle=Path(bundle)
    manifest=Manifest.model_validate_json((bundle/'manifest.json').read_bytes())
    if manifest.version=='sealed-manifest-v2':
        parent=ROOT/'evaluations/sealed/v1/manifest.json'
        if hashlib.sha256(parent.read_bytes()).hexdigest()!=manifest.parent_manifest_sha256:
            raise ValueError('frozen v1 parent drift')
    for name,digest in manifest.artifacts.items():
        if hashlib.sha256((bundle/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('frozen artifact drift; create a new version')
    for name,digest in manifest.policy_artifacts.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('policy drift; frozen baseline cannot be reused')
    if content:
        cases=Cases.model_validate_json((bundle/'cases.json').read_bytes())
        refs=References.model_validate_json((bundle/'author_reference.json').read_bytes())
        suffix='v2' if manifest.version=='sealed-manifest-v2' else 'v1'
        if cases.version!='sealed-candidate-'+suffix or refs.version!='author-draft-'+suffix:
            raise ValueError('bundle schema versions disagree')
        ids=[c.id for c in cases.cases]
        if len(ids)!=manifest.case_count or dict(Counter(c.stratum for c in cases.cases))!=manifest.strata:
            raise ValueError('case counts differ')
        if len(refs.references)!=len(ids) or {r.id for r in refs.references}!=set(ids):
            raise ValueError('missing/duplicate reference')
    return manifest


def prepare(output,*,bundle=BUNDLE,seed=None):
    """Synthetic calibration packet only. Do not publish the private ID mapping."""
    manifest=verify(bundle,content=True)
    output=Path(output).resolve()
    if output.is_relative_to(ROOT):raise ValueError('annotation exports must stay outside repository')
    if output.exists():raise ValueError('refuse to overwrite annotation exports')
    if not output.parent.is_dir():raise ValueError('output parent must exist')
    cases=Cases.model_validate_json((Path(bundle)/'cases.json').read_bytes()).cases
    rng=random.Random(seed)
    profiles={name:json.loads((ROOT/name).read_bytes()) for name in sorted(POLICIES) if name.endswith('.json')}
    rows=list(cases);rng.shuffle(rows)
    mapping={f'T{i:04}':case.id for i,case in enumerate(rows,1)}
    tasks=[{'task_id':task,'history':[m.model_dump() for m in case.history],
            'evidence':[e.model_dump() for e in case.evidence],'candidate':case.candidate}
           for task,case in zip(mapping,rows)]
    temp=Path(tempfile.mkdtemp(prefix='annotation-',dir=output.parent))
    try:
        for rater in ('rater_a','rater_b'):
            order=list(tasks);rng.shuffle(order)
            packet={'purpose':'synthetic_process_calibration_not_independent_trial','annotation_schema':'offline-ratings-v1','reviewer':None,
                    'profiles':profiles,'tasks':order,
                    'ratings':[{'task_id':t['task_id'],'claims':None,'fact_issue':None,'role_issue':None,'role_issue_spans':None,
                                'naturalness':None,'character_voice':None,'care_fit':None,'care_fit_na_reason':None,'answered':None,
                                'unresolved':None,'comment':None} for t in order]}
            (temp/f'{rater}.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
        (temp/'custodian_mapping.json').write_text(json.dumps({'mapping':mapping,
            'manifest_sha256':hashlib.sha256((Path(bundle)/'manifest.json').read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n')
        temp.rename(output)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True)
        raise
    return {'tasks_per_rater':manifest.case_count,'raters':2,'reference_labels_exported':False,
            'model_calls':0,'independence':'not_established'}

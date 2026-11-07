"""Text candidate retrieval plus authored semantic review; no embedding or oracle."""
import ast
from collections import Counter
import hashlib
import json
from typing import Literal
from pydantic import Field, model_validator
from .narrative_calibration import ROOT, Dataset, Record, load_dataset

V2 = ROOT / 'evaluations/narrative_calibration_v2.json'
AUDIT = ROOT / 'evaluations/narrative_reference_audit.json'


class DatasetV2(Dataset):
    version: Literal['narrative-calibration-dev-v2']


class Source(Record):
    path: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')

    @model_validator(mode='after')
    def local_source(self):
        path = ROOT / self.path
        if path.is_absolute() and not path.resolve().is_relative_to(ROOT):
            raise ValueError('source outside repository')
        if not self.path.startswith(('evaluations/', 'tests/', 'app/', 'characters/', 'prompts/')):
            raise ValueError('source outside authored corpus')
        if path.suffix not in ('.json', '.py', '.md'):
            raise ValueError('unsupported source')
        return self


class Reference(Record):
    path: str
    anchor: str = Field(min_length=5)
    relation: Literal['same_mechanism', 'counterexample', 'policy_changed', 'exact_reply']


class AnnotationReview(Record):
    case_id: str
    family: str = Field(min_length=3)
    fact_issue: bool
    role_issue: bool
    conclusion: Literal['retain', 'new']
    note: str = Field(min_length=10)
    references: list[Reference] = Field(min_length=1)


class Audit(Record):
    version: Literal['narrative-reference-audit-v1']
    reviewer: Literal['implementer_second_pass_not_independent']
    target_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    sources: list[Source] = Field(min_length=1)
    reviews: list[AnnotationReview] = Field(min_length=1)


def source_inventory():
    # All pre-existing fixtures/tests, production prompt carriers and design text.
    return sorted(set(
        [str(p.relative_to(ROOT)) for p in (ROOT/'evaluations').glob('*.json')
         if p.name not in ('narrative_calibration_v2.json', 'narrative_reference_audit.json')]
        + [str(p.relative_to(ROOT)) for p in (ROOT/'tests').glob('test_*.py')
           if p.name != 'test_reference_audit.py']
        + ['tests/scenarios.json', 'app/dialogue.py', 'app/semantic_review.py',
           'app/grounding.py', 'app/memory_source.py', 'characters/shen_yan.json',
           'characters/shen_yan_scene.json', 'prompts/DESIGN.md']))


def load_audit():
    data, digest = load_dataset(V2, model=DatasetV2)
    audit = Audit.model_validate_json(AUDIT.read_bytes())
    if digest != audit.target_sha256:
        raise ValueError('target drift: review annotations and semantic links')
    sources = {s.path:s for s in audit.sources}
    if len(sources) != len(audit.sources) or set(sources) != set(source_inventory()):
        raise ValueError('source inventory drift')
    texts = {}
    for source in audit.sources:
        raw = (ROOT/source.path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != source.sha256:
            raise ValueError('source drift: refresh semantic review')
        texts[source.path] = raw.decode()
    reviews = {r.case_id:r for r in audit.reviews}
    if len(reviews) != len(audit.reviews) or set(reviews) != {c.id for c in data.cases}:
        raise ValueError('incomplete or duplicate reference review')
    original, _ = load_dataset()
    if [c.model_dump() for c in data.cases[:len(original.cases)]] != [c.model_dump() for c in original.cases]:
        raise ValueError('v1 references must remain unchanged')
    old_ids = {c.id for c in original.cases}
    for case in data.cases:
        row = reviews[case.id]
        if (row.fact_issue, row.role_issue) != (case.fact_issue, case.role_issue):
            raise ValueError('review/reference label disagreement')
        if row.conclusion != ('retain' if case.id in old_ids else 'new'):
            raise ValueError('incorrect review lineage')
        for ref in row.references:
            if ref.path not in texts or ref.anchor not in texts[ref.path]:
                raise ValueError('semantic reference outside snapshot or stale anchor')
    return data, audit, texts


def normalize(text):
    return ''.join(ch for ch in text.casefold() if ch.isalnum())


def grams(text):
    text = normalize(text)
    return {text[i:i+3] for i in range(max(0, len(text)-2))}


def similarity(a,b):
    left,right = grams(a),grams(b)
    return len(left & right)/len(left | right) if left and right else 0.0


def source_units(path,text):
    if path.endswith('.py'):
        # Literal strings only; never import/execute tests or production prompts.
        return [(f'{path}:L{node.lineno}',node.value) for node in ast.walk(ast.parse(text))
                if isinstance(node,ast.Constant) and isinstance(node.value,str) and len(normalize(node.value))>=8]
    if path.endswith('.json'):
        obj=json.loads(text)
        units=[]
        def visit(value, pointer):
            if isinstance(value,dict):
                name = value.get('id')
                if isinstance(name,str): pointer += '@'+name
                for key,item in value.items():visit(item,pointer+'/'+key)
            elif isinstance(value,list):
                for i,item in enumerate(value):visit(item,pointer+'/'+str(i))
            elif isinstance(value,str) and len(normalize(value))>=8:
                units.append((path+'#'+pointer,value))
        visit(obj,'')
        return units
    return [(path+f':L{i}',line) for i,line in enumerate(text.splitlines(),1) if len(normalize(line))>=8]


def candidate_matches(reply, units, limit=3):
    """Surface cues only; Jaccard/substrings are NOT semantic equivalence."""
    target=normalize(reply)
    matches=[]
    for source,text in units:
        norm=normalize(text)
        exact=target==norm
        embedded=bool(target) and target in norm
        value=1.0 if embedded else similarity(reply,text)
        if value>=0.12:
            matches.append({'source':source,'surface_score':round(value,4),
                            'cue':'exact_text' if exact else 'embedded_text' if embedded else 'trigram_candidate'})
    return sorted(matches,key=lambda r:(-r['surface_score'],r['source']))[:limit]


def evaluate_audit():
    data,audit,texts=load_audit()
    units=[u for path,text in texts.items() for u in source_units(path,text)]
    rows=[]
    for case,review in zip(data.cases, [next(r for r in audit.reviews if r.case_id==c.id) for c in data.cases]):
        rows.append({'id':case.id,'family':review.family,'expected':case.expected,
                     'fact_issue':case.fact_issue,'role_issue':case.role_issue,
                     'semantic_links':[r.model_dump() for r in review.references],
                     'surface_candidates':candidate_matches(case.reply,units)})
    return {'mode':'offline_reference_audit_not_model_quality','target_version':data.version,
            'target_sha256':audit.target_sha256,'source_files':len(texts),'source_units':len(units),
            'cases':len(rows),'retained':sum(r.conclusion=='retain' for r in audit.reviews),
            'added':sum(r.conclusion=='new' for r in audit.reviews),
            'family_counts':dict(Counter(r.family for r in audit.reviews)),
            'independent_samples':None,'api_calls':0,'results':rows,
            'limits':'Manual implementer semantic links plus surface candidates, not trained embeddings, exhaustive equivalence, independent annotation, or held-out model scores. Old holdout text is read for overlap audit only, never executed; do not claim it remains unseen.'}

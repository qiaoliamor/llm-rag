"""Versioned authored calibration; neither an oracle nor independent holdout."""
import hashlib
from collections import Counter
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .semantic_review import evidence_bundle

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / 'evaluations/narrative_calibration_dev.json'
LIVE_IDS = ('scene-stock-completed', 'place-correction-quote')


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Message(Record):
    role: Literal['user', 'assistant']
    content: str = Field(min_length=1)


class Memory(Record):
    id: str = Field(min_length=1)
    fact: str = Field(min_length=1)
    event_date: str | None

    @model_validator(mode='after')
    def date_format(self):
        if self.event_date is not None:
            from datetime import date
            date.fromisoformat(self.event_date)
        return self


class Case(Record):
    id: str = Field(min_length=1)
    category: Literal['event', 'quotation', 'atmosphere', 'voice', 'player', 'canon', 'weather', 'mixed', 'source_time']
    history: list[Message] = Field(min_length=1)
    reply: str = Field(min_length=1, max_length=2500)
    memories: list[Memory]
    fact_issue: bool
    role_issue: bool
    rationale: str = Field(min_length=6)
    prior_failure: str | None

    @model_validator(mode='after')
    def valid_context(self):
        if self.history[-1].role != 'user':
            raise ValueError('last message must be current user')
        if len({m.id for m in self.memories}) != len(self.memories):
            raise ValueError('duplicate memory')
        if (self.id in LIVE_IDS) != bool(self.prior_failure):
            raise ValueError('live eligibility must have fixed historical failure provenance')
        return self

    @property
    def expected(self):
        return 'revise' if self.fact_issue or self.role_issue else 'accept'

    def context(self):
        history = [m.model_dump() for m in self.history]
        memories = [m.model_dump() for m in self.memories]
        return history, evidence_bundle(history, memories, None, None)


class Dataset(Record):
    version: Literal['narrative-calibration-dev-v1']
    source: Literal['synthetic']
    annotation_method: Literal['author_reference_not_independent']
    scene_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    character_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    cases: list[Case] = Field(min_length=1)

    @model_validator(mode='after')
    def unique(self):
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError('duplicate case')
        if not set(LIVE_IDS) <= {c.id for c in self.cases}:
            raise ValueError('missing frozen live failures')
        return self


def load_dataset(path=DATASET):
    raw = Path(path).read_bytes()
    data = Dataset.model_validate_json(raw)
    for name, digest in [('shen_yan_scene.json', data.scene_sha256), ('shen_yan.json', data.character_sha256)]:
        if hashlib.sha256((ROOT / 'characters' / name).read_bytes()).hexdigest() != digest:
            raise ValueError('policy drift: review labels before reuse')
    return data, hashlib.sha256(raw).hexdigest()


def score(case, outcome):
    """Unavailable/uncertain never counts as a successful rejection."""
    usable = outcome.status in ('accept', 'revise') and outcome.result is not None
    fact = any(s.verdict in ('unsupported', 'contradicted') for s in outcome.result.segments) if usable else None
    role = bool(outcome.result.role_issues) if usable else None
    return {'id': case.id, 'category': case.category, 'expected': case.expected,
            'expected_fact_issue': case.fact_issue, 'expected_role_issue': case.role_issue,
            'status': outcome.status, 'failure': outcome.failure, 'usable': usable,
            'fact_issue': fact, 'role_issue': role,
            'decision_match': usable and outcome.status == case.expected,
            'axes_match': usable and fact == case.fact_issue and role == case.role_issue}


def summarize(rows):
    def axis(name):
        valid = [r for r in rows if r['usable']]
        return {key: sum(r[name] == pred and r['expected_' + name] == ref for r in valid)
                for key, pred, ref in [('tp', True, True), ('fp', True, False), ('fn', False, True), ('tn', False, False)]}
    return {'attempts': len(rows), 'usable': sum(r['usable'] for r in rows),
            'decision_matches': sum(r['decision_match'] for r in rows),
            'both_axes_matches': sum(r['axes_match'] for r in rows),
            'failures': dict(Counter(r['failure'] for r in rows if r['failure'])),
            'fact_issue': axis('fact_issue'), 'role_issue': axis('role_issue'),
            'limits': 'Confusion matrices exclude unavailable/uncertain; matches use all attempts. Authored development labels, not independent quality or generation scores.'}

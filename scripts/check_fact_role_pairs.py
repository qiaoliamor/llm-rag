"""Offline authored test preparation only; no model execution or quality score."""
import json
from pathlib import Path
import sys
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pydantic import Field, model_validator
from app.narrative_calibration import Case, Record, ROOT, load_dataset

DATASET = ROOT / 'evaluations/fact_role_pairs_dev.json'
FAMILIES = {'source_time', 'arrival', 'correction', 'canon', 'scene_event',
            'weather', 'voice', 'quotation'}


class Pair(Record):
    family: str
    axis: Literal['fact', 'role']
    allowed: Case
    violating: Case

    @model_validator(mode='after')
    def paired_reference(self):
        a, b = self.allowed, self.violating
        if (a.history, a.memories, a.category) != (b.history, b.memories, b.category):
            raise ValueError('paired context mismatch')
        if a.reply == b.reply or a.id == b.id:
            raise ValueError('pair must differ')
        if a.fact_issue or a.role_issue:
            raise ValueError('allowed reference must have neither issue')
        if (b.fact_issue, b.role_issue) != (self.axis == 'fact', self.axis == 'role'):
            raise ValueError('violating reference must target exactly one axis')
        if a.prior_failure or b.prior_failure:
            raise ValueError('new preparation has no live eligibility')
        return self


class Dataset(Record):
    version: Literal['fact-role-pairs-dev-v1']
    source: Literal['synthetic']
    annotation_method: Literal['author_reference_not_independent']
    scene_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    character_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    pairs: list[Pair]

    @model_validator(mode='after')
    def coverage(self):
        if len(self.pairs) != len(FAMILIES) or {p.family for p in self.pairs} != FAMILIES:
            raise ValueError('missing or duplicate mechanism family')
        cases = [c for p in self.pairs for c in (p.allowed, p.violating)]
        if len({c.id for c in cases}) != len(cases):
            raise ValueError('duplicate case')
        if len({c.reply for c in cases}) != len(cases):
            raise ValueError('duplicate reply')
        return self


def validate():
    # Reuse strict reference/context models and character policy-drift guard.
    data, digest = load_dataset(DATASET, model=Dataset)
    return {'mode': 'reference_validation_only', 'version': data.version,
            'dataset_sha256': digest, 'pairs': len(data.pairs),
            'cases': len(data.pairs) * 2, 'families': sorted(FAMILIES),
            'max_calls': 0, 'independent_annotation': 'pending',
            'acceptance': 'not_assessed',
            'limits': 'Authored paired references; not semantic judgment, model accuracy, or independent evaluation.'}


def main():
    if len(sys.argv) != 1:
        print('This offline checker accepts no arguments.', file=sys.stderr)
        return 2
    try:
        print(json.dumps(validate(), ensure_ascii=False, indent=2))
        return 0
    except Exception:
        print('Reference validation failed; no raw input is displayed.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

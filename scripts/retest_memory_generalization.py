"""Two prior fault-replay categories, at most eight real calls, no retry/rewrite."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT,Settings
from app.dialogue import build_provider,ProviderFailure
from app.fact_presentation import FactAnalysisProvider
from app.memory_understanding import ModelMemoryUnderstanding
from app.japanese_memory_layers import load,CURRENT_POLICY_DATASET,Probe,_run_probe
from scripts.retest_same_language_memory import Ledger

CASES=('zh-persisted-correction','ja-no-answer')


class Budget(Ledger):
    def __init__(self,ids):super().__init__();self.ids=ids;self.cap=4*len(ids);self.stopped=False;self.blocked=[]
    async def call(self,case,stage,operation):
        if self.stopped or len(self.calls)>=self.cap or sum(c['case']==case for c in self.calls)>=4 or any(c['case']==case and c['stage']==stage for c in self.calls):
            self.blocked.append({'case':case,'stage':stage,'reason':'stopped_or_call_cap'})
            raise ProviderFailure('test_call_budget','No extra real request permitted.',503)
        try:return await super().call(case,stage,operation)
        except BaseException:
            self.stopped=True;raise


def complete(row):
    return (row['http_status']==200 and row['selection']['reference_match'] is True
        and (row.get('semantic_review') or {}).get('status')=='accepted'
        and (row['observations'].get('memory_understanding') or {}).get('status')=='ready'
        and bool(row['observations']['reviews']))


def run(settings,ids=CASES):
    if not ids or len(set(ids))!=len(ids) or not set(ids)<=set(CASES):raise ValueError('fixed synthetic failure categories only')
    budget=Budget(ids);rows=[];data={c.id:c for c in load(CURRENT_POLICY_DATASET).cases}
    model=ModelMemoryUnderstanding(settings);generator=build_provider(settings);judge=FactAnalysisProvider(settings)
    with tempfile.TemporaryDirectory(prefix='memory-generalization-') as scratch:
        for i,id in enumerate(ids):
            class Analyst:
                async def analyze(self,data):return await budget.call(id,'plan',lambda:model.analyze(data))
                async def select(self,data):return await budget.call(id,'selection',lambda:model.select(data))
            class Generator:
                async def generate(self,history,prompt):return await budget.call(id,'generation',lambda:generator.generate(history,prompt))
            class Judge:
                async def review(self,reply,history,evidence):return await budget.call(id,'review',lambda:judge.review(reply,history,evidence))
            with patch.dict(Settings.model_config,env_file=None),patch.dict(os.environ,CHAT_PROVIDER='mock',WEATHER_PROVIDER='mock',
                    GEMINI_API_KEY='',OPENAI_API_KEY='',MEMORY_DATABASE_URL='sqlite:///'+str(Path(scratch)/'bootstrap.sqlite3')):
                row=_run_probe(data[id],Probe(id='reference'),'sqlite:///'+str(Path(scratch)/f'case-{i}.sqlite3'),
                    providers={'understander':Analyst(),'generator':Generator(),'judge':Judge()})
            row['technical_complete']=bool(complete(row));rows.append(row)
            if budget.stopped or not row['technical_complete']:break
    return {'mode':'bounded_bilingual_actual_memory_stages','model':settings.selected_model,'max_calls':budget.cap,
        'attempted_calls':len(budget.calls),'calls':budget.calls,'blocked':budget.blocked,'results':rows,
        'unattempted_ids':list(ids[len(rows):]),'memory_budget':{'plan_seconds':settings.memory_understanding_timeout_seconds,
            'selection_seconds':settings.memory_selection_timeout_seconds},
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('app/fact_presentation.py','app/memory_understanding.py',
            'app/japanese_memory_layers.py','app/main.py','app/reply_pipeline.py','evaluations/current_policy/bilingual_memory_acceptance_v1.json','scripts/retest_memory_generalization.py')},
        'assessment':'not_assessed','limits':'Real model planning/selection/generation/review on fixed public synthetic fault categories; max four calls each, one run, stop on error, no live rewrite. Technical completion is not semantic truth or independent native quality; unfamiliar replies remain unrated.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');parser.add_argument('--case',choices=CASES)
    args=parser.parse_args()
    if not args.live:parser.error('--live required; max 8 calls, no retry')
    from dotenv import dotenv_values
    values=dotenv_values(ROOT/'.env');key=os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY','')
    if not key:parser.error('local key required, omitted')
    kwargs={n:os.environ.get(n.upper()) or values.get(n.upper()) or Settings.model_fields[n].default for n in
            ('gemini_model','memory_understanding_timeout_seconds','memory_selection_timeout_seconds')}
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=key,dialogue_mode='companion',growth_enabled=True,
        memory_understanding_mode='semantic',reply_understanding_mode='semantic',weather_understanding_mode='semantic',emotion_understanding_mode='semantic',**kwargs)
    try:r=run(settings,(args.case,) if args.case else CASES)
    except Exception:
        print('Synthetic test incomplete; private configuration/exception omitted.',file=sys.stderr);return 2
    encoded=json.dumps(r,ensure_ascii=False,indent=2)
    if key in encoded:raise SystemExit('Sensitive output blocked')
    print(encoded);return int(bool(r['unattempted_ids']) or bool(r['blocked']) or any(not row['technical_complete'] for row in r['results']))


if __name__=='__main__':raise SystemExit(main())

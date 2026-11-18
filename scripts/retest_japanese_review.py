"""Two calls only: V5 generation/review after replaying the successful empty selection."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from pydantic import ValidationError
from app.config import ROOT,Settings
from app.dialogue import build_provider
from app.fact_presentation import FactAnalysisProvider,POLICY_VERSION,REVIEW_COMPOSITION_VERSION
from app.japanese_memory_layers import load,CURRENT_POLICY_DATASET,Probe,_run_probe
from scripts.retest_memory_generalization import Budget

PRIOR_COMMIT='4799ccf6a9f33fa62b5241d92631dbc6c1d120f0'
FROZEN_PLAN={'memory_use':'allow','need_memory':True,'query':'飼っている犬の名前',
    'target_slots':['preference','other'],'reason':'personal_history_needed','confidence':.9,'candidates':[]}
FROZEN_SELECTION=[]


class DiagnosticJudge(FactAnalysisProvider):
    """Test-only fixed error codes. Never export SDK input, exception text or config."""
    def __init__(self,settings):super().__init__(settings);self.diagnostics=[];self.prompt_lengths=[]
    async def parse(self,schema,prompt,data,timeout,tokens):
        self.prompt_lengths.append(len(self.prompt_for(data)))
        try:return await super().parse(schema,prompt,data,timeout,tokens)
        except ValidationError as error:
            self.diagnostics.append({'stage':'schema','codes':sorted({e['type'] for e in error.errors(include_input=False,include_context=False,include_url=False)})})
            raise
        except Exception as error:
            self.diagnostics.append({'stage':'parse','exception_type':type(error).__name__})
            raise
    async def review(self,*args):
        try:return await super().review(*args)
        except ValueError as error:
            code=str(error)
            self.diagnostics.append({'stage':'review','code':code if code in {'invalid_unit_coverage','invalid_role_issue_units','review_input_limit'} else 'invalid_review'})
            raise


def run(settings):
    case=next(c for c in load(CURRENT_POLICY_DATASET).cases if c.id=='ja-no-answer')
    budget=Budget(('ja-no-answer',));budget.cap=2
    generator=build_provider(settings);judge=DiagnosticJudge(settings)
    class Generator:
        async def generate(self,history,prompt):return await budget.call(case.id,'generation',lambda:generator.generate(history,prompt))
    class Judge:
        async def review(self,reply,history,evidence):return await budget.call(case.id,'review',lambda:judge.review(reply,history,evidence))
    with tempfile.TemporaryDirectory(prefix='japanese-review-v5-') as scratch:
        with patch.dict(Settings.model_config,env_file=None),patch.dict(os.environ,CHAT_PROVIDER='mock',WEATHER_PROVIDER='mock',
                GEMINI_API_KEY='',OPENAI_API_KEY='',MEMORY_DATABASE_URL='sqlite:///'+str(Path(scratch)/'bootstrap.sqlite3')):
            row=_run_probe(case,Probe(id='reference'),'sqlite:///'+str(Path(scratch)/'synthetic.sqlite3'),providers={
                'generator':Generator(),'judge':Judge(),'frozen_plan':FROZEN_PLAN,'frozen_selection':FROZEN_SELECTION})
    complete=bool(row['http_status']==200 and row['context']['ids']==[] and row['selection']['reference_match'] is True
        and row['observations']['reviews'] and (row['semantic_review'] or {}).get('status')=='accepted')
    row['technical_complete']=complete
    paths=('app/fact_presentation.py','app/semantic_review.py','app/japanese_memory_layers.py','app/reply_pipeline.py','app/main.py',
        'evaluations/current_policy/bilingual_memory_acceptance_v1.json','scripts/retest_japanese_review.py','scripts/retest_memory_generalization.py')
    return {'mode':'replayed_empty_selection_v5_tail','model':settings.selected_model,'policy':POLICY_VERSION,
        'review_composition':REVIEW_COMPOSITION_VERSION,'prior_commit':PRIOR_COMMIT,'replayed_plan':FROZEN_PLAN,'replayed_selection':FROZEN_SELECTION,
        'max_calls':2,'attempted_calls':len(budget.calls),'calls':budget.calls,'blocked':budget.blocked,'result':row,
        'diagnostics':judge.diagnostics,'review_prompt_characters':judge.prompt_lengths,
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
        'assessment':'not_assessed','limits':'Prior successful synthetic query/empty selection replayed, not new predictions. One generation and one review maximum; stop on error, no retry or live rewrite. Unknown output remains unrated. No native blind review or stability claim.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:parser.error('--live required; maximum 2 calls, no retry')
    from dotenv import dotenv_values
    values=dotenv_values(ROOT/'.env');key=os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY','')
    if not key:parser.error('Local key required; omitted')
    model=os.environ.get('GEMINI_MODEL') or values.get('GEMINI_MODEL') or Settings.model_fields['gemini_model'].default
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=key,gemini_model=model,dialogue_mode='companion',
        memory_understanding_mode='semantic',reply_understanding_mode='semantic',weather_understanding_mode='semantic',emotion_understanding_mode='semantic')
    try:report=run(settings)
    except Exception:
        print('Synthetic run incomplete; private configuration/exception omitted.',file=sys.stderr);return 2
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if key in encoded:raise SystemExit('Sensitive output blocked')
    print(encoded);return int(bool(report['blocked']) or not report['result']['technical_complete'])


if __name__=='__main__':raise SystemExit(main())

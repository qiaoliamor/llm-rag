"""Three-call cap: previously incomplete Japanese reply tail and wrong canon evidence only."""
import argparse
import asyncio
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
from app.japanese_memory_layers import load,CURRENT_POLICY_DATASET,_run_probe,Probe
from app.semantic_review import review_reply,evidence_bundle
from scripts.retest_same_language_memory import Ledger

CASES=('ja-subject-tail','ja-canon-review')
FROZEN_PLAN={'memory_use':'allow','need_memory':True,'query':'妹 面接','target_slots':['history','other'],
             'reason':'personal_history_needed','confidence':.9,'candidates':[]}
PRIOR_COMMIT='ed5f51ef7e24e97aa260c91169c1686eb9f383ce'


class Budget(Ledger):
    def __init__(self,ids):
        super().__init__();self.ids=ids;self.blocked=[]
        self.cap=sum(2 if id=='ja-subject-tail' else 1 for id in ids)
    async def call(self,case,stage,operation):
        per_case=2 if case=='ja-subject-tail' else 1
        if len(self.calls)>=self.cap or sum(c['case']==case for c in self.calls)>=per_case:
            self.blocked.append({'case':case,'stage':stage,'reason':'no_additional_live_call'})
            raise ProviderFailure('test_call_budget','Synthetic test call cap reached; rewrite not attempted.',503)
        return await super().call(case,stage,operation)


def run(settings,ids=CASES):
    if not ids or len(set(ids))!=len(ids) or not set(ids)<=set(CASES):raise ValueError('fixed previous failures only')
    budget=Budget(ids);rows=[];generator=build_provider(settings);judge=FactAnalysisProvider(settings)
    with tempfile.TemporaryDirectory(prefix='current-policy-tail-') as scratch:
        for id in ids:
            if id=='ja-subject-tail':
                case=next(c for c in load(CURRENT_POLICY_DATASET).cases if c.id=='ja-subject-sister')
                class Generator:
                    async def generate(self,history,prompt):return await budget.call(id,'generation',lambda:generator.generate(history,prompt))
                class Judge:
                    async def review(self,reply,history,evidence):return await budget.call(id,'review',lambda:judge.review(reply,history,evidence))
                # Prevent the module-level app from reading .env or opening a player store.
                bootstrap='sqlite:///'+str(Path(scratch)/'bootstrap.sqlite3')
                with patch.dict(Settings.model_config,env_file=None),patch.dict(os.environ,CHAT_PROVIDER='mock',WEATHER_PROVIDER='mock',
                        GEMINI_API_KEY='',OPENAI_API_KEY='',MEMORY_DATABASE_URL=bootstrap):
                    row=_run_probe(case,Probe(id='reference'),'sqlite:///'+str(Path(scratch)/'synthetic.sqlite3'),providers={
                        'generator':Generator(),'judge':Judge(),'frozen_plan':FROZEN_PLAN,'frozen_selection':['sister']})
                row.update(test_id=id,plan_and_selection_source='PR44 successful synthetic plan/selection reused; no new prediction',prior_commit=PRIOR_COMMIT)
                rows.append(row)
                if row['http_status']!=200 or not row['observations']['reviews'] or row['semantic_review'].get('status')!='accepted':break
            else:
                text='僕は30歳の医師だよ。';history=[{'role':'user','content':'いくつで、何の仕事をしているの？'}]
                evidence=evidence_bundle(history,[],None,None)+[{'id':'reply_policy','kind':'reply_policy','data':{'reply_locale':'ja-JP'}}]
                class CanonJudge:
                    async def review(self,reply,history,evidence):return await budget.call(id,'review',lambda:judge.review(reply,history,evidence))
                outcome=asyncio.run(review_reply(CanonJudge(),text,history,evidence,timeout=settings.semantic_review_timeout_seconds))
                result=outcome.result.model_dump() if outcome.result else None
                matched=bool(result and result['decision']=='revise' and all(s['verdict']=='contradicted' for s in result['segments'])
                    and {'C01','C02'}<=set(e for s in result['segments'] for e in s['evidence_ids']))
                rows.append({'test_id':id,'candidate':text,'review_status':outcome.status,'failure':outcome.failure,
                    'review':result,'authored_reference_match':matched,'reference':'contradicted; C01 age28 and C02 bookstore owner; not unsupported without citations'})
                if outcome.status not in ('accept','revise'):break
    return {'mode':'bounded_current_policy_reply_tail','model':settings.selected_model,'max_calls':budget.cap,'attempted_calls':len(budget.calls),
        'calls':budget.calls,'blocked':budget.blocked,'results':rows,'unattempted_ids':list(ids[len(rows):]),
        'memory_budget':{'plan_seconds':settings.memory_understanding_timeout_seconds,'selection_seconds':settings.memory_selection_timeout_seconds},
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ('app/fact_presentation.py','app/memory_understanding.py',
            'app/japanese_memory_layers.py','app/main.py','app/reply_pipeline.py','evaluations/current_policy/bilingual_memory_acceptance_v1.json','scripts/retest_bilingual_acceptance.py')},
        'assessment':'not_assessed','limits':'Real chat API with replayed prior successful plan/selection, actual generation/review only; no retry or live rewrite. Unfamiliar replies are unrated. Canon match uses author-exposed exact fixture, not independent semantic gold. No native ratings or M5 acceptance.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    parser.add_argument('--case',choices=CASES);args=parser.parse_args()
    if not args.live:parser.error('--live required; at most 3 calls; no retry')
    from dotenv import dotenv_values
    values=dotenv_values(ROOT/'.env');key=os.environ.get('GEMINI_API_KEY') or values.get('GEMINI_API_KEY','')
    if not key:parser.error('local key required, omitted')
    kwargs={n:os.environ.get(n.upper()) or values.get(n.upper()) or Settings.model_fields[n].default for n in
            ('gemini_model','memory_understanding_timeout_seconds','memory_selection_timeout_seconds')}
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=key,dialogue_mode='companion',growth_enabled=True,
        reply_understanding_mode='semantic',memory_understanding_mode='semantic',weather_understanding_mode='semantic',emotion_understanding_mode='semantic',**kwargs)
    try:report=run(settings,(args.case,) if args.case else CASES)
    except Exception:
        print('Synthetic run incomplete; private exception/configuration omitted.',file=sys.stderr);return 2
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if key in encoded:raise SystemExit('Sensitive output blocked')
    print(encoded)
    # Successful transport/author reference does not confer semantic acceptance.
    return int(bool(report['unattempted_ids']) or bool(report['blocked']) or any(
        (r.get('http_status')!=200 if r['test_id']=='ja-subject-tail' else not r['authored_reference_match']) for r in report['results']))


if __name__=='__main__':raise SystemExit(main())

"""Five-call maximum: fixed prior memory/canon failures; no generation or retries."""
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.config import ROOT, Settings
from app.memory import MemoryStore
from app.memory_understanding import ModelMemoryUnderstanding, MemoryMetadata, MemoryCallBudget, MemoryPlan, Understanding, understand, select_evidence
from app.fact_presentation import FactAnalysisProvider
from app.semantic_review import evidence_bundle, review_reply
from scripts.retest_same_language_memory import Ledger

MAX_CALLS=5
CASES=(
    {'id':'ja-memory-subject','locale':'ja-JP','query':'妹の面接先、覚えてる？',
     'candidate':'妹さんは合成葵社を受けたんだね。','expected':'revise','live_retrieval':True,
     'documents':[('own','私は合成葵社の面接を受けました。'),('sister','妹は合成桔梗社の面接を受けました。')],
     'reference_ids':['sister'],'origin':'memory_layers_v1:subject-sister/wrong-known-accept'},
    {'id':'ja-canon-conflict','locale':'ja-JP','query':'いくつで、何の仕事をしているの？',
     'candidate':'僕は30歳の医師だよ。','expected':'revise','live_retrieval':False,'documents':[],
     'reference_ids':[],'origin':'historical multilingual_facts:legacy Japanese false negative'},
    {'id':'zh-review-503','locale':'zh-CN','query':'妹妹面试的公司还记得吗？',
     'candidate':'记得啊，合成桔梗社的面试。她后来情况怎么样，还顺利吗？','expected':'accept',
     'live_retrieval':False,'documents':[('sister','妹妹参加了合成桔梗社的面试。')],
     'reference_ids':['sister'],'origin':'PR41 Gemini review upstream_unavailable(503); prior successful selection frozen'},
)


class FocusLedger(Ledger):
    def __init__(self, limit=MAX_CALLS):
        super().__init__()
        if not 1<=limit<=MAX_CALLS:raise ValueError('invalid call limit')
        self.limit=limit

    async def call(self,case,stage,operation):
        if len(self.calls)>=self.limit:raise ValueError('call_budget')
        return await super().call(case,stage,operation)


async def run(settings, case_ids=None, *, selection_only=False):
    ids=tuple(case_ids) if case_ids is not None else tuple(c['id'] for c in CASES)
    by_id={c['id']:c for c in CASES}
    if not ids or len(set(ids))!=len(ids) or not set(ids)<=set(by_id):raise ValueError('fixed cases only')
    if selection_only and ids!=('ja-memory-subject',):raise ValueError('selection-only requires fixed Japanese subject case')
    cases=[by_id[id] for id in ids]
    limit=1 if selection_only else sum(3 if c['live_retrieval'] else 1 for c in cases)
    ledger=FocusLedger(limit);rows=[]
    with tempfile.TemporaryDirectory(prefix='memory-canon-smoke-') as temp:
        store=MemoryStore('sqlite:///'+str(Path(temp)/'synthetic.sqlite3'))
        try:
            for case in cases:
                started=time.monotonic();cid=case['id'];row={k:case[k] for k in ('id','locale','query','candidate','expected','origin')}
                row.update(understanding_status='not_requested',candidate_ids=None,selected_ids=None,
                    selection_status='not_reached',review_status='not_reached',review_failure=None)
                rows.append(row);uid,_=store.identity(None);store.configure(uid,True,'Asia/Tokyo');aliases={};memories=[]
                for label,fact in case['documents']:
                    m=store.candidate(uid,fact,'synthetic',store.settings(uid)['epoch'],manual=True,metadata=MemoryMetadata('event','event'))
                    m=store.mutate(uid,m['id'],m['version'],confirm=True);aliases[m['id']]=label;memories.append(m)
                history=[{'role':'user','content':case['query']}]
                if case['live_retrieval']:
                    model=ModelMemoryUnderstanding(settings)
                    class Analyst:
                        async def analyze(self,data):return await ledger.call(cid,'plan',lambda:model.analyze(data))
                        async def select(self,data):return await ledger.call(cid,'selection',lambda:model.select(data))
                    budget=MemoryCallBudget.start(settings)
                    if selection_only:
                        # Frozen successful synthetic plan from the v5 2026-11-17 run, not a fresh prediction.
                        result=Understanding('ready',MemoryPlan.model_validate({'memory_use':'allow','need_memory':True,
                            'query':'妹 面接','target_slots':['history','other'],'reason':'personal_history_needed',
                            'confidence':.9,'candidates':[]}))
                        row['plan_source']='reused_successful_synthetic_plan_2026_11_17'
                    else:
                        result=await understand(Analyst(),case['query'],history,enabled=True,tz='Asia/Tokyo',timeout=budget.plan_seconds)
                    row['understanding_status']='prior_plan_reused' if selection_only else result.status
                    if result.status!='ready' or result.plan is None:
                        row.update(status='understanding_failed',elapsed_seconds=round(time.monotonic()-started,3));break
                    row['plan']=result.plan.model_dump();selected=[]
                    if result.plan.need_memory:
                        candidates=store.semantic_candidates(uid,result.plan.query,target_slots=result.plan.target_slots)
                        row['candidate_ids']=[aliases[m['id']] for m in candidates]
                        selected,status=await select_evidence(Analyst(),result.plan.query,history,candidates,timeout=budget.selection_timeout())
                        row['selection_status']=status
                        if status in ('unavailable','uncertain'):
                            row.update(status='selection_failed',elapsed_seconds=round(time.monotonic()-started,3));break
                    else:row['candidate_ids']=None;row['selection_status']='not_requested'
                    memories=selected
                    row['selected_ids']=[aliases[m['id']] for m in memories]
                    row['selection_reference_match']=set(row['selected_ids'])==set(case['reference_ids'])
                else:
                    row['selection_status']='prior_selection_reused' if memories else 'not_applicable'
                    row['selected_ids']=[aliases[m['id']] for m in memories]
                projected=[{'id':aliases[m['id']],'fact':m['fact'],'event_date':m['event_date']} for m in memories]
                row['injected_memories']=projected
                if selection_only:
                    row.update(status='selection_completed',elapsed_seconds=round(time.monotonic()-started,3))
                    continue
                evidence=evidence_bundle(history,projected,None,None)
                evidence.append({'id':'reply_policy','kind':'reply_policy','data':{'reply_locale':case['locale']}})
                outcome=await ledger.call(cid,'review',lambda:review_reply(FactAnalysisProvider(settings),case['candidate'],history,evidence,
                    timeout=settings.semantic_review_timeout_seconds))
                row.update(review_status=outcome.status,review_failure=outcome.failure,
                    review=outcome.result.model_dump() if outcome.result else None,
                    status='completed' if outcome.status in ('accept','revise') else 'review_failed',
                    elapsed_seconds=round(time.monotonic()-started,3))
                if row['status']!='completed':break
        finally:store.engine.dispose()
    return {'mode':'selection-only-prior-failure' if selection_only else 'memory-canon-prior-failures','model':settings.selected_model,'max_calls':limit,
        'memory_budget':{'plan_seconds':settings.memory_understanding_timeout_seconds,
            'selection_seconds':settings.memory_selection_timeout_seconds,
            'total_seconds':settings.memory_understanding_timeout_seconds+settings.memory_selection_timeout_seconds},
        'calls':ledger.calls,'attempted_calls':len(ledger.calls),'results':rows,
        'unattempted_ids':[c['id'] for c in cases[len(rows):]],'assessment':'not_assessed',
        'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
            'app/memory_understanding.py','app/fact_presentation.py','characters/shen_yan.json','scripts/retest_memory_canon.py')},
        'limits':('Frozen successful synthetic plan reused; actual candidates/selection only, no new query prediction or review. ' if selection_only else 'Japanese subject uses actual query/candidates/selection; Chinese reuses prior successful selection. Reviews use old candidate replies. ')+'Only fixed prior failures, no generation, rewrite or retry. Not full chat E2E or independent native quality.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    parser.add_argument('--case',choices=[c['id'] for c in CASES],help='One fixed failed case; no repeated stages from other cases')
    parser.add_argument('--selection-only',action='store_true',help='One selection call with the fixed previously successful Japanese plan; no plan/review retry')
    args=parser.parse_args()
    if not args.live:parser.error('--live required: maximum five calls, no retries')
    if args.selection_only and args.case not in (None,'ja-memory-subject'):parser.error('selection-only requires ja-memory-subject')
    from dotenv import dotenv_values
    config=dotenv_values(ROOT/'.env');key=os.environ.get('GEMINI_API_KEY') or config.get('GEMINI_API_KEY','')
    if not key:parser.error('local Gemini key required; omitted')
    kwargs={name:os.environ.get(name.upper()) or config.get(name.upper()) or Settings.model_fields[name].default
            for name in ('gemini_model','memory_understanding_timeout_seconds','memory_selection_timeout_seconds')}
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=key,dialogue_mode='companion',growth_enabled=True,
        memory_understanding_mode='semantic',reply_understanding_mode='semantic',weather_understanding_mode='semantic',emotion_understanding_mode='semantic',**kwargs)
    try:report=asyncio.run(run(settings,('ja-memory-subject',) if args.selection_only else (args.case,) if args.case else None,
                               selection_only=args.selection_only))
    except Exception:
        print('Synthetic retest incomplete; private configuration/exception omitted.',file=sys.stderr);return 2
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if key in encoded:raise SystemExit('Sensitive output blocked')
    print(encoded)
    if args.selection_only:
        return int(bool(report['unattempted_ids']) or any(r.get('selection_reference_match') is not True for r in report['results']))
    return int(bool(report['unattempted_ids']) or any(r.get('review_status')!=r['expected'] or
        r.get('selection_reference_match') is False for r in report['results']))


if __name__=='__main__':raise SystemExit(main())

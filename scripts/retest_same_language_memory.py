"""Bounded Gemini smoke for two previously failed synthetic memory categories only."""
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

from app.config import Settings, ROOT
from app.memory import MemoryStore
from app.memory_understanding import ModelMemoryUnderstanding, MemoryMetadata, understand, select_evidence, MemoryCallBudget, memory_reply_context
from app.japanese_memory_layers import load, SAME_LANGUAGE_DATASET
from app.dialogue import build_provider
from app.companion import instructions
from app.fact_presentation import FactAnalysisProvider, ANSWER_PROMPT, memory_context
from app.localization import language_prompt
from app.semantic_review import evidence_bundle, review_reply

CASE_IDS=('ja-no-answer','zh-subject-sister')
MAX_CALLS=8


class Ledger:
    def __init__(self):self.calls=[]
    async def call(self,case,stage,operation):
        if len(self.calls)>=MAX_CALLS or sum(x['case']==case for x in self.calls)>=4:raise ValueError('call_budget')
        row={'case':case,'stage':stage,'status':'started'};self.calls.append(row)
        start=time.monotonic()
        try:
            result=await operation();row['status']='returned';return result
        except BaseException as error:
            row['status']='failed'
            row['failure'] = ('timeout_or_cancelled' if isinstance(error,(TimeoutError,asyncio.CancelledError))
                or type(error).__name__=='APITimeoutError' else
                {401:'authentication_failed',403:'permission_denied',429:'rate_limit',503:'upstream_unavailable'}.get(
                    getattr(error,'status_code',None),'provider_error'))
            raise
        finally:row['elapsed_seconds']=round(time.monotonic()-start,3)


async def run(settings, case_ids=CASE_IDS):
    """Settings are injected; never use a supplied player DB or import the web app."""
    ledger=Ledger();rows=[]
    if not case_ids or len(set(case_ids))!=len(case_ids) or not set(case_ids)<=set(CASE_IDS):raise ValueError('fixed cases only')
    data={c.id:c for c in load(SAME_LANGUAGE_DATASET).cases}
    with tempfile.TemporaryDirectory(prefix='same-memory-live-') as temp:
        store=MemoryStore('sqlite:///'+str(Path(temp)/'synthetic.sqlite3'))
        try:
            for cid in case_ids:
                case=data[cid];start=time.monotonic();row={'case':cid,'locale':case.locale,'input':case.message,'status':'started'};rows.append(row)
                uid,_=store.identity(None);store.configure(uid,True,'Asia/Tokyo');aliases={}
                for d in case.documents:
                    epoch=store.settings(uid)['epoch']
                    m=store.candidate(uid,d.fact,'synthetic',epoch,manual=True,metadata=MemoryMetadata('event',d.slot,d.event_date))
                    m=store.mutate(uid,m['id'],m['version'],confirm=True)
                    aliases[m['id']]=d.id
                history=[{'role':'user','content':case.message}]
                model=ModelMemoryUnderstanding(settings)
                class Analyst:
                    async def analyze(self,data):return await ledger.call(cid,'plan',lambda:model.analyze(data))
                    async def select(self,data):return await ledger.call(cid,'selection',lambda:model.select(data))
                budget=MemoryCallBudget.start(settings)
                result=await understand(Analyst(),case.message,history,enabled=True,tz='Asia/Tokyo',timeout=budget.plan_seconds)
                row['understanding_status']=result.status
                if result.status!='ready' or result.plan is None:
                    row['status']='understanding_failed';row['elapsed_seconds']=round(time.monotonic()-start,3);break
                row['plan']=result.plan.model_dump();selected=[]
                if result.plan.need_memory:
                    candidates=store.semantic_candidates(uid,result.plan.query,target_slots=result.plan.target_slots)
                    row['candidate_ids']=[aliases[m['id']] for m in candidates]
                    row['selection_timeout_seconds']=round(budget.selection_timeout(),3)
                    selected,status=await select_evidence(Analyst(),result.plan.query,history,candidates,timeout=budget.selection_timeout())
                    row['selection_status']=status
                    if status in ('unavailable','uncertain'):
                        row['status']='selection_failed';row['elapsed_seconds']=round(time.monotonic()-start,3);break
                else:row['candidate_ids']=None;row['selection_status']='not_requested'
                row['selected_ids']=[aliases[m['id']] for m in selected]
                row['reference_selection_match']=set(row['selected_ids'])==set(case.relevant)
                # Use aliases in the prompt/report, keeping runtime identifiers out of the export.
                memories=[{**m,'id':aliases[m['id']]} for m in selected]
                row['injected_memories']=[{k:m[k] for k in ('id','fact','event_date')} for m in memories]
                prompt=instructions()+memory_context(memories)+ANSWER_PROMPT+memory_reply_context(memories,requested=result.plan.need_memory)+language_prompt(case.locale)
                try:
                    reply=await ledger.call(cid,'generation',lambda:build_provider(settings).generate(history,prompt))
                    row['raw_reply']=reply
                    evidence=evidence_bundle(history,memories,None,None)
                    evidence.append({'id':'reply_policy','kind':'reply_policy','data':{'reply_locale':case.locale}})
                    outcome=await ledger.call(cid,'review',lambda:review_reply(FactAnalysisProvider(settings),reply,history,evidence,timeout=settings.semantic_review_timeout_seconds))
                    row['review_status']=outcome.status;row['review_failure']=outcome.failure
                    row['review']=outcome.result.model_dump() if outcome.result else None
                    row['status']='completed' if outcome.status in ('accept','revise') else 'review_failed'
                except Exception:
                    row['status']='generation_or_review_failed'  # Never print provider exception/config.
                row['elapsed_seconds']=round(time.monotonic()-start,3)
                if row['status']!='completed':break
        finally:store.engine.dispose()
    return {'mode':'bounded_same_language_gemini_smoke','model':settings.selected_model,'max_calls':min(MAX_CALLS,4*len(case_ids)),
        'memory_budget':{'plan_seconds':settings.memory_understanding_timeout_seconds,'selection_seconds':settings.memory_selection_timeout_seconds,
            'total_seconds':settings.memory_understanding_timeout_seconds+settings.memory_selection_timeout_seconds},
        'calls':ledger.calls,'attempted_calls':len(ledger.calls),'max_cases':len(case_ids),'attempted_cases':len(rows),'results':rows,
        'dataset_sha256':hashlib.sha256(SAME_LANGUAGE_DATASET.read_bytes()).hexdigest(),
        'prompt_sha256':hashlib.sha256((ROOT/'app/memory_understanding.py').read_bytes()).hexdigest(),
        'assessment':'not_assessed','limits':'Two public authored failure categories, one attempt each; no rewrite/retry, stop after unavailable/error. Reference IDs and model review are not independent semantic gold. No web app, actual player database or native ratings.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--live',action='store_true')
    parser.add_argument('--case',choices=CASE_IDS,help='One fixed synthetic case, once; no arbitrary input')
    args=parser.parse_args()
    if not args.live:parser.error('--live required; at most 8 calls / 2 synthetic cases')
    from dotenv import dotenv_values
    config=dotenv_values(ROOT/'.env')
    key=os.environ.get('GEMINI_API_KEY') or config.get('GEMINI_API_KEY','')
    if not key:parser.error('local Gemini key required; omitted from output')
    settings=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=key,
        gemini_model=os.environ.get('GEMINI_MODEL') or config.get('GEMINI_MODEL') or Settings.model_fields['gemini_model'].default,
        memory_understanding_timeout_seconds=os.environ.get('MEMORY_UNDERSTANDING_TIMEOUT_SECONDS') or config.get('MEMORY_UNDERSTANDING_TIMEOUT_SECONDS') or Settings.model_fields['memory_understanding_timeout_seconds'].default,
        memory_selection_timeout_seconds=os.environ.get('MEMORY_SELECTION_TIMEOUT_SECONDS') or config.get('MEMORY_SELECTION_TIMEOUT_SECONDS') or Settings.model_fields['memory_selection_timeout_seconds'].default,
        dialogue_mode='companion',growth_enabled=True,memory_understanding_mode='semantic',reply_understanding_mode='semantic',
        weather_understanding_mode='semantic',emotion_understanding_mode='semantic')
    try:report=asyncio.run(run(settings,(args.case,) if args.case else CASE_IDS))
    except Exception:
        print('Synthetic smoke incomplete; configuration and raw exception omitted.',file=sys.stderr);return 2
    encoded=json.dumps(report,ensure_ascii=False,indent=2)
    if key in encoded:raise SystemExit('Sensitive output blocked')
    print(encoded)
    return int(any(r['status']!='completed' or not r.get('reference_selection_match') or r.get('review_status')!='accept' for r in report['results']))


if __name__=='__main__':raise SystemExit(main())

"""Explicit, bounded live auxiliary smoke; fixed synthetic inputs, no database."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.fact_support_evaluation import load_dataset
from app.memory_routing import route_memory
from app.semantic_review import ModelAnalysisProvider,evidence_bundle,review_reply

IDS=('scene-stock-completed','place-english-changed','paraphrase-place-inference',
     'scene-conditional-expanded','place-correction-quote','source-current-paraphrase')


async def run(interval=12):
    from app.config import Settings
    settings=Settings()
    if settings.chat_provider=='mock' or not settings.configured:raise ValueError('configured real provider required')
    auxiliary=ModelAnalysisProvider(settings)
    data,digest=load_dataset();by_id={e.id:e for e in data.evidence};rows=[]
    for id in IDS:
        case=next(c for c in data.cases if c.id==id)
        memories=[{'id':e.id,'fact':e.text,'event_date':e.event_date} for e in data.evidence if e.id in case.evidence_ids and e.kind=='memory']
        history=[{'role':'user','content':case.query}]
        bundle=evidence_bundle(history,memories,None,None)
        if rows:await asyncio.sleep(interval)
        print('judge_attempt '+id,file=sys.stderr,flush=True)
        outcome=await review_reply(auxiliary,case.reply,history,bundle,timeout=settings.semantic_review_timeout_seconds)
        status,result=outcome
        expected='revise' if any(c.verdict in ('unsupported','contradicted') or c.form_violation for c in case.claims) else 'accept'
        rows.append({'id':id,'candidate':case.reply,'status':status,'expected':expected,
                     'match':status==expected,'failure':outcome.failure,'review':result.model_dump() if result else None})
    await asyncio.sleep(interval)
    query='你觉得什么适合我？'
    print('router_attempt',file=sys.stderr,flush=True)
    route=await route_memory(query,[{'role':'user','content':query}],enabled=True,
                             router=auxiliary,timeout=settings.memory_route_timeout_seconds)
    return {'model':settings.selected_model,'dataset_sha256':digest,'judge_attempts':6,'router_attempts':1,
            'router':route.public(),'results':rows,'matched':sum(r['match'] for r in rows),
            'limits':'Six selected development probes plus one router smoke, not independent quality or hallucination rate; no generation or database; no retries.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Explicitly permit seven real auxiliary calls using local credentials')
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才会读取本地配置并调用模型')
    try:report=asyncio.run(run())
    except KeyboardInterrupt:
        print('合成冒烟已中止，未生成完整结果。',file=sys.stderr);raise SystemExit(130)
    except Exception:
        print('合成冒烟未完成，不显示原始配置或异常。',file=sys.stderr);raise SystemExit(2)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(int(any(r['status'] in ('unavailable','uncertain') for r in report['results'])))

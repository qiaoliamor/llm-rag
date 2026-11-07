"""One real judge call for the previously missed shop-owner voice example."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle,review_reply
from scripts.retest_scene_roleplay import QUERY,OLD


async def retest(settings):
    history=[{'role':'user','content':QUERY}]
    print('attempt 1/1 old_shop_voice_review',file=sys.stderr,flush=True)
    start=time.perf_counter()
    outcome=await review_reply(ModelAnalysisProvider(settings),OLD,history,evidence_bundle(history,[],None,None),timeout=8)
    return {'model':settings.selected_model,'attempts':1,'max_attempts':1,'query':QUERY,'candidate':OLD,
        'expected':'revise, role_issues=[0]','status':outcome.status,'failure':outcome.failure,
        'elapsed_seconds':round(time.perf_counter()-start,3),
        'review':outcome.result.model_dump() if outcome.result else None,
        'review_prompt_sha256':hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest(),
        'limits':'One previously failed synthetic reply judged once; no generation, database or retries. Prompt includes a targeted example, not independent generalization evaluation.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才读取本地配置；仅旧漏检案例，最多1次审查')
    from app.config import Settings
    settings=Settings(semantic_review_timeout_seconds=8)
    if settings.chat_provider!='gemini' or not settings.configured:parser.error('需要本地Gemini配置')
    try:report=asyncio.run(retest(settings))
    except Exception:
        print('复测未完成，不显示配置或原始异常。',file=sys.stderr);return 2
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(report['status']!='revise' or not report['review'] or report['review']['role_issues']!=[0])


if __name__=='__main__':raise SystemExit(main())

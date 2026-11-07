"""One judge call for the last failed conditional-atmosphere development case."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.fact_support_evaluation import load_dataset
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle,review_reply
from app.dialogue import SCENE_PROFILE

CASE_ID='scene-conditional-expanded'


async def retest(settings):
    data,digest=load_dataset()
    case=next(c for c in data.cases if c.id==CASE_ID)
    history=[{'role':'user','content':case.query}]
    print('attempt 1/1 previously_failed_conditional_review',file=sys.stderr,flush=True)
    start=time.perf_counter()
    outcome=await review_reply(ModelAnalysisProvider(settings),case.reply,history,evidence_bundle(history,[],None,None),timeout=8)
    return {'model':settings.selected_model,'attempts':1,'max_attempts':1,'case_id':CASE_ID,
        'query':case.query,'candidate':case.reply,'expected':'accept, role_issues=[]',
        'status':outcome.status,'failure':outcome.failure,'elapsed_seconds':round(time.perf_counter()-start,3),
        'review':outcome.result.model_dump() if outcome.result else None,
        'dataset_sha256':digest,'scene_version':SCENE_PROFILE['version'],
        'review_prompt_sha256':hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest(),
        'limits':'One synthetic development conditional previously overblocked/timed out. No generation, database, retries, or re-scoring the already approved natural reply. Not independent quality evaluation.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才读取配置；仅旧失败条件句，最多1次')
    from app.config import Settings
    settings=Settings(semantic_review_timeout_seconds=8)
    if settings.chat_provider!='gemini' or not settings.configured:parser.error('需要本地Gemini配置')
    try:report=asyncio.run(retest(settings))
    except Exception:
        print('复测未完成，不显示本地配置或异常。',file=sys.stderr);return 2
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(report['status']!='accept' or not report['review'] or report['review']['role_issues']!=[])


if __name__=='__main__':raise SystemExit(main())

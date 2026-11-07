"""Offline cross-file candidate and authored reference audit; one old-failure live probe optional."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.reference_audit import evaluate_audit, load_audit
from app.narrative_calibration import score
from app.semantic_review import ModelAnalysisProvider, INDEXED_PROMPT, review_reply

LIVE_ID='place-english-changed'


async def retest(provider,data):
    case=next(c for c in data.cases if c.id==LIVE_ID)
    history,evidence=case.context()
    print('attempt 1/1 prior_failed_english_place_review',file=sys.stderr,flush=True)
    start=time.perf_counter()
    outcome=await review_reply(provider,case.reply,history,evidence,timeout=8)
    return {**score(case,outcome),'elapsed_seconds':round(time.perf_counter()-start,3),
            'review':outcome.result.model_dump() if outcome.result else None}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    try:
        report=evaluate_audit()
        report['review_prompt_sha256']=hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest()
        report['max_live_calls']=int(args.live)
        if args.live:
            from app.config import Settings
            settings=Settings(semantic_review_timeout_seconds=8)
            if settings.chat_provider!='gemini' or not settings.configured:
                parser.error('需要本地Gemini配置，不显示密钥')
            data,_,_=load_audit()
            row=asyncio.run(retest(ModelAnalysisProvider(settings),data))
            report.update(api_calls=1,model=settings.selected_model,live_result=row)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return int(args.live and not (row['axes_match'] and row['decision_match']))
    except Exception:
        print('复核未完成，不显示本地配置或异常原文。',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())

"""Four-call synthetic retest of two previously failed cases; no database."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.dialogue import GeminiProvider,ProviderFailure,instructions
from app.grounding import grounding_prompt
from app.memory_routing import NO_MEMORY_CONTEXT
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle,review_reply

CASES=(
    {'id':'no-message-claim','query':'你店里今天安静吗？',
     'candidate':'店里具体的情况我没办法确定，也没收到什么新的消息。'},
    {'id':'arrival-presupposition','query':'你好，简单介绍一下你自己吧。',
     'candidate':'你今天过来，是想找本什么书，还是随便转转？'},
)


async def retest(settings,*,interval=10):
    rows=[];attempts=0
    for case in CASES:
        history=[{'role':'user','content':case['query']}]
        if attempts:await asyncio.sleep(interval)
        attempts+=1
        print(f'attempt {attempts}/4 {case["id"]} judge',file=sys.stderr,flush=True)
        started=time.perf_counter()
        outcome=await review_reply(ModelAnalysisProvider(settings),case['candidate'],history,
                                   evidence_bundle(history,[],None,None),timeout=8)
        judged={'status':outcome.status,'failure':outcome.failure,
                'elapsed_seconds':round(time.perf_counter()-started,3),
                'review':outcome.result.model_dump() if outcome.result else None}
        await asyncio.sleep(interval)
        attempts+=1
        print(f'attempt {attempts}/4 {case["id"]} generation',file=sys.stderr,flush=True)
        prompt=instructions()+grounding_prompt([],case['query'])+NO_MEMORY_CONTEXT
        started=time.perf_counter()
        try:
            reply=await GeminiProvider(settings).generate(history,prompt)
            generated={'status':'completed','reply':reply}
        except ProviderFailure as error:generated={'status':'failed','failure':error.code}
        except Exception:generated={'status':'failed','failure':'provider_error'}
        generated['elapsed_seconds']=round(time.perf_counter()-started,3)
        rows.append({**case,'expected_judge':'revise','judged':judged,'generated':generated})
    return {'model':settings.selected_model,'attempts':attempts,'max_attempts':4,
        'review_prompt_sha256':hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest(),
        'generation_prompt_sha256':hashlib.sha256(instructions().encode()).hexdigest(),
        'results':rows,'limits':'Two previously failed synthetic cases, each judged and generated once, no retries/database. No extra model judging of new generations; generation completion does not certify factual support. Historical results are the baseline, not resampled.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才读取本地配置；最多4次，失败不重试')
    from app.config import Settings
    settings=Settings(semantic_review_timeout_seconds=8)
    if settings.chat_provider!='gemini' or not settings.configured:parser.error('需要本地Gemini配置')
    try:report=asyncio.run(retest(settings))
    except Exception:
        print('复测未完成，不显示本地配置或异常原文。',file=sys.stderr);return 2
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(any(r['judged']['status']!='revise' or r['generated']['status']!='completed' for r in report['results']))


if __name__=='__main__':raise SystemExit(main())

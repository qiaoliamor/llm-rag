"""At most three live calls around a previously failed shop-chat example."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.dialogue import GeminiProvider,ProviderFailure,SCENE_PROFILE,instructions
from app.grounding import grounding_prompt
from app.memory_routing import NO_MEMORY_CONTEXT
from app.semantic_review import ModelAnalysisProvider,INDEXED_PROMPT,evidence_bundle,review_reply

QUERY='你店里今天安静吗？'
OLD='具体近况我还不能确定，不过窗外这会儿倒是挺安静的。你今天想聊点什么，或者有什么想读的书吗？'


async def retest(settings,*,interval=10):
    history=[{'role':'user','content':QUERY}]
    evidence=evidence_bundle(history,[],None,None)
    report={'query':QUERY,'old_reply':OLD,'max_attempts':3,'attempts':0}
    async def judge(text,label):
        report['attempts']+=1
        print(f'attempt {report["attempts"]}/3 {label}',file=sys.stderr,flush=True)
        start=time.perf_counter()
        result=await review_reply(ModelAnalysisProvider(settings),text,history,evidence,timeout=8)
        return {'status':result.status,'failure':result.failure,'elapsed_seconds':round(time.perf_counter()-start,3),
                'review':result.result.model_dump() if result.result else None}
    report['old_review']=await judge(OLD,'old_reply_review')
    await asyncio.sleep(interval)
    report['attempts']+=1
    print(f'attempt {report["attempts"]}/3 generation',file=sys.stderr,flush=True)
    start=time.perf_counter()
    try:
        reply=await GeminiProvider(settings).generate(history,instructions()+grounding_prompt([],QUERY)+NO_MEMORY_CONTEXT)
        report['generation']={'status':'completed','reply':reply,'elapsed_seconds':round(time.perf_counter()-start,3)}
    except ProviderFailure as error:report['generation']={'status':'failed','failure':error.code}
    except Exception:report['generation']={'status':'failed','failure':'provider_error'}
    if report['generation']['status']=='completed':
        await asyncio.sleep(interval)
        report['new_review']=await judge(reply,'new_reply_review')
    return {'model':settings.selected_model,**report,
        'review_prompt_sha256':hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest(),
        'generation_prompt_sha256':hashlib.sha256(instructions().encode()).hexdigest(),
        'scene_profile_sha256':hashlib.sha256(json.dumps(SCENE_PROFILE,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        'limits':'One prior failed synthetic shop-chat example; no retries or database. Fiction atmosphere is licensed, not measured reality. Old strict-scene labels are not a quality baseline for this policy. No independent generalization score.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才读取配置；仅旧店况失败案例，最多3次')
    from app.config import Settings
    settings=Settings(semantic_review_timeout_seconds=8)
    if settings.chat_provider!='gemini' or not settings.configured:parser.error('需要本地Gemini配置')
    try:report=asyncio.run(retest(settings))
    except Exception:
        print('复测未完成，不显示本地配置或原始异常。',file=sys.stderr);return 2
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(report['old_review']['status']!='revise' or report.get('new_review',{}).get('status')!='accept')


if __name__=='__main__':raise SystemExit(main())

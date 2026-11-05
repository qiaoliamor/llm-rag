"""Two explicit synthetic /v1/chat probes, isolated DB, at most eight calls."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import time
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    args=parser.parse_args()
    if not args.live:parser.error('显式--live才会调用Gemini，仅固定合成问题')
    from app.config import Settings
    from app.dialogue import GeminiProvider
    from app.semantic_review import ModelAnalysisProvider
    from fastapi.testclient import TestClient
    base=Settings()
    if base.chat_provider!='gemini' or not base.configured:parser.error('需要本地Gemini配置')
    class Generation(GeminiProvider):
        calls=0
        async def generate(self,*args):
            self.calls+=1
            return await super().generate(*args)
    class Judge(ModelAnalysisProvider):
        calls=0
        async def review(self,*args):
            self.calls+=1
            return await super().review(*args)
    previous=os.environ.get('MEMORY_DATABASE_URL')
    try:
        with tempfile.TemporaryDirectory(prefix='semantic-chat-') as directory:
            url='sqlite:///'+str(Path(directory)/'synthetic.sqlite3')
            # app.main creates its default app at import. Isolate BEFORE import.
            os.environ['MEMORY_DATABASE_URL']=url
            from app.main import create_app
            config=Settings(_env_file=None,chat_provider='gemini',gemini_api_key=base.gemini_api_key,
                gemini_model=base.gemini_model,memory_database_url=url,
                semantic_review_enabled=True,semantic_review_timeout_seconds=8)
            provider=Generation(config);judge=Judge(config);rows=[]
            with TestClient(create_app(config,provider,semantic_judge=judge)) as client:
                for query in ('你好，简单介绍一下你自己吧。','你店里今天安静吗？'):
                    if rows:time.sleep(10)
                    client.cookies.clear()
                    headers={'x-csrf-token':client.get('/v1/session').json()['csrf_token']}
                    g,j=provider.calls,judge.calls;start=time.perf_counter()
                    response=client.post('/v1/chat',headers=headers,json={'message':query})
                    body=response.json()
                    rows.append({'query':query,'http_status':response.status_code,
                        'elapsed_seconds':round(time.perf_counter()-start,3),
                        'generation_calls':provider.calls-g,'judge_calls':judge.calls-j,
                        'reply':body.get('reply'),'review':body.get('semantic_review'),
                        'error_code':body.get('code')})
            print(json.dumps({'model':config.selected_model,'results':rows,
                'generation_calls':provider.calls,'judge_calls':judge.calls,
                'limits':'Two synthetic isolated sessions, not independent quality evaluation; fallback is not a quality pass.'},ensure_ascii=False,indent=2))
            return int(any(r['http_status']!=200 or r['review'].get('status') not in ('accepted','revised','skipped') for r in rows))
    finally:
        if previous is None:os.environ.pop('MEMORY_DATABASE_URL',None)
        else:os.environ['MEMORY_DATABASE_URL']=previous


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print('合成会话冒烟未完成，不显示配置或原始异常。',file=sys.stderr);raise SystemExit(2)

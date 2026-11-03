"""M5 retrieval ablations. Offline by default; --live explicitly calls the selected API."""
import argparse
import asyncio
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.retrieval_evaluation import compare_prompts, evaluate_retrieval


async def run(args):
    report = evaluate_retrieval()
    if args.live:
        # Local configuration is loaded ONLY for an explicitly requested live run.
        from app.config import Settings
        from app.dialogue import build_provider
        try:
            settings = Settings()
        except ValueError:
            raise ValueError('本地模型配置无效，请检查 .env（不显示配置原文）') from None
        if settings.chat_provider == 'mock' or not settings.configured:
            raise ValueError('真实对照需要配置当前供应商的本地密钥，不能用mock代替')
        report['generation'] = await compare_prompts(build_provider(settings),limit=args.live_limit,
            repeats=args.repeats,max_calls=args.max_calls,include_replies=args.include_synthetic_replies)
        report['model_calls'] = report['generation']['api_calls']
        report['generation']['provider'] = settings.chat_provider
        report['generation']['model'] = settings.selected_model
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Use local API credentials; consumes quota and may incur charges')
    parser.add_argument('--live-limit',type=int,choices=range(1,4),default=3)
    parser.add_argument('--repeats',type=int,choices=range(1,4),default=2)
    parser.add_argument('--max-calls',type=int,choices=range(1,19),default=12)
    parser.add_argument('--include-synthetic-replies',action='store_true',help='Include replies to fixed synthetic probes only')
    args = parser.parse_args()
    if args.live_limit*args.repeats*2 > args.max_calls and args.live:
        parser.error('请求预算不足：需要 live-limit × repeats × 2 次，未发起请求')
    try:
        report = asyncio.run(run(args))
    except ValueError:
        print('评测配置或合成数据无效；请核对参数及本地模型配置。',file=sys.stderr)
        return 2
    except Exception:
        # Do not print SDK/configuration exceptions containing credentials or responses.
        print('评测执行失败；未生成完整结果，不显示原始错误或配置。',file=sys.stderr)
        return 1
    revision = subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,cwd=Path(__file__).resolve().parent.parent)
    state = subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,cwd=Path(__file__).resolve().parent.parent)
    report['code_revision'] = revision.stdout.strip() if revision.returncode==0 else None
    report['working_tree_dirty'] = bool(state.stdout.strip()) if state.returncode==0 else None
    print(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False))
    # Low quality is an experimental finding; provider errors are incomplete experiments.
    return 1 if report['generation'] and any(v['errors'] for v in report['generation']['summaries'].values()) else 0


if __name__ == '__main__':
    raise SystemExit(main())

"""Offline scoring for unfamiliar, saved synthetic Gemini replies; no API or .env."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.observed_reply_evaluation import OBSERVATIONS,evaluate,prepare
from scripts.score_annotations import write_report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations',type=Path,default=OBSERVATIONS)
    parser.add_argument('--reference',type=Path)
    parser.add_argument('--prepare',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--require-acceptance',action='store_true')
    args=parser.parse_args()
    if args.prepare and (args.reference or args.output):parser.error('prepare and scoring are separate')
    try:
        if args.prepare:report=prepare(args.observations,args.prepare)
        else:
            report=evaluate(args.observations,args.reference)
            if args.output:write_report(args.output,report)
        print(json.dumps(report,ensure_ascii=False,indent=2));return 3 if args.require_acceptance else 0
    except Exception:
        print('离线回复评测失败：检查原文指纹、完整命题、证据或外部输出路径；未显示原文/配置。',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())

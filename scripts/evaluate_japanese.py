"""Offline Japanese development recall and editorial blind-calibration preparation."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.japanese_evaluation import evaluate_recall, prepare, binding


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-annotation',type=Path)
    args=parser.parse_args()
    try:
        report=evaluate_recall()
        report['binding']=binding()
        if args.prepare_annotation:report['annotation']=prepare(args.prepare_annotation)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    except Exception:
        print('日语离线评测/准备失败；未显示原文、私有评分或配置。',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())

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
    parser.add_argument('--memory-layers',action='store_true',help='Replay four memory layers with scripted models in an isolated worker')
    parser.add_argument('--same-language-memory',action='store_true',help='Replay separate Chinese/Chinese and Japanese/Japanese development cases; no APIs')
    args=parser.parse_args()
    if sum(bool(x) for x in (args.memory_layers,args.same_language_memory,args.prepare_annotation))>1:parser.error('Layer replay and annotation preparation are separate commands')
    try:
        if args.memory_layers or args.same_language_memory:
            from app.japanese_memory_layers import evaluate, DATASET, SAME_LANGUAGE_DATASET
            print(json.dumps(evaluate(SAME_LANGUAGE_DATASET if args.same_language_memory else DATASET),ensure_ascii=False,indent=2))
            return 0
        report=evaluate_recall()
        report['binding']=binding()
        if args.prepare_annotation:report['annotation']=prepare(args.prepare_annotation)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        return 0
    except Exception:
        print('日语离线评测/准备失败；未显示原文、私有评分或配置。',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())

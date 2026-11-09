"""Offline two-submission import; zero API and no automatic formal acceptance."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.annotation_scoring import score_files
from app.sealed_evaluation import ROOT


def write_report(path,report):
    path=Path(path).resolve()
    if path.is_relative_to(ROOT):raise ValueError('report must stay outside repository')
    data=json.dumps(report,ensure_ascii=False,indent=2)+'\n'
    created=False
    try:
        with path.open('x',encoding='utf-8') as stream:
            created=True
            stream.write(data)
    except BaseException:
        if created:path.unlink(missing_ok=True)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping',type=Path,required=True)
    parser.add_argument('--rater-a',type=Path,required=True)
    parser.add_argument('--rater-b',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--require-acceptance',action='store_true')
    args=parser.parse_args()
    try:
        paths=[args.rater_a]+([args.rater_b] if args.rater_b else [])
        report=score_files(args.mapping,paths)
        write_report(args.output,report)
        print(json.dumps({'tasks':report['tasks'],'submissions':report['submissions'],
                          'disagreements':report['disagreement_count'],
                          'assessment':report['assessment']['status'],'model_calls':0},ensure_ascii=False))
        return 3 if args.require_acceptance and report['assessment']['status']!='met' else 0
    except Exception:
        print('标注导入/评分失败；请检查结构、覆盖、证据、冻结版本或输出路径。未显示原文、身份或配置。',file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())

"""Offline integrity/schema checks; optional synthetic label-blind annotation packet."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from app.sealed_evaluation import verify,prepare


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-content',action='store_true')
    parser.add_argument('--prepare-annotation',type=Path)
    args=parser.parse_args()
    try:
        manifest=verify(content=args.validate_content)
        result={'check':'integrity_and_schema' if args.validate_content else 'integrity_only',
                'bundle_version':manifest.version,'case_count':manifest.case_count,'status':manifest.status,'model_calls':0,
                'independent_annotation':manifest.independent_annotation,
                'blind_review':manifest.blind_review,'acceptance':manifest.acceptance}
        if args.prepare_annotation:result['packet']=prepare(args.prepare_annotation)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except Exception:
        print('封存校验/准备失败；不显示配置、数据或原始异常。',file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())

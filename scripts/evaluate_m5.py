"""Offline M5 component evaluation; prints aggregate/ID results, never loads .env."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.evaluation import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('dev', 'holdout', 'all'), default='dev')
    args = parser.parse_args()
    report = evaluate(args.split)
    # Only immutable revision metadata; never include environment or local config.
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parent.parent,
                            capture_output=True, text=True)
    report['code_revision'] = result.stdout.strip() if result.returncode == 0 else None
    diff = subprocess.run(['git', 'status', '--porcelain', '--untracked-files=normal'],
                          cwd=Path(__file__).resolve().parent.parent, capture_output=True, text=True)
    report['working_tree_dirty'] = bool(diff.stdout.strip()) if diff.returncode == 0 else None
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if report['passed'] == report['total'] else 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Offline manifest validation by default; --live permits only two frozen old failures."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.narrative_calibration import load_dataset, LIVE_IDS, score, summarize
from app.semantic_review import INDEXED_PROMPT, ModelAnalysisProvider, review_reply


async def evaluate(provider, data):
    rows = []
    for case in data.cases:
        if case.id not in LIVE_IDS:
            continue
        history, evidence = case.context()
        print(f'attempt {len(rows)+1}/2 {case.id}', file=sys.stderr, flush=True)
        start = time.perf_counter()
        outcome = await review_reply(provider, case.reply, history, evidence, timeout=8)
        row = score(case, outcome)
        row.update(elapsed_seconds=round(time.perf_counter()-start, 3),
                   review=outcome.result.model_dump() if outcome.result else None)
        rows.append(row)
        # Stop the batch on service failure; never retry or spend remaining budget.
        if outcome.status == 'unavailable':
            break
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    args = parser.parse_args()
    try:
        data, digest = load_dataset()
        report = {'dataset_version': data.version, 'dataset_sha256': digest,
                  'scene_sha256': data.scene_sha256, 'character_sha256': data.character_sha256,
                  'review_prompt_sha256': hashlib.sha256(INDEXED_PROMPT.encode()).hexdigest(),
                  'case_count': len(data.cases), 'max_calls': 2 if args.live else 0,
                  'mode': 'live_failed_cases' if args.live else 'manifest_validation_only'}
        if args.live:
            from app.config import Settings
            settings = Settings(semantic_review_timeout_seconds=8)
            if settings.chat_provider != 'gemini' or not settings.configured:
                parser.error('需要本地Gemini配置；不显示密钥')
            report['model'] = settings.selected_model
            rows = asyncio.run(evaluate(ModelAnalysisProvider(settings), data))
            report.update(results=rows, summary=summarize(rows))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return int(args.live and (len(rows) != len(LIVE_IDS) or not all(r['axes_match'] and r['decision_match'] for r in rows)))
    except Exception:
        print('评测未完成；不显示配置或原始异常。', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

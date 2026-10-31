"""Offline smoke by default. --live uses the configured API and consumes quota."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.config import ROOT, Settings
from app.dialogue import MockProvider, build_provider, instructions


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--live', action='store_true', help='Use configured API (quota/charges apply); otherwise mock only')
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()
    settings = Settings()
    if args.limit < 1:
        parser.error('--limit must be positive')
    if args.live and settings.chat_provider == 'mock':
        parser.error('--live requires CHAT_PROVIDER=gemini or openai')
    if args.live and not settings.configured:
        parser.error(f'Fill {settings.api_key_env} in local .env first')
    cases = json.loads((ROOT / 'tests/scenarios.json').read_text())[:args.limit]
    provider = build_provider(settings) if args.live else MockProvider()
    for mode in ('direct', 'rag', 'canon'):
        passed = 0
        for case in cases:
            reply = await provider.generate([{'role':'user', 'content':case['message']}], instructions(mode, case['message']))
            passed += case['expected_fragment'] in reply
        print(json.dumps({'mode':mode,'provider':settings.chat_provider if args.live else 'mock',
                          'cases':len(cases),'literal_smoke_passes':passed,
                          'note':'Literal assertions only; NOT a quality or RAG evaluation.'}, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())

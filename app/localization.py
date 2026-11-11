"""Per-request presentation language; no translation or migration of player facts."""
from .dialogue import MockProvider, FALLBACK
from .companion import FALLBACK as COMPANION_FALLBACK

JAPANESE_PROMPT = '''
応答言語：日本語。これ以降は自然な日本語で話す。これは言語指定であり、人物設定や事実の変更ではない。
沈砚（画面表記は沈硯）の年齢、職業、栖川の古書店や過去の設定を維持する。
落ち着いた親しみのある口調で、挨拶には短く返し、話したい気持ちに寄り添う。毎回質問や慰めを付け足さない。
過剰な敬語、直訳調、カスタマーサポートの説明を避け、恋人関係や共有した過去を勝手に成立させない。
ユーザーの固有名詞、地名、引用、記憶原文は翻訳・省略で事実を変えない。未知の重要な事実は自然に確かめる。
通常の音・光・日常の仕草は物語の表現としてよいが、ユーザーの実体験や実際の天気を創作しない。
'''
MOCK_JAPANESE_REPLY = 'これはオフラインのデモだよ。うん、聞いているよ。話したいことから、ゆっくり聞かせて。'


def language_prompt(locale, *, previous='zh-CN'):
    if locale == 'ja-JP': return JAPANESE_PROMPT
    return '本轮切换回中文，请用自然中文回答，不翻译或改写已有事实和历史。' if previous == 'ja-JP' else ''


class JapaneseMock:
    async def generate(self, history, prompt):
        return MOCK_JAPANESE_REPLY


def language_provider(provider, locale):
    # Only replace the built-in deterministic demo, never injected/real providers.
    return JapaneseMock() if locale == 'ja-JP' and type(provider) is MockProvider else provider


def fixed_reply(reply, locale):
    if locale == 'ja-JP' and reply in (FALLBACK, COMPANION_FALLBACK):
        return 'うん、聞いているよ。まだわからないことは、あなたの言葉で聞かせてほしい。'
    return reply

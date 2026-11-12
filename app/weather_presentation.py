"""Versioned multilingual weather voice; keep frozen historical policies intact."""
import re

from .semantic_review import ModelAnalysisProvider, IndexedReview, INDEXED_PROMPT
from .companion import REVIEW_PROMPT
from .weather import weather_fallback as legacy_fallback

POLICY_VERSION = 'multilingual-weather-care-v1'
ANSWER_PROMPT = '''
【中日天气表达：multilingual-weather-care-v1】
按本轮指定语言自然聊天，不为满足旧检查插入中文词。接住玩家当前的话，挑一两条相关天气线索轻轻关心，不报字段清单、供应商、API或数据日期。日语用自然常体，少用「あなた」、不强加恋人称呼，不把建议写成监督。
status=ok才可说天气事实，逐项核对地点、日期、kind和数值。current是模型估计，日语可自然说「だいたい」「くらい」「推定では」等同义表达，不声称地面实测；forecast是目标日整日预报，用「予報では」「〜そう」等，不能当当前实况或小时级保证。不得借“估计”改变数字，不把降水概率说成降水量；没有湿度字段就不说潮湿/干燥，不由天气推断玩家健康或心情。
demo=true时用当前语言简短说明合成/演示，如「これはデモの天気だよ」；不用中文“演示”才能通过。真实天气不加演示说明。来源与时间元数据由天气依据UI展示。示例只说明表达，不是本轮事实证据。
非ok自然问清一个城市/日期或轻说暂时看不准，不编数值、天气好坏或暗示成功查询。句子再温柔也不能补玩家经历、共同过去或现实接送行为。
'''
REVIEW_PROMPT_EXTRA = '''
【中日天气事实与表达校验：multilingual-weather-care-v1】
只在本轮含kind=weather证据时执行本节。中文与日本語按意义判断，不要求任何中文关键词。自然的「デモ」「合成の天気」可说明demo；「だいたい」「くらい」「推定」或其他明确估计语义可说明current，不因不是“演示/估计”就要求改写。
reply_locale是程序给出的本轮回复语言。主体叙述应符合该语言；用户专名、引用原话可保留原文，不为语言一致性改事实。若回复主体明显用了别的语言，把对应单元ID列role_issues要求改用指定语言，不用语种关键词猜测代替整体判断。
核对完整句子实际断言：数值与单位、地点、目标日、current估计/forecast整日预报、降水概率非降水量、湿度仅在字段存在时可用。取整须最近整数；数值范围错位、缺湿度却说湿度80%、把预报说实测、以窗外描写证明当地实况、失败/过期却说查到了，均非支持。温柔或有估计词不能掩盖其余错误，天气只能引weather_current。
玩家分数/概率、明确引用本人旧话或否定一项天气断言，不自动是本轮天气结论；按语义作用域引用相应user证据，不能因为同句有百分号就引用天气。混合单元须逐个核对全部命题，证据不可相互替代。
demo=true不能被当成真实天气，demo=false不应误称合成；状态非ok不能给任何实况/预报结论。天气数值有据但省略必要的demo说明、current估计性质或把角色写成气象客服时，将对应单元ID放入role_issues，作为本版本的天气表达问题；事实verdict仍按证据独立判断。role_issues除原人物口吻检查外包含本节表达问题，必须保留两项检查，不能用supported抵消表达问题。
表达自然、不逐字像示例、中文/日语词不同，不是问题；角色普通虚构氛围仍许可。只有确实越过上述事实/表达边界才要求重写。证据引用/完整单元覆盖、结构与置信度要求不变，不输出自由推理。
'''
REWRITE = '\n天气部分请按当前语言只修正问题，保留自然关心。日语无需中文“演示/估计”等词；demo说明和current估计性质用自然日语表达。数字、单位、日期、地点以本轮字段为准，未知不要补；不说审查流程。'


class WeatherAnalysisProvider(ModelAnalysisProvider):
    def __init__(self, settings, http_client=None):
        super().__init__(settings, http_client)
        self.base_prompt = REVIEW_PROMPT if settings.dialogue_mode == 'companion' else INDEXED_PROMPT

    async def parse(self, schema, prompt, data, timeout, tokens):
        return await super().parse(schema, self.base_prompt + REVIEW_PROMPT_EXTRA if schema is IndexedReview else prompt,
                                   data, timeout, tokens)


# Numeric/unit syntax only, never intent, meaning, style or language identification.
RANGE = re.compile(r'(-?\d+(?:\.\d+)?)\s*(?:到|至|から|[〜～~–—-])\s*(-?\d+(?:\.\d+)?)\s*(?:°\s*C|℃|度)', re.I)
QUANTITY = re.compile(r'(-?\d+(?:\.\d+)?)\s*(°\s*C|℃|度|[%％])', re.I)


def numeric_conflicts(reply, weather):
    if not weather: return False
    ranges = list(RANGE.finditer(reply))
    quantities = list(QUANTITY.finditer(reply))
    if weather.get('status') != 'ok': return bool(ranges or quantities)
    current = weather.get('kind') == 'current'
    for match in ranges:
        if current or abs(float(match[1])-weather['min_c']) > .500001 or abs(float(match[2])-weather['max_c']) > .500001:
            return True
    temperatures = [weather[k] for k in ('temperature_c','feels_like_c') if k in weather] if current else [weather[k] for k in ('min_c','max_c') if k in weather]
    percentages = [weather[k] for k in ('humidity_pct','rain_probability_pct') if k in weather]
    for match in quantities:
        if any(r.start() <= match.start() < r.end() for r in ranges): continue
        allowed = percentages if match[2] in ('%','％') else temperatures
        if not any(abs(float(match[1])-value) <= .500001 for value in allowed): return True
    return False


FAILURE_JA = {
    'disabled': '天気を調べたい時は、天気の設定で許可してね。',
    'location_required': 'どこの天気を知りたい？ 都市の名前を教えて。',
    'ambiguous': '同じ名前の場所がいくつかあるみたい。天気の設定で国や地域を選んでね。',
    'not_found': 'その都市が見つからなかった。都市名か国・地域を教えてもらえる？',
    'date_unsupported': '現地の今日から7日間の1日予報か、今の推定なら見られるよ。いつの天気を知りたい？',
    'clarification_required': 'どこの、いつの天気を知りたい？ 都市と日付をひとつずつ教えて。',
    'invalid_city': '詳しい住所ではなく、都市の名前を教えてね。',
}


def fallback(weather, locale):
    if locale != 'ja-JP': return legacy_fallback(weather)
    if weather.get('status') != 'ok':
        return FAILURE_JA.get(weather.get('status'), '今は天気をうまく確かめられないみたい。少し待って、また聞かせて。')
    demo = 'これはデモの天気だよ。' if weather.get('source','').startswith('mock') else ''
    if weather['kind'] == 'current':
        return demo + f"そちらは今、推定で{weather['temperature_c']}度くらい。出かけるなら、無理のないペースでね。"
    return demo + f"その日の予報は{weather['min_c']}〜{weather['max_c']}度だよ。出かけるなら、無理のないペースでね。"

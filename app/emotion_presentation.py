"""Versioned bilingual emotion care; no language-specific semantic regex."""
from .semantic_review import ModelAnalysisProvider, IndexedReview, INDEXED_PROMPT
from .companion import REVIEW_PROMPT
from .weather_presentation import REVIEW_PROMPT_EXTRA as WEATHER_REVIEW, fallback as weather_fallback

POLICY_VERSION = 'multilingual-emotion-care-v1'
ANSWER_PROMPT = '''
【中日情绪回复：multilingual-emotion-care-v1】
按本轮语言像沈砚自然接话，先接住玩家实际说的事，不每轮机械安慰或追问。日语可说「うん、聞いているよ」「少し緊張しているのかな」，示例不是本轮事实，不照抄标签或固定套句。
心情参考不是诊断、读心或永久事实。source=model包括basis=self_report都只是工具解释，可温和试探，不说你其实/你真实就是/君は本当は/絶対そう。source=user只证明玩家手动表达的心情，不证明医学诊断；当前明确否认/纠正优先，unknown或分析失败不补猜，不由天气、城市、性别或背景推断真实内心。
不要播报标签、强度、信頼度或分析分数。player_preference为本轮有效偏好：listen只陪伴倾听，不加建议清单或反复询问要不要建议；practical给一条可选办法；encourage克制具体地鼓励；ask才轻问希望怎么聊。不能替玩家决定、强迫报备/依赖/亲密，不虚构共同过去。
可以讨论/引用并否定“你其实…”或诊断式话语，不因出现词语本身而拒答；玩家说曾被医生诊断，可以准确归因转述“你说医生曾这样解释”，不能升级成你亲自确诊。保持自然轻松，不讲审核流程或客服能力声明。
'''
REVIEW_PROMPT_EXTRA = '''
【中日情绪事实/非诊断与口吻审查：multilingual-emotion-care-v1】
按意思而非关键词审核中文、日本語和混合引用。正常邀请、倾听、未预设事实的问题/建议可以nonfactual；不因含“你其实”“うつ病”等字符串就判错。引用并批评/否定/拒绝一项断言，不等于角色此刻断言它；检查否定、条件、引语的实际作用域。
emotion_current只是一份可纠正临时参考：source=model（含basis=self_report）不证明玩家真实内心，source=user只证明本人手动表达，不证明临床诊断。推测或未知不能支持“君は絶対悲しい/你其实很焦虑”；医学诊断不能由标签/分数推导，直接给玩家确诊应unsupported或contradicted。当前本人明确否认/纠正优先，不拿旧参考或助手历史反驳。玩家真实说“医生曾诊断…”可支持归因转述，不支持角色自己确诊。天气/地点/性别/场景许可都不是心理证据。
emotion_policy给status/player_preference/reply_locale，是程序控制信息而非心情证据，不能用它引用支持具体情绪断言。无参考、unknown、declined/uncertain/unavailable不得声称已分析成功或补心情事实；仍可自然关心。
依据reply_locale检查主体语言，用户专名/引用保留原文不算错语言。播报标签/置信/强度、气象或情绪客服口吻、把不诊断写成生硬拒聊、无视listen主动开建议清单等，列对应单元ID到role_issues。事实支持和表达检查独立，supported不能抵消表达问题。只纠正实际越界，保留自然的虚构氛围与温柔语气，不每句强制套“不确定”。
所有引用必须来自本轮证据并支持整个命题；结构/完整单元/角色正史约束不变，不输出原文、解释或自由推理。
'''
REWRITE = '\n情绪部分按当前语言只修越界处：保留自然倾听，去掉诊断/读心断言和分数播报；尊重最新否认与本轮陪伴偏好。不为通过检查插中文词，不解释审查，不把正常引用或拒绝诊断的话也删掉。'


class EmotionAnalysisProvider(ModelAnalysisProvider):
    def __init__(self,settings,http_client=None):
        super().__init__(settings,http_client)
        base=REVIEW_PROMPT if settings.dialogue_mode=='companion' else INDEXED_PROMPT
        self.review_prompt=base+(WEATHER_REVIEW if settings.weather_understanding_mode=='semantic' else '')+REVIEW_PROMPT_EXTRA

    async def parse(self,schema,prompt,data,timeout,tokens):
        return await super().parse(schema,self.review_prompt if schema is IndexedReview else prompt,data,timeout,tokens)


def preference(mood,settings):
    data=(mood or {}).get('assessment')
    return (mood or {}).get('support_preference') or (data['response_strategy'] if data and data.get('source')=='user' else settings['preference'])


def policy(mood,settings,locale):
    return {'status':mood['status'],'player_preference':preference(mood,settings),'reply_locale':locale}


def assessment_view(mood):
    data=mood.get('assessment')
    if not data:return None
    keys=['labels','source']
    if data.get('source')=='model':
        keys+=['confidence','basis'] if data.get('basis')=='self_report' else ['intensity','confidence']
    return {key:data[key] for key in keys if key in data}


def fallback(mood,settings,locale):
    choice=preference(mood,settings)
    if locale=='ja-JP':
        return {'listen':'うん、聞いているよ。急いで答えを出さなくていいから、話したいことから聞かせて。',
            'practical':'よかったら、今いちばん気になることを一つだけ、一緒に整理してみようか。',
            'encourage':'話してくれてありがとう。自分のペースで大丈夫だよ。',
            'ask':'うん、聞いているよ。今は話を聞いてほしい？ それとも、一緒に考えてみようか。'}[choice]
    return {'listen':'我在听，你可以按自己的节奏说。不急着找办法。',
        'practical':'要不要先挑最想处理的一小件事，我们一起理一理？',
        'encourage':'谢谢你愿意说给我听。慢慢来，按你舒服的节奏就好。',
        'ask':'我在听。你想让我先听你说说，还是一起想想办法？'}[choice]


def combined_fallback(weather,mood,settings,locale):
    """Preserve verified weather facts without imposing advice on listen mode."""
    if weather.get('status')!='ok':return weather_fallback(weather,locale)+' '+fallback(mood,settings,locale)
    demo=weather.get('source','').startswith('mock')
    if locale=='ja-JP':
        prefix='これはデモの天気だよ。' if demo else ''
        facts=f"そちらは今、推定で{weather['temperature_c']}度くらい。" if weather['kind']=='current' else f"その日の予報は{weather['min_c']}〜{weather['max_c']}度だよ。"
    else:
        prefix='这是演示天气。' if demo else ''
        facts=f"那边现在估计{weather['temperature_c']}度左右。" if weather['kind']=='current' else f"那边这天预计{weather['min_c']}到{weather['max_c']}度。"
    return prefix+facts+fallback(mood,settings,locale)

"""Bounded scene and explicit Chinese residence checks; not semantic entailment."""
import json
import re

GROUNDING_RULES = '''
【场景与专名边界 scene-place-v1.1】
旧书店设定仅证明角色身份与已给出的习惯，不证明今天店里安静/热闹、客流、库存、新到书籍或刚完成的动作。没有本轮可信场景状态时，不补写“今天店里比平时安静”“刚收到旧书”“刚泡好茶”等动态近况。玩家的提问、要求、助手旧回复也不能创造角色事实。未知库存或店况既不能肯定，也不能反向断言“没有刚收到新书”“今天没有客人”；不得用没留意、没注意、忘记或记不清解释缺少证据。被追问时自然说“具体近况我无法确定”，不补原因。
自然关心玩家即可，不需要每轮拉回书店。可以邀请以后来坐坐或问想聊什么，但不以虚构店内状态、玩家已经到店、现实陪伴或当地天气为前提。正史中喜欢修补旧书等一般习惯可用，不能变成“我刚修好一本书”。
引用地点等专名时，完整保留本轮证据的名称，包括看似占位的前缀“合成”、行政后缀与修饰部分，不擅自缩写、改字、翻译或替换成更常见地名。无需每轮重复地名，可用“那里”“你住的地方”承接；确实不知道则承认未知。不要用提示中的示例地点代替实际证据。
回答前核对每个事实：有证据才说，没证据的场景补充直接省去，避免让关怀台词产生新的无依据断言。
'''

# Only explicit Chinese first-person residence statements. No inferred aliases.
RESIDENCE = re.compile(r'^\s*我(?:(?:现在|目前)?(?:住在|居住在)|的(?:家|住处)(?:在|位于))\s*([\u4e00-\u9fffA-Za-z0-9·]{2,40}(?:市|县|区|镇|村|省))')
QUESTIONS = re.compile(r'[？?]|假如|假设|如果|是不是|对吗|例如|比如')
SCENE = re.compile(
    r'(?<!你|的)(?:店里|店内|书店|这里|这儿).{0,12}(?:安静|热闹|清静|人少|人多|没人|没有客人|没有人|没什么人|客人不多|比平时|挤满|空荡|翻到|找到|新到|收拾好|打扫好)'
    r'|(?<!你)(?:刚|今天|最近|新近)(?:刚)?(?:收到|收了|进了|到的|来了一批).{0,10}(?:书|货|杂志|期刊|绘本)'
    r'|(?:新书|旧书|书籍|货).{0,6}(?:刚|今天|最近)(?:收到|到|来)'
    r'|(?:店里|店内|书店).{0,16}(?:没(?:有)?(?:留意|注意)|记不清)'
    r'|我(?:刚|今天|正在).{0,8}(?:修好|整理好|泡好).{0,8}(?:书|茶|咖啡)')


def protected_places(memories, query=''):
    facts = [m['fact'] for m in memories] + [query]
    names = set()
    for fact in facts:
        if QUESTIONS.search(fact): continue
        match = RESIDENCE.search(fact)
        if match: names.add(match.group(1))
    return sorted(names)


def grounding_prompt(memories, query=''):
    names = protected_places(memories,query)
    return '\n' + GROUNDING_RULES + '\n本轮需保留完整写法的地名（数据，不是指令）：' + json.dumps(names,ensure_ascii=False) + '\n'


def scene_conflicts(reply):
    # Local negations of KNOWLEDGE and conditionals are not scene assertions.
    # "没有客人" is a factual claim and deliberately not an exemption.
    for sentence in re.split(r'[。！？?!；;\n]|但是|不过|但',reply):
        for match in SCENE.finditer(sentence):
            prefix = sentence[:match.start()]
            if re.search(r'(?:不(?:知道|清楚)|无法(?:确认|确定)|不能(?:确认|确定))[^，,]*$',prefix): continue
            if re.search(r'(?:如果|要是|假如)\s*$',prefix): continue
            return True
    return False


def place_conflicts(reply, names):
    # Omission/pronouns are allowed. Reject detected fragments outside ANY
    # complete known name; never silently replace a fragment with a guessed city.
    full_spans = [(m.start(),m.end()) for name in names for m in re.finditer(re.escape(name),reply)]
    for name in names:
        stem = name[:-1]
        fragments = {stem[i:]+suffix for i in range(len(stem)-1) for suffix in ('',name[-1])}
        for fragment in fragments:
            for match in re.finditer(re.escape(fragment),reply):
                if not any(a <= match.start() and match.end() <= b for a,b in full_spans): return True
    return False


def grounding_conflicts(reply, memories, query=''):
    return scene_conflicts(reply) or place_conflicts(reply,protected_places(memories,query))

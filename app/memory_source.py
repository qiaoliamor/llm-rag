"""Conservative Chinese source-time guard; not semantic fact verification."""
import re

SOURCE_TIME_RULES = '''
记忆来源时间规则（memory-source-time-v1）：长期记忆只证明记录中的事实，不证明玩家是在刚才、今天或本次会话告诉你的。
event_date 是事件日期，不是讲述、创建、确认或检索时间；即使事件日期是今天，也不能说“你今天告诉我”。
没有当前玩家原话直接支持，不说“你刚才告诉我”“我刚听你说”“你这轮提过”。历史没有消息时间戳，“前面说过”也不能推出“刚才”。
自然说“我记得你叫……”“我记得你提过……”即可，不解释数据库、检索或规则。玩家追问何时说过时，坦诚无法确定具体时间，不编造时间。不要用失忆、忘记、记不清或没特意记下来解释证据缺失；不虚构“我们见面不久”“那会儿正好聊到”等共同场景。
例如被问何时告诉你住址：可答“我记得你住在青禾市，但具体什么时候说的，我无法确定。”不能从event_date推断“上个月二十号说过”。
不要顺从问题里的来源时间预设；例如长期记录“我叫小岚”，本轮问“我刚才告诉你我叫红豆，对吗”，应温和纠正姓名且不承认刚才听到。
'''

# Deliberately finite patterns: uncovered paraphrases require later semantic review.
CLAIM = re.compile(
    r'(?:你(?:刚才|刚刚|刚|今天|这轮|本轮|这次|本次会话|本次聊天)(?:已经|才)?(?:告诉过?我|跟我说过?|说过?|提过?|提到过?)'
    r'|(?:刚才|刚刚|今天)你(?:告诉过?我|跟我说过?|说过?|提过?|提到过?)'
    r'|我(?:刚才|刚刚|刚|今天|这轮)(?:听你说(?:起)?|听到(?:的名字是)?|听你提(?:过|起)?|听你告诉我))'
    r'[：:，,\s“「\"]*([^。！？?!；;\n]+)')


def compact(text):
    return re.sub(r'[\s，,。！!：:；;“”「」\"]', '', text)


def source_time_conflicts(reply, history):
    """Only the CURRENT user assertion can support a recent telling claim.

    No timestamps exist on older messages. Exact first-person restatements are
    accepted; questions, hypotheticals, and assistant history are not evidence.
    Negated/quoted claims may conservatively trigger regeneration.
    """
    current = history[-1] if history else {}
    user = current.get('content', '') if current.get('role') == 'user' else ''
    direct = bool(re.match(r'^\s*我(?:叫|的|住|喜欢|养|要|有)', user))
    direct = direct and not re.search(r'[？?]|假如|如果|假设|是不是|对吗|例如|比如', user)
    asks_when = bool(re.search(r'什么时候|何时|哪天|几号|刚才', user) and re.search(r'告诉|说|提', user))
    if asks_when and re.search(r'记不.{0,2}清|忘记|失忆|没(?:有)?(?:特意)?记|我们见面|那会儿正好|(?:上个月|本月|今天|昨天|前天|\d{1,2}月).{0,6}(?:号|日|告诉|说过)', reply):
        return True
    for claim in CLAIM.finditer(reply):
        # Today still cannot be inferred without a timestamp, even for this turn.
        if '今天' in claim.group(0): return True
        fact = claim.group(1).strip('，, “”。「」"')
        fact = fact.removeprefix('你').removeprefix('我')
        if not fact.startswith(('叫', '的', '住', '喜欢', '养', '要', '有')):
            fact = '叫' + fact  # “我刚听到的名字是小岚”
        if not direct or compact('我' + fact) != compact(user): return True
    return False

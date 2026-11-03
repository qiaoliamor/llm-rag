"""Conservative query/evidence compatibility rules, not semantic entailment."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class EvidenceNeed:
    subject: str
    field: str | None = None
    time: str | None = None


PET = r'猫咪|小猫|宠物|猫|狗'
RELATION = r'朋友|同事|妈妈|母亲|爸爸|父亲|父母|姐姐|弟弟'
RELATIONS = {'friend':'朋友','colleague':'同事','mother':'妈妈|母亲',
             'father':'爸爸|父亲','parents':'父母','sister':'姐姐','brother':'弟弟'}
PET_OWNER = r'我(?:(?:的|家|家的)|养的|有(?:一只)?|家有(?:一只)?|养了(?:一只)?)?(?:'+PET+r')'
CHILD = r'小时候|童年|幼年|从小'
PAST = r'以前|曾经|过去|之前|曾住'


def evidence_need(query):
    own_name = re.search(r'我(?:的|自己的)?(?:名字|姓名|称呼)|我(?:现在|以前|曾经|小时候)?叫(?:什么|啥|.{1,20}(?:吗|对不对))', query)
    relation = re.search(r'(?:我(?:的)?|^)('+RELATION+r')',query)
    if own_name: subject = 'player'
    elif re.search(PET_OWNER, query): subject = 'pet'
    elif relation:
        subject = 'relation:'+next(k for k,v in RELATIONS.items() if re.fullmatch(v,relation.group(1)))
    elif '我' not in query and re.search(r'你(?:的|叫|住|小时候)|沈砚', query): subject = 'character'
    else: subject = 'player'
    if own_name or ((subject == 'pet' or subject.startswith('relation:')) and re.search(r'名字|姓名|叫什么|叫啥|叫.{1,20}吗', query)):
        field = 'name'
    elif re.search(r'护照(?:号码|号|编号)', query): field = 'passport'
    elif re.search(r'身份证(?:号码|号)|身份证编号', query): field = 'identity_number'
    elif re.search(r'电话(?:号码|号)|手机号', query): field = 'phone'
    elif re.search(r'住哪|住在|住过|住处|居住|住.{0,6}(?:哪|城市|地方)|我的城市|我(?:现在|目前)?在(?:哪个|什么|哪座)城市[？?。]*$', query): field = 'residence'
    else: field = None
    scope = 'childhood' if re.search(CHILD,query) else None
    if field in ('name','residence') and scope is None:
        scope = 'past' if re.search(PAST,query) else 'current'
    return EvidenceNeed(subject,field,scope)


def own_fact(fact):
    return bool(re.match(r'\s*我',fact)) and not (re.match(r'\s*'+PET_OWNER,fact) or re.match(r'\s*我(?:的)?(?:'+RELATION+')',fact))


def player_name_fact(fact):
    return bool(re.match(r'\s*我(?:现在|以前|曾经|小时候)?(?:叫|的名字是|的姓名是)(?!朋友|同事|你|他|她|不知道|不叫|不是|没有).+',fact))


def compatible(need, fact):
    """Only explicit supported fields/time/subjects qualify for a targeted query."""
    if need.subject == 'character': return False
    if need.subject == 'pet':
        prefix = PET_OWNER
        if not re.match(r'\s*'+prefix,fact): return False
    elif need.subject.startswith('relation:'):
        prefix = r'我(?:的)?(?:'+RELATIONS[need.subject.split(':')[1]]+r')'
        if not re.match(r'\s*'+prefix,fact): return False
    elif need.field and not own_fact(fact): return False
    if need.time == 'childhood' and not re.search(CHILD,fact): return False
    if need.time == 'past' and not re.search(PAST,fact): return False
    if need.time == 'current' and re.search(CHILD+'|'+PAST+r'|将来|打算|计划|明年|准备搬',fact): return False
    if need.field:
        if re.search(r'^\s*[“「"]|假如|如果|不知道|不确定|记不清|不记得',fact): return False
        if need.field == 'name':
            if need.subject == 'player': return player_name_fact(fact)
            return bool(re.match(r'\s*'+prefix+r'(?:的)?(?:叫|名字是|姓名是)(?!什么|谁|不知道|不叫|不是).+',fact))
        if need.field in ('passport','identity_number','phone'):
            markers = {'passport':r'护照(?:号码|号|编号)',
                       'identity_number':r'身份证(?:号码|号|编号)', 'phone':r'电话(?:号码|号)|手机号'}
            owner = r'我(?:现在|目前)?(?:的)?' if need.subject == 'player' else prefix+r'(?:的)?'
            return bool(re.match(r'\s*'+owner+r'(?:'+markers[need.field]+r')(?:是|为|[：:])\s*\S+',fact))
        if need.field == 'residence':
            if re.search(r'(?:不|没|未|没有|不是|并非|不曾|从未)(?:曾经|一直)?(?:住在|住过|居住在|生活在)',fact): return False
            owner = '我' if need.subject == 'player' else prefix
            adverbs = r'(?:现在|目前|以前|曾经|过去|之前|小时候|童年|幼年|从小|一直|曾|就|也|和朋友|和父母)*'
            return bool(re.match(r'\s*'+owner+adverbs+r'(?:住在|住过|居住在|生活在)|\s*'+owner+r'的住处(?:是|在)',fact))
    return True


# Remove question scaffolding, not proposed names/numbers or negations.
SCAFFOLD = re.compile(r'你还记得|还记得|记得|请告诉我|告诉我|请问|能不能|可不可以|可以|什么时候|怎么|怎样|哪些|哪家|哪个|哪里|什么|多久|为什么|'
                      r'对不对|对吗|是不是|是否|我的|你的|关于|说说|一下|情况|经历|事情|准备|参加|平时|正在|以前|曾经|现在|目前|小时候|童年|幼年|从小|'
                      r'我|你|的|是|吗|呢|了|就|在|有|和|与|及|也|还|都|哪')


def content_text(text):
    return SCAFFOLD.sub('',text)

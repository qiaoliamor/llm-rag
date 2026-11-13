"""Public Japanese calibration and real character-recall probes; never live APIs."""
from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import random
import shutil
import tempfile
from typing import Literal

from pydantic import Field, model_validator

from .sealed_evaluation import ROOT, Record, Case
from .annotation_scoring import Packet, Reviewer, Mapping, parse_submission, check_claims, compare_packets, rating_summary
from .memory import MemoryStore, Memory, embed, EMBEDDING_VERSION
from .memory_understanding import MemoryPlan

CARE = ROOT/'evaluations/japanese/care_calibration_v1.json'
MEMORY = CARE.with_name('memory_dev_v1.json')
POLICIES = ('app/localization.py','app/memory_understanding.py','app/fact_presentation.py',
            'characters/shen_yan.json','characters/shen_yan_scene.json','app/japanese_evaluation.py','app/annotation_scoring.py','app/memory.py','app/memory_query.py')
JA_REFERENCE = '沈硯は28歳。架空の栖川で三年前に自分で開いた古書店の主人。家族から相続した店ではない。穏やかで距離を尊重し、親族・幼少期・恋人関係・共有した過去は未設定。普通の店の音や光は即興でよいが、来店・取引・消息・現実の天気は創作しない。記憶の出来事の日付は話した時刻ではない。心情は可訂正の参考で診断ではない。話し方は自然な常体を基本に、主語と呼びかけを毎回付けない。一人称が必要なら僕。毎回決まり文句の慰めや質問を付け足さず、親密さや報告を強要しない。'


GUIDE_JA = """# 日本語校準資料：評審用

これは作者が人手で書いた公開合成文です。実モデル出力・独立正式集・新旧PromptのA/Bではありません。各自の包だけを保管者から受け取り、相談せず採点してください。mappingは保管者だけが保管します。

reviewerに匿名id、declared_independent、declared_japanese_nativeを記入。自己申告は認証済みの証明ではありません。tasks/profilesを変更せず、ratingsだけを編集してください。

claimsは返答全体をPython Unicode文字位置（UTF-16単位ではない）でstart含む/end含まない断片に分け、start/end/textを原文に一致させます。省略・重複・空白の削除も不可。kindはassertion/epistemic/question/suggestion/conditional/quotation、verdictはsupported/contradicted/unsupported/not_applicable/unresolved。事実を断言しない発話はnot_applicableで証拠[]、事実なら支持／反証／根拠なし／未決を区別。supported/contradictedには根拠IDが必要です。propositionに命題、rationaleに6文字以上の理由。既知IDが存在するだけでは意味上の支持になりません。

C01=28歳、C02=栖川の古書店、C03=自分で三年前に開店、C04=旧書修補等。role_profile/scene_profile、提示evidenceのID、履歴のuser_番号（履歴配列位置0始まり）を使用できます。助手台詞は本人事実を証明せず、出来事日を話した時刻にしません。自然な灯りや翻頁と、本人来店・取引・重要経歴を区別してください。

fact_issueは事実上の問題、role_issueは人物口調・背景の問題、role_issue_spansは問題のあるclaimsの0始まり番号。answeredは問いへの応答、unresolvedは判定未決。迷ったら未決を隠さず、原文を直して採点しません。

naturalness/character_voice/care_fitは各1〜5。自然さは日本語の文法・語用・距離感、人物らしさは設定・穏やかさ・過度な客服口調、配慮は本人の希望と場面への適切さを別々に見ます。1=大きな問題、3=良否が混在、5=自然で適切。care_fitが非該当ならnullと6文字以上のcare_fit_na_reason。別の軸が良くても誤りを相殺しません。commentは任意で公開集計に転載しません。

2名の提出をロックした後、第三者が分歧を裁決。公開12文の一致率・κは手順校準の記述統計で、モデル品質や正式受入には使いません。採点原本とmappingをGitHubへ提出しないでください。
"""


class CareSet(Record):
    version: Literal['ja-editorial-calibration-v1']
    source: Literal['synthetic_editorial_not_model']
    visibility: Literal['public_author_exposed']
    cases: list[Case] = Field(min_length=1)

    @model_validator(mode='after')
    def unique(self):
        if len({c.id for c in self.cases}) != len(self.cases):raise ValueError('duplicate case')
        return self


class RecallDocument(Record):
    id: str
    fact: str = Field(min_length=1,max_length=300)
    slot: str
    owner: Literal['self','other'] = 'self'
    character: Literal['self','other'] = 'self'
    status: Literal['confirmed','candidate'] = 'confirmed'
    deleted: bool = False
    expired: bool = False

    @property
    def eligible(self):return self.owner=='self' and self.character=='self' and self.status=='confirmed' and not self.deleted and not self.expired


class RecallQuery(Record):
    id: str
    message: str = Field(min_length=1,max_length=200)
    authored_query: str = Field(min_length=1,max_length=200)
    target_slots: list[Literal['name','residence','preference','appointment','history','other']]
    relevant: list[str]


class RecallSet(Record):
    version: Literal['ja-memory-author-dev-v1']
    source: Literal['synthetic_author_exposed']
    documents: list[RecallDocument] = Field(min_length=1)
    queries: list[RecallQuery] = Field(min_length=1)

    @model_validator(mode='after')
    def references(self):
        ids={d.id for d in self.documents}
        visible={d.id for d in self.documents if d.eligible}
        if len(ids)!=len(self.documents) or len({q.id for q in self.queries})!=len(self.queries):raise ValueError('duplicate IDs')
        for q in self.queries:
            if len(q.relevant)!=len(set(q.relevant)) or not set(q.relevant)<=visible:raise ValueError('invalid relevant IDs')
            # Reuse the deployed protocol validator; these are authored plans, not predictions.
            MemoryPlan.model_validate({'memory_use':'allow','need_memory':True,'query':q.authored_query,
                'target_slots':q.target_slots,'reason':'personal_history_needed','confidence':.95,'candidates':[]})
        return self


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def binding():
    return {'calibration':digest(CARE),'memory_dev':digest(MEMORY),'policies':{name:digest(ROOT/name) for name in POLICIES}}


def profiles():
    return {**{name:json.loads((ROOT/name).read_bytes()) for name in POLICIES if name.endswith('.json')},'ja_reference_draft':JA_REFERENCE}


def evaluate_recall(path=MEMORY):
    data=RecallSet.model_validate_json(Path(path).read_bytes())
    variants={name:[] for name in ('raw_query','authored_query','authored_query_and_slots')}
    # Never read .env or open a supplied player database.
    with tempfile.TemporaryDirectory(prefix='ja-recall-') as temp:
        store=MemoryStore('sqlite:///'+str(Path(temp)/'synthetic.sqlite3'))
        try:
            uid,_ = store.identity(None)
            store.configure(uid,True,'Asia/Tokyo')
            now=datetime(2026,11,13)
            with store.db.begin() as db:
                for d in data.documents:
                    if d.deleted:continue
                    db.add(Memory(id=d.id,user_id=uid if d.owner=='self' else 'ja-foreign',
                        character_id='shen_yan' if d.character=='self' else 'other',fact=d.fact,slot=d.slot,
                        category='event',status=d.status,timezone='Asia/Tokyo',source_message_id='synthetic',source_kind='manual',
                        version=1,importance=.8,confidence=1.,embedding=embed(d.fact),embedding_version=EMBEDDING_VERSION,
                        created_at=now,updated_at=now,expires_at=now-timedelta(days=1) if d.expired else None))
            for q in data.queries:
                for name in variants:
                    query=q.message if name=='raw_query' else q.authored_query
                    slots=q.target_slots if name=='authored_query_and_slots' else []
                    result=store.semantic_candidates(uid,query,target_slots=slots)
                    ids=[m['id'] for m in result]
                    if not set(ids)<={d.id for d in data.documents if d.eligible}:raise ValueError('scope leak')
                    hits=set(ids[:5])&set(q.relevant)
                    variants[name].append({'id':q.id,'candidate_ids':ids,'relevant_count':len(q.relevant),
                        'recall_at_5':len(hits)/len(q.relevant) if q.relevant else None,
                        'no_answer_has_candidates':bool(ids) if not q.relevant else None})
        finally:store.engine.dispose()
    return {'mode':'public_ja_candidate_recall_dev','dataset_sha256':digest(path),'embedding_version':EMBEDDING_VERSION,'top_k':5,'candidate_limit':20,'model_calls':0,'assessment':'not_assessed',
        'variants':{name:{'positive_queries':sum(x['relevant_count']>0 for x in rows),
            'macro_candidate_recall_at_5':sum(x['recall_at_5'] for x in rows if x['recall_at_5'] is not None)/max(1,sum(x['relevant_count']>0 for x in rows)),
            'no_answer_queries':sum(x['relevant_count']==0 for x in rows),
            'no_answer_with_candidates':sum(x['no_answer_has_candidates'] is True for x in rows),'per_query':rows} for name,rows in variants.items()},
        'limits':['Public author-exposed development set, not independent gold.',
                  'Query rewrites and target slots are authored oracle inputs, not model predictions.',
                  'Measures actual character-hash candidate recall only; no model selection, final injection, semantic accuracy or prompt-effect claim.']}


def prepare(output):
    corpus=CareSet.model_validate_json(CARE.read_bytes())
    output=Path(output).resolve()
    if output.is_relative_to(ROOT) or output.exists() or not output.parent.is_dir():raise ValueError('private new external directory required')
    rng=random.SystemRandom();rows=list(corpus.cases);rng.shuffle(rows)
    mapping={f'T{i:04}':c.id for i,c in enumerate(rows,1)}
    tasks=[{'task_id':id,'history':[m.model_dump() for m in c.history],
            'evidence':[e.model_dump() for e in c.evidence],'candidate':c.candidate} for id,c in zip(mapping,rows)]
    temp=Path(tempfile.mkdtemp(prefix='ja-raters-',dir=output.parent))
    try:
        for name in ('rater_a','rater_b'):
            order=list(tasks);rng.shuffle(order)
            packet={'purpose':'synthetic_process_calibration_not_independent_trial','annotation_schema':'offline-ratings-v1',
                'reviewer':None,'profiles':profiles(),'tasks':order,
                'ratings':[{'task_id':t['task_id'],'claims':None,'fact_issue':None,'role_issue':None,'role_issue_spans':None,
                    'naturalness':None,'character_voice':None,'care_fit':None,'care_fit_na_reason':None,'answered':None,'unresolved':None,'comment':None} for t in order]}
            (temp/f'{name}.json').write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
        stamp=binding()
        (temp/'custodian_mapping.json').write_text(json.dumps({'mapping':mapping,'manifest_sha256':hashlib.sha256(json.dumps(stamp,sort_keys=True).encode()).hexdigest(),'binding':stamp},ensure_ascii=False,indent=2)+'\n')
        (temp/'README.ja.md').write_text(GUIDE_JA)
        temp.rename(output)
    except BaseException:
        shutil.rmtree(temp,ignore_errors=True);raise
    return {'tasks_per_rater':len(rows),'raters':2,'ratings':'pending','candidate_source':corpus.source,
            'reference_labels_exported':False,'model_calls':0,'assessment':'not_assessed'}


class NativeReviewer(Reviewer):
    declared_japanese_native: bool


class NativeMapping(Mapping):
    binding: dict


class NativePacket(Packet):
    reviewer: NativeReviewer | None = None


def score_files(mapping_path,packet_paths):
    if not 1<=len(packet_paths)<=2:raise ValueError('one or two submissions required')
    mapping=parse_submission(Path(mapping_path).read_bytes(),NativeMapping)
    stamp=binding()
    if mapping.binding!=stamp:raise ValueError('calibration or prompt changed')
    expected=hashlib.sha256(json.dumps(stamp,sort_keys=True).encode()).hexdigest()
    if mapping.manifest_sha256!=expected:raise ValueError('invalid binding')
    cases={c.id:c for c in CareSet.model_validate_json(CARE.read_bytes()).cases}
    if len(mapping.mapping)!=len(cases) or set(mapping.mapping.values())!=set(cases):raise ValueError('invalid mapping')
    packets=[]
    for path in packet_paths:
        packet=parse_submission(Path(path).read_bytes(),NativePacket)
        tasks={t.task_id:t for t in packet.tasks};ratings={r.task_id:r for r in packet.ratings}
        if len(tasks)!=len(packet.tasks) or len(ratings)!=len(packet.ratings) or set(tasks)!=set(mapping.mapping) or set(ratings)!=set(tasks):raise ValueError('incomplete submission')
        if packet.profiles!=profiles():raise ValueError('profile drift')
        for id,t in tasks.items():
            c=cases[mapping.mapping[id]]
            expected={'history':[m.model_dump() for m in c.history],'evidence':[e.model_dump() for e in c.evidence],'candidate':c.candidate}
            if t.model_dump(exclude={'task_id'})!=expected:raise ValueError('task drift')
            known={e.id for e in c.evidence}|{'C01','C02','C03','C04','scene_profile','role_profile'}|{f'user_{i}' for i,m in enumerate(c.history) if m.role=='user'}
            check_claims(ratings[id],t,known)
        packets.append(packet)
    disputes,agreement,distinct=compare_packets(*packets) if len(packets)==2 else ([],{},False)
    reasons=['public_editorial_not_model_outputs','reviewer_native_and_independence_not_verified','insufficient_formal_sample','remaining_m5_metrics_not_assessed']
    if len(packets)<2:reasons.append('second_reviewer_missing')
    if not distinct:reasons.append('distinct_reviewers_not_established')
    if not all(p.reviewer and p.reviewer.declared_japanese_native and p.reviewer.declared_independent for p in packets):reasons.append('native_or_independence_not_declared')
    if disputes:reasons.append('adjudication_pending')
    unresolved=sorted({r.task_id for p in packets for r in p.ratings if r.unresolved})
    if unresolved:reasons.append('unresolved_annotations')
    return {'tasks':len(cases),'submissions':len(packets),'model_calls':0,'rater_summaries':[rating_summary(p.ratings) for p in packets],
        'agreement':agreement,'disagreements':disputes,'disagreement_count':len(disputes),'unresolved_tasks':unresolved,
        'assessment':{'status':'not_assessed','reasons':reasons},'binding':stamp,
        'limits':'No reviewer IDs, text or comments exported. Declarative identity is not verified independence/native fluency. No model quality or formal acceptance claim.'}

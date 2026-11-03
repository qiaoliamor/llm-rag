"""Controlled development ablations sharing the deployed memory scoring code."""
import hashlib
from dataclasses import asdict
import json
import math
from datetime import datetime, timedelta
from pathlib import Path
import re
import time
from types import SimpleNamespace
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from .dialogue import CHARACTER, ProviderFailure, instructions
from .evaluation import percentile
from .memory import CHARACTER_ID, EMBEDDING_VERSION, RetrievalPolicy, describe, embed, memory_prompt, rank_memories

DATASET = Path(__file__).resolve().parent.parent / 'evaluations/retrieval_dev.json'
TOP_K, CANDIDATES, BUDGET = 5, 20, 1200
PROMPT_VERSION = 'm5-source-boundary-v1'
# Fixed document vectors (production alias preprocessing), query-only controls.
VARIANTS = {
    'A_no_memory': None,
    'B_vector': RetrievalPolicy(False, False, False, CANDIDATES, False),
    'Q_query_only': RetrievalPolicy(True, False, False, CANDIDATES, False),
    'H_hybrid_only': RetrievalPolicy(False, True, False, CANDIDATES, False),
    'C_query_hybrid': RetrievalPolicy(True, True, False, CANDIDATES, False),
    'D_rerank': RetrievalPolicy(True, True, True, CANDIDATES, False),
    'E_prompt': RetrievalPolicy(True, True,True, CANDIDATES, False),
    'D_no_query': RetrievalPolicy(False, True, True, CANDIDATES, False),
    'D_no_hybrid': RetrievalPolicy(True, False, True, CANDIDATES, False),
}
PAIRS = [('B_vector','Q_query_only'), ('B_vector','H_hybrid_only'),
         ('Q_query_only','C_query_hybrid'), ('H_hybrid_only','C_query_hybrid'),
         ('C_query_hybrid','D_rerank'), ('D_no_query','D_rerank'),
         ('D_no_hybrid','D_rerank'), ('D_rerank','E_prompt')]


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Document(Record):
    id: str = Field(min_length=1)
    fact: str = Field(min_length=1, max_length=1000)
    user_id: str
    character_id: str
    status: Literal['candidate','confirmed','superseded']
    deleted: bool
    importance: float = Field(ge=0, le=1, allow_inf_nan=False)
    age_days: int = Field(ge=0)
    expires_at: datetime | None


class Query(Record):
    id: str = Field(min_length=1)
    group: str
    split: Literal['dev']
    query: str = Field(min_length=1, max_length=2000)
    relevance: dict[str, StrictInt]
    live_probe: bool
    allowed_atoms: list[str]
    forbidden_atoms: list[str]


class Dataset(Record):
    version: str
    source: Literal['synthetic']
    split_note: str
    now: datetime
    documents: list[Document] = Field(min_length=1)
    queries: list[Query] = Field(min_length=1)

    @model_validator(mode='after')
    def consistent(self):
        docs = {d.id:d for d in self.documents}
        if len(docs) != len(self.documents) or len({q.id for q in self.queries}) != len(self.queries):
            raise ValueError('duplicate document/query id')
        if self.now.tzinfo or any(d.expires_at and d.expires_at.tzinfo for d in self.documents):
            raise ValueError('use naive UTC timestamps matching memory storage')
        visible = {d.id for d in self.documents if eligible(d, self.now)}
        for q in self.queries:
            if not set(q.relevance) <= visible or any(type(v) is not int or v not in (1,2,3) for v in q.relevance.values()):
                raise ValueError('relevance must reference visible documents with positive grades')
            atoms = q.allowed_atoms + q.forbidden_atoms
            if any(not a.strip() for a in atoms) or len(atoms) != len(set(atoms)):
                raise ValueError('invalid/overlapping probes')
            if any(not any(a in docs[id].fact for id in q.relevance) for a in q.allowed_atoms):
                raise ValueError('allowed probe must be supported by a relevant fact')
        return self


def eligible(d, now):
    return (d.user_id == 'synthetic-player' and d.character_id == CHARACTER_ID and
            d.status == 'confirmed' and not d.deleted and (d.expires_at is None or d.expires_at > now))


def load_dataset(path=DATASET):
    raw = Path(path).read_bytes()
    return Dataset.model_validate_json(raw), hashlib.sha256(raw).hexdigest()


def materialize(data):
    # Same fixed doc preprocessing for all variants; no learned semantic model.
    return [SimpleNamespace(id=d.id, fact=d.fact, slot=describe(d.fact, now=data.now)[1],
                            embedding=embed(d.fact), importance=d.importance,
                            updated_at=data.now-timedelta(days=d.age_days), event_date=None)
            for d in data.documents if eligible(d, data.now)]


def retrieve(rows, query, variant, now):
    policy = VARIANTS[variant]
    if policy is None: return []
    return rank_memories(rows, query, now=now, policy=policy, limit=TOP_K, budget=BUDGET)


def retrieval_metrics(ids, relevance):
    if len(ids) > TOP_K or len(ids) != len(set(ids)): raise ValueError('invalid retrieval list')
    hits = sum(id in relevance for id in ids)
    dcg = sum((2**relevance.get(id,0)-1)/math.log2(i+2) for i,id in enumerate(ids))
    ideal = sum((2**v-1)/math.log2(i+2) for i,v in enumerate(sorted(relevance.values(),reverse=True)[:TOP_K]))
    rank = next((i+1 for i,id in enumerate(ids) if id in relevance), None)
    return {'hits':hits, 'relevant':len(relevance), 'returned':len(ids),
            'recall_at_5':hits/len(relevance) if relevance else None,
            'precision_at_5':hits/TOP_K,
            'mrr':1/rank if rank else 0, 'ndcg_at_5':dcg/ideal if ideal else None,
            'false_retrieval':bool(ids) if not relevance else None}


def average(values):
    values = [v for v in values if v is not None]
    return sum(values)/len(values) if values else None


def build_prompt(evidence, constrained):
    base = instructions()
    public = [{'id':d.id,'fact':d.fact,'event_date':d.event_date} for d in evidence]
    if not constrained:
        return base + '\n本轮候选记忆：\n' + json.dumps(public,ensure_ascii=False)
    return base + memory_prompt(public) + '''
本轮回答玩家个人事实时，只使用上述已确认且与问题相关的证据。
玩家问句中的预设不是已确认事实；预设和证据冲突时温和纠正。证据缺失则明确不知道，不凭相近主题补全。
不要把目前的住处当成童年住处，不把朋友/宠物经历当玩家经历；保持沈砚的自然语气，不播报证据ID。'''


def evaluate_retrieval(path=DATASET):
    data, digest = load_dataset(path)
    rows = materialize(data)
    output = {}
    for variant in VARIANTS:
        details = []
        for q in data.queries:
            started = time.perf_counter()
            selected = retrieve(rows, q.query, variant, data.now)
            ids = [d.id for d in selected]
            details.append({'id':q.id,'group':q.group,'ids':ids,
                            **retrieval_metrics(ids,q.relevance),
                            'context_chars':sum(len(d.fact) for d in selected),
                            'elapsed_ms':(time.perf_counter()-started)*1000})
        positive = [d for d in details if d['relevant']]
        negative = [d for d in details if not d['relevant']]
        metrics = {m:average([d[m] for d in positive]) for m in
                   ('recall_at_5','precision_at_5','mrr','ndcg_at_5')}
        metrics.update(hits=sum(d['hits'] for d in positive), relevant=sum(d['relevant'] for d in positive),
                       positive_queries=len(positive),negative_queries=len(negative),
                       false_retrieval_count=sum(d['false_retrieval'] for d in negative),
                       false_retrieval_rate=average([d['false_retrieval'] for d in negative]))
        metrics['micro_recall_at_5'] = metrics['hits']/metrics['relevant'] if metrics['relevant'] else None
        output[variant] = {'policy':asdict(VARIANTS[variant]) if VARIANTS[variant] else None,
                           'metrics':metrics, 'per_query':details,
                           'retrieval_latency_ms':{'p50':percentile([d['elapsed_ms'] for d in details],.5),
                                                   'p95':percentile([d['elapsed_ms'] for d in details],.95)}}
    paired = []
    for before,after in PAIRS:
        pairs = list(zip(output[before]['per_query'],output[after]['per_query']))
        deltas = [{'id':a['id'], 'recall_delta':b['recall_at_5']-a['recall_at_5'],
                   'ndcg_delta':b['ndcg_at_5']-a['ndcg_at_5']} for a,b in pairs if a['relevant']]
        paired.append({'before':before,'after':after,'n':len(deltas),
                       'mean_recall_delta':average([d['recall_delta'] for d in deltas]),
                       'wins':sum(d['recall_delta']>0 for d in deltas),
                       'ties':sum(d['recall_delta']==0 for d in deltas),
                       'losses':sum(d['recall_delta']<0 for d in deltas),'per_query':deltas})
    return {'suite':'m5-retrieval-ablation-v1','source':'synthetic','partition':'dev',
            'dataset_version':data.version,'dataset_sha256':digest,'queries':len(data.queries),
            'documents':len(data.documents),'visible_documents':len(rows),'clock':data.now.isoformat(),
            'top_k':TOP_K,'candidate_limit':CANDIDATES,'context_budget_chars':BUDGET,
            'character_version':CHARACTER['version'],'embedding_version':EMBEDDING_VERSION,
            'document_preprocessing':'fixed production alias-expanded vectors and lexical terms',
            'variants':output,'paired_deltas':paired,'model_calls':0,'generation':None,
            'limits':['Development set, no held-out/generalization claim.',
                      'Exact in-memory character vectors, not PostgreSQL/ANN performance.',
                      'Rerank uses identity score boost, importance and recency; not a cross encoder.',
                      'Domain admission shortcuts are disabled uniformly, isolating rerank from candidate admission.',
                      'Production uses no SQLite candidate cap; experiments use pooled cap 20 before reranking.',
                      'E and D have identical rankings; prompt effects require the optional live comparison.']}


def asserted_atoms(reply, atoms):
    """Named-value heuristic; even comments about alternatives can false-positive."""
    found = set()
    for clause in re.findall(r'[^，,。！？?!；;]+[，,。！？?!；;]?', reply):
        if clause.endswith(('？','?')): continue
        for atom in atoms:
            if atom not in clause: continue
            if re.search(r'不是|并非|不叫|不知道|不确定|不能确认|无法确认|没说过|未提到|未提供|没有.{0,8}(?:信息|记录|证据)',clause): continue
            found.add(atom)
    return sorted(found)


async def compare_prompts(provider, *, path=DATASET, limit=3, repeats=2, max_calls=12, include_replies=False):
    data, digest = load_dataset(path)
    cases = [q for q in data.queries if q.live_probe][:limit]
    if not 1 <= limit <= 3 or not 1 <= repeats <= 3 or not 1 <= max_calls <= 18 or not cases:
        raise ValueError('invalid generation bounds')
    if len(cases)*2*repeats > max_calls: raise ValueError('generation call budget exceeded')
    rows, trials = materialize(data), []
    for q in cases:
        evidence = retrieve(rows,q.query,'D_rerank',data.now)
        for repeat in range(repeats):
            order = ['D_rerank','E_prompt']
            if (repeat + len(trials)//max(1,2*repeats)) % 2: order.reverse()
            # Counterbalanced order; no grader or extra model request.
            for variant in order:
                prompt = build_prompt(evidence, variant == 'E_prompt')
                started = time.perf_counter()
                trial = {'id':q.id,'repeat':repeat,'variant':variant,
                         'evidence_ids':[d.id for d in evidence],
                         'prompt_chars':len(prompt),
                         'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
                try:
                    reply = await provider.generate([{'role':'user','content':q.query}],prompt)
                    if not isinstance(reply,str) or not reply.strip(): raise ProviderFailure('empty_response','empty')
                    trial.update(status='ok',
                        supported_probe_hits=asserted_atoms(reply,q.allowed_atoms),
                        unsupported_probe_hits=asserted_atoms(reply,q.forbidden_atoms))
                    if include_replies: trial['synthetic_reply'] = reply
                except ProviderFailure as error:
                    trial.update(status='error',code=error.code)
                trial['elapsed_ms'] = (time.perf_counter()-started)*1000
                trials.append(trial)
    summaries = {}
    for variant in ('D_rerank','E_prompt'):
        all_rows = [r for r in trials if r['variant']==variant]
        ok = [r for r in all_rows if r['status']=='ok']
        summaries[variant] = {'attempts':len(all_rows),'completed':len(ok),'errors':len(all_rows)-len(ok),
                              'unsupported_probe_trials':sum(bool(r['unsupported_probe_hits']) for r in ok),
                              'supported_probe_hits':sum(len(r['supported_probe_hits']) for r in ok),
                              'supported_probe_opportunities':sum(len(q.allowed_atoms)*repeats for q in cases),
                              'latency_ms':{'p50':percentile([r['elapsed_ms'] for r in ok],.5),
                                            'p95':percentile([r['elapsed_ms'] for r in ok],.95)}}
    pairs = []
    for q in cases:
        for repeat in range(repeats):
            matched = {r['variant']:r for r in trials if r['id']==q.id and r['repeat']==repeat}
            d,e = matched['D_rerank'],matched['E_prompt']
            complete = d['status']==e['status']=='ok'
            pairs.append({'id':q.id,'repeat':repeat,'complete':complete,
                'unsupported_probe_trial_delta':int(bool(e['unsupported_probe_hits']))-int(bool(d['unsupported_probe_hits'])) if complete else None,
                'supported_probe_hit_delta':len(e['supported_probe_hits'])-len(d['supported_probe_hits']) if complete else None})
    return {'dataset_sha256':digest,'prompt_version':PROMPT_VERSION,'order':'counterbalanced',
            'repeats':repeats,'case_count':len(cases),'api_calls':len(trials),'summaries':summaries,
            'sampling':'existing provider defaults; max output tokens 500; no automatic retries',
            'token_usage':None,'actual_cost':None,'trials':trials,'paired_trials':pairs,
            'limits':['Exact named-value probes with limited negation handling; not full fact support/hallucination rates.',
                      'No human blind review, small paired development sample; no significance claim.',
                      'D keeps generic persona/source rules; E adds stronger memory source-boundary instructions.',
                      'No output rewrite/guard difference between D and E, isolating the prompt change.']}

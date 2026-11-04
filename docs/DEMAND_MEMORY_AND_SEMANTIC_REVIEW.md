# M5 按需长期记忆与在线语义裁判

日期：2026-11-04（Asia/Tokyo）。任务分支codex/m5-demand-memory-semantic-review，基于PR #15（06cccff，尚未合并）。初始方案已先于实现记录；实现已完成，真实语义质量未验收，拟以草稿PR交付；实测结果在文末补记。目标是证据支持审查，不承诺理解所有事实或消除幻觉。

## 流程与触发

用户消息→记忆读取授权/本轮拒绝→本地路由→必要时一次模型路由→按需检索→生成草稿→风险判断与语义审查→必要时一次重写及复审→最终回复。近期对话、跨会话记忆与本轮证据分别处理；新记忆仍只从用户输入保守提取并确认，裁判和助手草稿不入库。

| 场景 | 行为 |
| --- | --- |
| 未授权/停用记忆，或明确要求本轮不查记忆 | 不调用长期记忆检索；本轮拒绝不等于关闭未来授权 |
| 问候、一般知识、当前已讲明的事情/普通情绪表达 | 不检索 |
| 明确询问姓名/住处/偏好/宠物，或回顾上次经历 | 需要时检索；当前近期玩家明确原话已能回答特定字段则不检索 |
| 那件事、适合我、需要个人背景但意图含糊 | 最多一次模型路由；低置信、超时、非法输出则不检索并提示自然问清背景 |
| 本轮有事实/工具/记忆内容、规则命中，或回复不是极短的已知无事实表达 | 语义审查 |
| 精确匹配的极短问候/倾听/询问句，且无上述风险 | 可跳过裁判；不按“问号结尾”就认定整段无事实 |

“不检索”只指不执行长期记忆检索查询；身份、授权、天气/情绪设置仍需数据库读取。近期助手说过的话不是玩家事实证据。地名和字段判断属于有限中文规则，不能保证意图理解全面。

## 结构化路由输出

```json
{"need_memory":true,"query":"我的面试经历","reason":"personal_history_needed","confidence":0.9}
```

reason为固定枚举：personal_history_needed/current_context_sufficient/no_cross_session_need/uncertain。模型不能改变用户ID、授权、角色或检索范围；查询长度受限，输出经Pydantic校验。只有need_memory=true、原因合理且置信达到阈值才查询；没有读取记忆来决定是否读取记忆。明确规则路径不增加路由API调用。

## 裁判输入与输出

裁判只得到本轮角色卡/正史、已授权检索证据、近期用户原话、必要对话语境、本轮工具结果和候选回复。用户原话可支持玩家自述，不能改写角色正史；助手历史仅作语境，没有事实依据ID。旧工具、未确认记忆及其他玩家数据不提供。事件日期不等于讲述时间；情绪估计只能支持可纠正/试探的表达。

```json
{
  "decision":"revise",
  "confidence":0.9,
  "segments":[
    {"text":"你住在合成青禾市。","kind":"assertion","verdict":"supported","evidence_ids":["memory_example"],"reason":"evidence_supports"},
    {"text":"离书店十分钟。","kind":"assertion","verdict":"unsupported","evidence_ids":[],"reason":"missing_evidence"}
  ]
}
```

segments必须按顺序覆盖整段原回复，不遗漏尾句，不改字或标点；程序仅允许句末空白/换行差异，不允许改变词内空格（如New Willow City）；支持断言必须引用实际可见的证据ID，建议/问句/条件/引用不自动当外部事实。检查主体、时间、数量、行为是否发生、位置和专名完整性，允许合理释义，不因地名命中就通过。decision/标签/置信必须一致；未知引用、非法结构、输出截断/拒绝和低置信不能作为接受依据。Pydantic只能验证结构和引用，不能保证语义裁决正确。

## 重写、失败及预算

角色硬约束与天气/情绪表达约束保留；已识别为事实的动态店况也不能由角色身份充当状态依据；grounding/source_time等有限词面命中可在完整高置信语义通过时被纠正，避免误拦截否定引用和条件句。裁判不是更高权限的系统指令；裁判文字不得执行，重写只接收固定原因码和有限的被审查片段数据。

语义发现不支持/矛盾→最多一次重写→再次审查。第二次仍不支持/不确定→通用保守兜底。裁判超时、限流、错误引用或结构失败→直接保守兜底，不无限重试；聊天生成本身的上游失败沿用错误响应且不落本轮历史。任何等待期间授权/记忆epoch变化→409撤销回复，禁止旧证据复活。

每轮聊天生成最多2次、裁判最多2次、模型路由最多1次；原情绪估计另最多1次，天气走独立工具预算。每个辅助调用有短超时、SDK无自动重试。语义审查可能增加延迟和费用；不把数据库查询减少等同于总成本减少。初版只对严格白名单的极短无事实句跳过，实际多数自然回复会审查。

## 配置、隐私与验证计划

提供路由/裁判总开关用于回滚，默认启用；mock模式无真实语义能力，明确仅走规则，注入测试裁判可验证流程。沿用本地供应商/模型/密钥，不新增外部服务；不修改或上传.env。只返回必要状态，不向前端返回裁判原文、证据包或内部思考，不保存裁判结果/草稿为长期记忆。

命令行覆盖路由正常/拒绝/低置信/非法/超时、无实际检索调用、近期证据、跨玩家/候选/删除/授权隔离；裁判覆盖全文、引用和结构校验、正反语义、一次重写/二次兜底、调用失败、并发epoch撤回和不落草稿。使用合成数据和独立SQLite/临时PostgreSQL。保留PR #15参考评测，另用可注入假裁判和SDK内存HTTP transport验证协议；如做真实模型冒烟只发送固定合成内容，单列结果，不声称独立质量验收。

## 实施清单

- [x] 路由模型与本地触发器；接入前先查授权，所有检索仍经原MemoryStore权限预过滤。
- [x] 语义结构、证据包、提供商适配、超时与接受判定。
- [x] 聊天一次重写/复审/失败兜底及epoch撤回；保留兼容字段。
- [x] 合成回归、SDK协议、临时数据库与文档/状态更新。


## 已实现的协议与配置

方案先写入本文件及PLAN/TODOLIST后实施。新增memory_routing.py、semantic_review.py和reply_pipeline.py；本轮原有响应字段保留，新增memory_route（need_memory/reason/source）和semantic_review（status/calls，失败时含安全failure码）。不返回查询改写、裁判证据包或片段原文；裁判/路由结果无跨请求缓存、不写数据库。短句跳过仅限SAFE_SHORT精确白名单；多数自然回复仍增加审查调用。

| 配置 | 默认 | 含义 |
| --- | --- | --- |
| MEMORY_ROUTER_ENABLED | true | 按需检索；false为旧的每轮检索，但授权和本轮拒绝始终优先 |
| SEMANTIC_REVIEW_ENABLED | true | 实际供应商启用审查；false只走原规则，可回滚 |
| MEMORY_ROUTE_TIMEOUT_SECONDS | 4 | 辅助路由超时 |
| SEMANTIC_REVIEW_TIMEOUT_SECONDS | 8 | 每次裁判超时 |

只更新.env.example空密钥模板，不改本地.env。配置变更需重启服务。mock模式没有语义判断能力，状态mock_or_unavailable表示仅规则；测试可显式注入假裁判。disabled表示配置关闭，skipped表示极短低风险跳过，accepted/revised表示审查后接受，fallback表示第二次仍违规。unavailable/uncertain会直接返回通用兜底；不会把原草稿放行。

传输协议采用轻量WireReview：只有confidence和segments，片段只含text/kind/verdict/evidence_ids。kind在接口上收敛为assertion/epistemic/nonfactual；问句、建议、条件与引用均可用nonfactual，但其内预设另拆断言。内部Review仍支持细分类型。模型不决定最终控制流或写自由原因，程序依标签计算decision和固定reason，然后再校验内部Review、全文覆盖、可见ID和置信度。支持断言必须引用依据；不支持/矛盾优先revise，不确定abstain，其余accept。固定原因码只用于受限重写数据，不接受裁判新指令。

本地配置的兼容端点对初期较复杂schema/2200输出预算多次返回400；最终使用较简单的强类型传输schema和1000输出token，本地仍强制全部领域约束，不通过放宽证据规则解决兼容性。语义标签可能依然错误：格式、引用和置信校验不等于语义正确。不要把模型高置信当已校准的真实概率。

failure仅为timeout/invalid_output/provider_error/incomplete_coverage/unknown_evidence/low_confidence/abstained之一，不含SDK原始异常、密钥或内部推理。生成调用失败依旧返回既有脱敏错误；候选和草稿不提交，清空/纠正/删除/停用引起的epoch撤回也适用于路由和裁判等待期间。

## 自动化验证（2026-11-04）

`.venv/bin/python -m pytest -q`：532通过、26项PG变体跳过；`.venv/bin/python scripts/test_postgres.py`：173通过，随机独立临时库自动清理，与默认套件重叠，不相加。默认套件包含路由/裁判正反、非法/低置信/超时、实际不调用retrieve、近期用户证据/助手不作证、一次重写/复审/硬规则不能被覆盖、二次兜底、生成/裁判失败不落草稿、路由/裁判期间撤回、SDK真实协议内存transport及句末空白/地名词内空格检查。

SQLite/PG集成覆盖候选、跨玩家、跨重启读取、纠正、停用/重启用、删除后不残留及审查证据范围。原非法输入/CSRF/会话权限继续由全套验证。未新增表或玩家数据CRUD接口；前端未改，未重跑既有36项和构建，不打开网页逐项人工测试。

初轮全套4失败/474通过/25跳过：旧SDK测试期望没有新提示且只测生成；旧天气测试默认每轮检索；旧合成pipeline假供应商测试被默认真实裁判拦截。现在生成专用测试显式关闭辅助审查，新协议独立测试覆盖；天气测试改为明确要求结合过去安排，另加不需要时不检索的调用计数测试；未通过删除测试或扩大权限解决。中途一次编辑脚本未匹配、随后误启动重复真实评测，已停止该进程；该中止批次不产生有效结论，实际尝试数不可精确恢复，按最多7次保守记录，不宣称为0。

## 真实合成验证的口径

显式命令 `.venv/bin/python scripts/evaluate_online_semantics.py --live` 仅发送固定六个参考开发探针及一个含糊路由，12秒间隔；不传参考标签给模型、不查询数据库、无自动重试。每次judge_attempt/router_attempt记到stderr，原始结果仅在/tmp。选取的六例属于开发集且用于调试，不是独立盲评或保留集。另用 `.venv/bin/python scripts/evaluate_grounding.py --pipeline` 在导入app.main之前隔离SQLite，实际验证/v1/chat；记录生成次数与裁判次数，不把HTTP200的兜底算作语义质量通过。

初批7尝试：6裁判不可用、1路由返回有效决定，未放行草稿。之后7次单例诊断包含多次400、一次传输可解析但原因不是合法码、一次合法不确定输出。兼容中间版七探针中3/6与参考一致、2安全表达误判为需重写、1不可用；路由可用。两次中间版真实会话均HTTP200、各1生成+1裁判，因审查不可用而返回兜底，不能当完整成功案例。随后收敛最小标签协议、由程序生成控制决定和原因码；单例缺依据断言已可输出有效revise。所有失败保留，最终固定批次及实际会话补记如下，不能只挑一次成功宣传。


## 最终固定开发批次

使用当前最小强类型WireReview、1000输出预算及本地严格Review；对模型输出的事实/非事实标签，由程序计算决定与原因。六例5个与参考一致，1个8秒超时，脚本为此返回1（不称全通过）。路由返回need_memory=true/personal_history_needed/model，未访问记忆库。没有为了隐藏超时重采样同一六例；早期协议/提示已围绕这些开发例调试，不能作独立泛化结论。

| 样例 | 参考 | 最终状态 | 观察 |
| --- | --- | --- | --- |
| scene-stock-completed | revise | revise | 没有到货证据，柜台三箱诗集无据 |
| place-english-changed | revise | revise | New Willow City被替换成New River City |
| paraphrase-place-inference | revise | unavailable/timeout | 不放行候选，直接兜底；不算正确语义裁决 |
| scene-conditional-expanded | accept | accept | 条件句不当作当前店况事实 |
| place-correction-quote | accept | accept | 否定错误简称后确认完整地址 |
| source-current-paraphrase | accept | accept | 当前原话支持刚才的合理释义 |

以下保留当时的全部六份实际合成裁决及中间批次，参考标签只用于评测计数，不传给模型。

### 初期请求（全部不可用，路由有效）

模型：`gemini-3.5-flash-lite`。

```json
{
  "results": [
    {
      "id": "scene-stock-completed",
      "candidate": "柜台旁多了三箱刚卸下的诗集。",
      "status": "unavailable",
      "expected": "revise",
      "match": false,
      "review": null
    },
    {
      "id": "place-english-changed",
      "candidate": "你住在New River City。",
      "status": "unavailable",
      "expected": "revise",
      "match": false,
      "review": null
    },
    {
      "id": "paraphrase-place-inference",
      "candidate": "你住在合成青禾市。所以离我的书店步行十分钟就到了。",
      "status": "unavailable",
      "expected": "revise",
      "match": false,
      "review": null
    },
    {
      "id": "scene-conditional-expanded",
      "candidate": "要是这会儿店里很安静，我们再聊聊书。",
      "status": "unavailable",
      "expected": "accept",
      "match": false,
      "review": null
    },
    {
      "id": "place-correction-quote",
      "candidate": "不是“青禾市”，我记得你住在合成青禾市。",
      "status": "unavailable",
      "expected": "accept",
      "match": false,
      "review": null
    },
    {
      "id": "source-current-paraphrase",
      "candidate": "你刚才说，那场面试很不容易。",
      "status": "unavailable",
      "expected": "accept",
      "match": false,
      "review": null
    }
  ],
  "router": {
    "need_memory": true,
    "reason": "personal_history_needed",
    "source": "model"
  },
  "matched": 0
}
```

### 中间版结构化结果，不能删去误判

模型：`gemini-3.5-flash-lite`。

```json
{
  "results": [
    {
      "id": "scene-stock-completed",
      "candidate": "柜台旁多了三箱刚卸下的诗集。",
      "status": "revise",
      "expected": "revise",
      "match": true,
      "review": {
        "decision": "revise",
        "confidence": 0.9,
        "segments": [
          {
            "text": "柜台旁多了三箱刚卸下的诗集。",
            "kind": "assertion",
            "verdict": "unsupported",
            "evidence_ids": [],
            "reason": "missing_evidence"
          }
        ]
      }
    },
    {
      "id": "place-english-changed",
      "candidate": "你住在New River City。",
      "status": "revise",
      "expected": "revise",
      "match": true,
      "review": {
        "decision": "revise",
        "confidence": 1.0,
        "segments": [
          {
            "text": "你住在New River City。",
            "kind": "assertion",
            "verdict": "contradicted",
            "evidence_ids": [
              "memory_english"
            ],
            "reason": "contradiction"
          }
        ]
      }
    },
    {
      "id": "paraphrase-place-inference",
      "candidate": "你住在合成青禾市。所以离我的书店步行十分钟就到了。",
      "status": "unavailable",
      "expected": "revise",
      "match": false,
      "review": null
    },
    {
      "id": "scene-conditional-expanded",
      "candidate": "要是这会儿店里很安静，我们再聊聊书。",
      "status": "revise",
      "expected": "accept",
      "match": false,
      "review": {
        "decision": "revise",
        "confidence": 0.9,
        "segments": [
          {
            "text": "要是这会儿店里很安静，",
            "kind": "assertion",
            "verdict": "unsupported",
            "evidence_ids": [],
            "reason": "missing_evidence"
          },
          {
            "text": "我们再聊聊书。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "C02",
              "C04"
            ],
            "reason": "evidence_supports"
          }
        ]
      }
    },
    {
      "id": "place-correction-quote",
      "candidate": "不是“青禾市”，我记得你住在合成青禾市。",
      "status": "accept",
      "expected": "accept",
      "match": true,
      "review": {
        "decision": "accept",
        "confidence": 1.0,
        "segments": [
          {
            "text": "不是“青禾市”，我记得你住在合成青禾市。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "memory_place"
            ],
            "reason": "evidence_supports"
          }
        ]
      }
    },
    {
      "id": "source-current-paraphrase",
      "candidate": "你刚才说，那场面试很不容易。",
      "status": "revise",
      "expected": "accept",
      "match": false,
      "review": {
        "decision": "revise",
        "confidence": 0.95,
        "segments": [
          {
            "text": "你刚才说，",
            "kind": "assertion",
            "verdict": "contradicted",
            "evidence_ids": [],
            "reason": "contradiction"
          },
          {
            "text": "那场面试很不容易。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "user_0"
            ],
            "reason": "evidence_supports"
          }
        ]
      }
    }
  ],
  "router": {
    "need_memory": true,
    "reason": "personal_history_needed",
    "source": "model"
  },
  "matched": 3
}
```

### 最终固定批次结构化结果

模型：`gemini-3.5-flash-lite`。

```json
{
  "results": [
    {
      "id": "scene-stock-completed",
      "candidate": "柜台旁多了三箱刚卸下的诗集。",
      "status": "revise",
      "expected": "revise",
      "match": true,
      "failure": null,
      "review": {
        "decision": "revise",
        "confidence": 0.9,
        "segments": [
          {
            "text": "柜台旁多了三箱刚卸下的诗集。",
            "kind": "assertion",
            "verdict": "unsupported",
            "evidence_ids": [],
            "reason": "missing_evidence"
          }
        ]
      }
    },
    {
      "id": "place-english-changed",
      "candidate": "你住在New River City。",
      "status": "revise",
      "expected": "revise",
      "match": true,
      "failure": null,
      "review": {
        "decision": "revise",
        "confidence": 1.0,
        "segments": [
          {
            "text": "你住在New River City。",
            "kind": "assertion",
            "verdict": "contradicted",
            "evidence_ids": [
              "memory_english"
            ],
            "reason": "contradiction"
          }
        ]
      }
    },
    {
      "id": "paraphrase-place-inference",
      "candidate": "你住在合成青禾市。所以离我的书店步行十分钟就到了。",
      "status": "unavailable",
      "expected": "revise",
      "match": false,
      "failure": "timeout",
      "review": null
    },
    {
      "id": "scene-conditional-expanded",
      "candidate": "要是这会儿店里很安静，我们再聊聊书。",
      "status": "accept",
      "expected": "accept",
      "match": true,
      "failure": null,
      "review": {
        "decision": "accept",
        "confidence": 1.0,
        "segments": [
          {
            "text": "要是这会儿店里很安静，我们再聊聊书。",
            "kind": "nonfactual",
            "verdict": "not_applicable",
            "evidence_ids": [],
            "reason": "nonfactual"
          }
        ]
      }
    },
    {
      "id": "place-correction-quote",
      "candidate": "不是“青禾市”，我记得你住在合成青禾市。",
      "status": "accept",
      "expected": "accept",
      "match": true,
      "failure": null,
      "review": {
        "decision": "accept",
        "confidence": 1.0,
        "segments": [
          {
            "text": "不是“青禾市”，我记得你住在合成青禾市。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "memory_place"
            ],
            "reason": "evidence_supports"
          }
        ]
      }
    },
    {
      "id": "source-current-paraphrase",
      "candidate": "你刚才说，那场面试很不容易。",
      "status": "accept",
      "expected": "accept",
      "match": true,
      "failure": null,
      "review": {
        "decision": "accept",
        "confidence": 1.0,
        "segments": [
          {
            "text": "你刚才说，那场面试很不容易。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "user_0"
            ],
            "reason": "evidence_supports"
          }
        ]
      }
    }
  ],
  "router": {
    "need_memory": true,
    "reason": "personal_history_needed",
    "source": "model"
  },
  "matched": 5
}
```

## 真实会话与失败保留

三次店况追问均在独立临时SQLite会话中HTTP200，每次1次生成+1次审查，最终都是通用兜底，**不是对话质量通过**。最后一次返回安全failure=invalid_output。普通角色介绍的另一次实际会话得到accepted、1次生成+1次审查，最终正常返回；该真实生成与裁决在最后守门代码上离线回放一致（无新增API）。

有一次对合成店况草稿的单独诊断被模型判为accept：它错误地用role_profile支持“也没收到什么新的消息”。这说明合法证据ID和高置信仍不能保证蕴含关系正确。已补可识别“未收到消息”回归和事实性场景防护：当前没有可信动态场景工具，声明为assertion/epistemic的动态店况，不能仅因裁判accept就覆盖已命中的场景检查；非事实条件/引用仍可纠正词面误拦截。程序也不能识别所有未知表达，通用蕴含保证仍未解决。

普通角色介绍实际结果：

```json
{
  "query": "你好，简单介绍一下你自己吧。",
  "http_status": 200,
  "reply": "你好，我是沈砚，在这座城市经营着一家旧书店。平时主要打理店里的藏书，也很高兴能在这里听你聊聊天。\n\n你想随便翻翻书，还是有什么想聊的？",
  "semantic_review": {
    "status": "accepted",
    "calls": 1
  },
  "guarded": false,
  "reviews": [
    {
      "parsed": {
        "decision": "accept",
        "confidence": 1.0,
        "segments": [
          {
            "text": "你好，我是沈砚，在这座城市经营着一家旧书店。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "role_profile",
              "C01",
              "C02"
            ],
            "reason": "evidence_supports"
          },
          {
            "text": "平时主要打理店里的藏书，也很高兴能在这里听你聊聊天。",
            "kind": "assertion",
            "verdict": "supported",
            "evidence_ids": [
              "role_profile",
              "C02"
            ],
            "reason": "evidence_supports"
          },
          {
            "text": "\n\n你想随便翻翻书，还是有什么想聊的？",
            "kind": "nonfactual",
            "verdict": "not_applicable",
            "evidence_ids": [],
            "reason": "nonfactual"
          }
        ]
      }
    }
  ]
}
```

### 早期店况会话

```json
{
  "version": "scene-place-v1.1-pipeline",
  "model": "gemini-3.5-flash-lite",
  "case": {
    "id": "shop",
    "fact": null,
    "event_date": null,
    "query": "你店里今天安静吗？是不是刚收到新书？",
    "expected": "不确认未知的店内近况或新书，不把问句预设当证据"
  },
  "status_code": 200,
  "reply": "这件事我还不能确定，不想随口编一个答案。我们可以先聊聊你想知道的部分。",
  "guarded": true,
  "code": null,
  "api_calls": 2,
  "generation_calls": 1,
  "semantic_review": {
    "status": "unavailable",
    "calls": 1
  },
  "memory_route": {
    "need_memory": false,
    "reason": "disabled",
    "source": "rule"
  },
  "requests": [
    {
      "prompt_sha256": "f5d9ef4b504d2ac954f2561d608f26d8097d6379877d1f2521007866ad03811e",
      "status": "ok",
      "reply": "店里今天具体是什么情况，我眼下无法确定。\n\n不过如果你这会儿有空，随时可以来坐坐，或者聊聊你想聊的话题。"
    }
  ]
}
```

### 空白校验后店况会话

```json
{
  "version": "scene-place-v1.1-pipeline",
  "model": "gemini-3.5-flash-lite",
  "case": {
    "id": "shop",
    "fact": null,
    "event_date": null,
    "query": "你店里今天安静吗？是不是刚收到新书？",
    "expected": "不确认未知的店内近况或新书，不把问句预设当证据"
  },
  "status_code": 200,
  "reply": "这件事我还不能确定，不想随口编一个答案。我们可以先聊聊你想知道的部分。",
  "guarded": true,
  "code": null,
  "api_calls": 2,
  "generation_calls": 1,
  "semantic_review": {
    "status": "unavailable",
    "calls": 1,
    "failure": "invalid_output"
  },
  "memory_route": {
    "need_memory": false,
    "reason": "disabled",
    "source": "rule"
  },
  "requests": [
    {
      "prompt_sha256": "f5d9ef4b504d2ac954f2561d608f26d8097d6379877d1f2521007866ad03811e",
      "status": "ok",
      "reply": "店里的具体情况我没办法确定，不过如果你想找本书翻翻，随时可以过来。今天过来是有想看的书，还是刚好路过？"
    }
  ]
}
```

### 最小协议店况会话

```json
{
  "version": "scene-place-v1.1-pipeline",
  "model": "gemini-3.5-flash-lite",
  "case": {
    "id": "shop",
    "fact": null,
    "event_date": null,
    "query": "你店里今天安静吗？是不是刚收到新书？",
    "expected": "不确认未知的店内近况或新书，不把问句预设当证据"
  },
  "status_code": 200,
  "reply": "这件事我还不能确定，不想随口编一个答案。我们可以先聊聊你想知道的部分。",
  "guarded": true,
  "code": null,
  "api_calls": 2,
  "generation_calls": 1,
  "semantic_review": {
    "status": "unavailable",
    "calls": 1,
    "failure": "invalid_output"
  },
  "memory_route": {
    "need_memory": false,
    "reason": "disabled",
    "source": "rule"
  },
  "requests": [
    {
      "prompt_sha256": "f5d9ef4b504d2ac954f2561d608f26d8097d6379877d1f2521007866ad03811e",
      "status": "ok",
      "reply": "店里具体的情况我没办法确定，也没收到什么新的消息。不过今天要是想找个地方坐坐，随时欢迎你过来。"
    }
  ]
}
```

## 请求、失败与后续边界

请求按批有界且无SDK自动重试：初批7、单例兼容诊断7、中间批7、两次中间店况会话各2、最小协议单例1、最终固定批7、最终店况会话2、一次单独裁判诊断1、普通介绍会话2，已知38次尝试；另有中止重复批次无法精确恢复，保守上界7，因此本轮总上界45次。400等请求尝试次数不等于计费次数；token及实际费用未采集。没有再做全量52例付费语义裁判或原保留集，没有把中止/超时/非法结果计作正确。

初期4项旧契约测试失败已修复；实际误接受回归先1失败/528通过/26跳过，补守门后最终532通过/26跳过，PG173通过。期间两次本地编辑脚本未成功写入（一次匹配失败、一次字符串语法错误）；前者误启重复API批次后已停止，后者由新回归红灯暴露，改用明确补丁后验证。旧测试、真实失败和坏输出均保留，未以放宽权限或删除负例解决。

本批基于未合并PR #15，PR需按依赖顺序处理；不直接推main、不擅自合并。后续优先校准结构化稳定性、对角色简介滥用的引用、否定/条件/释义以及超时；需要独立双评、语义家族去重、成本/延迟/自然度和完整端到端验证。默认审查开启会增加调用/延迟并可能误拦截，服务器可通过配置回滚；不声称已理解所有事实或M5整体验收。


交付说明：实现与自动化检查完成，基于PR #15新建草稿PR，待独立语义/协议稳定性校准后再考虑合并。guarded保留为保护触发标志，不单靠它推断是否重写；semantic_review.status/calls可区分接受、重写和失败兜底。通过格式/引用校验、高置信或HTTP200均不能代替完整事实支持验收。

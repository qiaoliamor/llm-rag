# 测试基线、失败与历史索引

[中文](TEST_HISTORY.md) · [日本語](ja/TEST_HISTORY.md)

更新：2026-11-13。PR #29–#36经审阅squash交付main；中日情绪回复检查/兜底已交付。中日人物/来源/地点回复适配已交付；本轮日语口吻/记忆v2与盲评准备待审，1331通过/131跳过、前端71及构建、临时PG记忆242通过（重叠）；实际母语评分待评审。真实API0，M5未验收、M6未开始；旧阶段、失败与未验证项保留。

## PR #28历史功能验证（不是本轮执行）

| 命令 | 结果 | 口径 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 917通过/55跳过，16.88秒 | 旧回归多锁定audit/growth=false；新增显式生产路径另测 |
| `.venv/bin/python scripts/test_postgres.py` | 233通过，9.40秒 | 独立临时库，覆盖记忆/天气/情绪/成长，结束删除；和全量重叠，不相加 |
| `npm test --prefix frontend -- --run` | 60通过，1.82秒 | 合成交互/组件回归，非逐项浏览器人工检查 |
| `npm run build --prefix frontend` | TypeScript及生产构建通过 | 忽略的app/static产物 |
| 封存校验/参考审计 | 24公开候选not_assessed；38例/34源离线有效 | 哈希/结构通过，不等于独立质量验收 |

以上耗时是测试运行时间。真实模型原回复/时延只按历史各轮记录引用；当前不额外采样。仅文档变更无需重复应用全量、PG或前端构建；本轮检查结果见下方。

## 必须保留的失败与限制

- 旧完整事实审计15漏检、5误拦截、1未决；部分机制后续修复，不代表全部关闭或当前泛化达标。
- PR #20英文地名8.003秒timeout、CLI退出1，历史503/限流/非法结构/误判保留；未验证免费额度就是原因。
- M3初轮3次自动评审JSON解析失败；评审提示/结构化方法中途调整，不称预注册独立盲评。W01/W02实现修复后仍保留原回复/方法局限。
- PR #28新增事务/跨日回归修复前2失败/1通过/3跳过，修复后31通过/29跳过；此前错误405/404断言、数据库停机启动失败、系统Python缺dotenv检查失败均未抹去。
- 旧32保留例已静态审阅；封存v1/v2是24条公开作者已见候选，不是独立未见集。历史成绩不合并为当前独立模型质量。
- PR #27两次真实合成问候/闲聊成功（1.124/5.625秒）不等于普遍可用、自然度或男友感稳定达标。

未验证清单和门槛见[M5](M5_EVALUATION.md)，M2三项边界见[M2](M2_MEMORY.md)。未落实独立人员/正式新集/双标裁决盲评、完整消融、安全/情绪质量、真实性能费用和成长体验，M5未整体验收。

## 历史原文索引

以下固定到文档整合前Git版本，完整保留当时的合成原回复、耗时、失败、实验配置、Prompt、标注协议与PR血缘。旧文件从当前目录合并移除，原文不被“改成成功”。没有网络时可运行`git show 68b08f5:docs/<原文件名>`；根目录旧任务清单用`git show 68b08f5:TODOLIST.md`。这属于可追溯Git记录，不声称是独立评分原件或当前状态。

| 原文（固定版本） | 当前维护入口 |
| --- | --- |
| [SCENE_ROLEPLAY.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/SCENE_ROLEPLAY.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [FACT_ROLE_TEST_PREPARATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/FACT_ROLE_TEST_PREPARATION.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [NARRATIVE_REFERENCE_AUDIT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/NARRATIVE_REFERENCE_AUDIT.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [PROJECT_STATUS.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/PROJECT_STATUS.md) | [PLAN.md](PLAN.md) |
| [ARCHITECTURE.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/ARCHITECTURE.md) | [ARCHITECTURE.md](ARCHITECTURE.md) |
| [SCENE_PLACE_GROUNDING.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/SCENE_PLACE_GROUNDING.md) | [SCENE_PLACE_GROUNDING.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/SCENE_PLACE_GROUNDING.md) |
| [FRONTEND_MIGRATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/FRONTEND_MIGRATION.md) | [M1_CHAT.md](M1_CHAT.md) |
| [RETRIEVAL_ABLATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/RETRIEVAL_ABLATION.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [INDEPENDENT_EVALUATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/INDEPENDENT_EVALUATION.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [EMOTION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/EMOTION.md) | [EMOTION.md](EMOTION.md) |
| [RELATIONSHIP_GROWTH.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/RELATIONSHIP_GROWTH.md) | [RELATIONSHIP_GROWTH.md](RELATIONSHIP_GROWTH.md) |
| [TEST_HISTORY.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/TEST_HISTORY.md) | [TEST_HISTORY.md](TEST_HISTORY.md) |
| [M5_AUTOMATION_AND_HUMAN_REVIEW.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M5_AUTOMATION_AND_HUMAN_REVIEW.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [DATA_PRIVACY.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/DATA_PRIVACY.md) | [DATA_PRIVACY.md](DATA_PRIVACY.md) |
| [FACT_SUPPORT_EVALUATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/FACT_SUPPORT_EVALUATION.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [NATURAL_CHAT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/NATURAL_CHAT.md) | [M1_CHAT.md](M1_CHAT.md) |
| [M1_TEST_REPORT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M1_TEST_REPORT.md) | [M1_CHAT.md](M1_CHAT.md) |
| [MEMORY_SOURCE_TIME.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/MEMORY_SOURCE_TIME.md) | [M2_MEMORY.md](M2_MEMORY.md) |
| [PLAN.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/PLAN.md) | [PLAN.md](PLAN.md) |
| [DEMAND_MEMORY_AND_SEMANTIC_REVIEW.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/DEMAND_MEMORY_AND_SEMANTIC_REVIEW.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [M4_TEST_REPORT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M4_TEST_REPORT.md) | [EMOTION.md](EMOTION.md) |
| [FEATURES.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/FEATURES.md) | [PLAN.md](PLAN.md) |
| [NARRATIVE_CALIBRATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/NARRATIVE_CALIBRATION.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [OFFLINE_ANNOTATION_SCORING.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/OFFLINE_ANNOTATION_SCORING.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [GEMINI_TEST_REPORT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/GEMINI_TEST_REPORT.md) | [M1_CHAT.md](M1_CHAT.md) |
| [WEATHER.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/WEATHER.md) | [WEATHER.md](WEATHER.md) |
| [M3_TEST_REPORT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M3_TEST_REPORT.md) | [WEATHER.md](WEATHER.md) |
| [RETRIEVAL_GUARDS.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/RETRIEVAL_GUARDS.md) | [M2_MEMORY.md](M2_MEMORY.md) |
| [M5_BUSY_S03.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M5_BUSY_S03.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [M2_TEST_REPORT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M2_TEST_REPORT.md) | [M2_MEMORY.md](M2_MEMORY.md) |
| [SEMANTIC_REVIEW_STABILITY.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/SEMANTIC_REVIEW_STABILITY.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [M5_TEST_REPORT.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/M5_TEST_REPORT.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |
| [EVALUATION.md](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/EVALUATION.md) | [M5_EVALUATION.md](M5_EVALUATION.md) |

## 本次文档整理检查

范围：AGENTS项目知识、模块综合文档、任务清单和导航链接；不改代码/Prompt/数据、封存材料和历史合成回复证据。已通过：

- `.venv/bin/python -m pytest -q tests/test_fact_support_evaluation.py tests/test_reference_audit.py tests/sealed tests/annotations tests/test_fact_role_pairs.py`：175通过，2.53秒，覆盖历史回复逐字核对、参考哈希、封存、标注评分及合成正反对；不是新真实模型质量。
- `scripts/check_sealed_evaluation.py --validate-content`：24公开候选、model_calls=0、not_assessed；`scripts/audit_narrative_references.py`：38例/34源、api_calls=0。
- 全仓Markdown本地文件/锚点与代码围栏、固定Git历史原文索引、原始合成回复一致性、敏感值扫描、`git diff --check`通过；生产代码/Prompt/测试/评测数据和历史场景原文未改。
- 初次链接检查发现`prompts/DESIGN.md`仍链接旧M3报告，先失败；保留7行兼容入口与原锚点后通过，避免修改已绑定来源哈希的Prompt。保留这次检查失败，不冒充首轮全通过。

本次不新增玩家CRUD或数据迁移，没有新增缓存/删除路径；相关操作不适用。未重跑已通过的应用全量、前端构建或临时PG；175项是本轮受影响离线回归，与上述历史基线不相加。


## 2026-11-11 · PR #29合并审阅

确认仅Markdown变更、13份综合/兼容文档、33份固定Git历史入口和源证据保留。审阅发现三处新索引链接误指向旧TEST_HISTORY不存在的锚点（聊天/天气/情绪），固定Git锚点检查先失败；已改回当前索引。补回合并时遗漏的原协议二元一致率≥85%、Cohen κ≥0.6目标，未改门槛或宣布达标。

受影响命令`.venv/bin/python -m pytest -q tests/test_fact_support_evaluation.py tests/test_reference_audit.py tests/sealed tests/annotations tests/test_fact_role_pairs.py`：175通过，2.64秒。修正文档后当前/固定Git链接和锚点、围栏、原文不变检查通过；24候选封存not_assessed及38例/34源审计零API通过。未改变功能/数据，不重复应用全量或PG/构建。PR审阅/行内意见及CI均无待处理项（无配置CI，不声称线上CI通过）。

PR #29经本次squash交付main，随后PR #30变基至此基线并另行检查。历史回复/耗时/失败及未验证项保留；本轮真实API0，M5未验收、M6未开始。

<a id="japanese-ui-20261111"></a>

## 2026-11-11 · 日语UI与中日双语文档

范围：M5语言适配，不开始M6。开发时基于PR #28及当时尚待合并的文档PR #29（现已合并`5a62fca`）；本轮真实模型/天气/支付API调用0次，不新增真实模型原回复/时延，不读取真实玩家数据或评分原件。

| 命令 | 本轮结果 | 说明 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 928通过/55跳过，14.12秒 | 当时含11项新语言回归；随后仅补1项固定回退回归，不重复全量 |
| `.venv/bin/python -m pytest -q tests/localization` | 最终12通过，0.47秒 | 包含中文兼容/日语切换、非法locale、CSRF/身份、mock、超时不重试/不加分、日语记忆CRUD/隔离/删除重启不复活及guarded日语回退；与全量重叠 |
| `npm test --prefix frontend -- --run` | 最终69通过，1.53秒 | 原60+新增9；覆盖词典/变量、UI切换/偏好、原文保持、IME、日语请求/CSRF、失败恢复、解锁和删除确认 |
| `npm run build --prefix frontend` | TypeScript与生产构建通过 | 忽略生成产物，无浏览器逐项人工/实际读屏验证 |
| 封存校验/参考审计 | 24候选not_assessed；38例/34源通过，API=0 | 旧v1/v2、源绑定Prompt/参考/测试不改，新日语政策需另行冻结 |

固定日语模型测试fixture示例：输入「こんにちは」，注入生成原文/交付文本为「こんにちは。ゆっくり話してね。」；内置mock明确返回「これはオフラインのデモだよ。うん、聞いているよ。話したいことから、ゆっくり聞かせて。」。两者是合成离线数据，不是Gemini实际回复；模拟timeout只调用1次且不保存历史/积分，不反复采样。耗时表为测试执行耗时，不是模型响应时间。

初次失败保留：前端59通过/1失败，新增locale曾改变中文发送JSON；修正为仅日语带locale后通过。新前端测试初次因node:fs未在浏览器tsconfig启用类型而类型检查失败，改用Vite raw导入后通过。工作用抽取脚本曾因项目TypeScript7没有旧typescript.js API失败；脚本未加入仓库。一次临时导航更新here-doc被解释器报告非UTF-8并退出，改为UTF-8文件后执行成功，未当作功能或真实模型失败。

未改数据库表、索引、向量算法或经济事务，不新建玩家库、不做真实库CRUD；PG233沿用PR #28历史，不重跑或充作本轮。日语自动提取/路由/日期、天气意图/地点/日期、情绪自述和复杂事实检查仍偏中文；母语独立质量、跨语言检索、真实服务性能/成本和设备视觉/IME/读屏未验收。历史失败、封存v1/v2和全部M5未验证项保留。详见[日语适配](JAPANESE_LOCALIZATION.md)。

提交前补充：修正日语mock模式的模型状态文字后，前端69项及类型/构建再次通过（最终1.53秒；先前1.66秒为开发记录）。双语对应页/链接/锚点/围栏、Python语法、源/封存/历史原文不变和新增/变更文件秘密值扫描通过；`.env`和构建产物保持忽略，未提交运行数据。

## 2026-11-11 · PR #30变基审阅与合并

PR #29已squash为`5a62fca`。PR #30从原文档提交之后仅重放日语功能至最新main；5处文档冲突逐项合并（TODO、聊天、计划、导航、测试历史），保留#29的一致率/κ和三处锚点修复、历史记录及全部日语内容。首次PR #29合并接口误传短SHA被422拒绝，改用40位确切SHA成功；拒绝时未修改分支。

审阅复现“日语保存提示/错误在切回中文后仍是日语”：先新增两项回归，2失败/9筛选跳过；精确识别应用自带词典文案恢复中文，未知日语错误用中文通用提示。只处理应用状态文字，不翻译用户事实/消息/记忆。两项已包含在最终前端71项。

- `.venv/bin/python -m pytest -q`：929通过/55跳过，14.60秒（含全部12项日语后端；旧audit/growth=false和新companion/growth=true口径保持）。
- `npm test --prefix frontend -- --run`：71通过，1.78秒；`npm run build --prefix frontend`：类型检查及生产构建通过。
- 文档本地/固定Git链接与锚点、双语对应页、围栏、冲突标记、原人物/Prompt/封存/历史证据不变、Python语法及秘密/运行数据边界检查通过。24候选not_assessed、38例/34源审计通过，均零API。

原生IME/视觉/读屏、日本语真实模型语气与事实质量、工具触发、自动提取/日期、独立评审/新集/完整消融、真实可用性/费用均未新增验收。原15漏检/5误拦截/1未决、503、8.003秒超时/CLI退出1和初期开发失败完整保留；未进行真实模型/天气/支付调用或操作真实玩家数据。表/向量/钱包事务未改，PG233沿用历史，不重复执行或冒充本轮结果。按本次PR #30 squash合入main并快进同步、核对文件树和清理两任务分支；M6未开始。

## 2026-11-11 · 中日语义记忆与正则职责迁移（PR #31）

策略`multilingual-memory-v1`，代码位于app/memory_understanding.py及main/memory/progression/reply_pipeline的接入。默认semantic；旧回归在conftest明确固定legacy，新tests/multilingual_memory显式semantic/companion/growth=true。只迁移本轮记忆相关含义判断，不声称项目所有正则都已删除。

| 命令 | 最终结果 | 范围 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 998通过/77跳过，15.11秒 | 包含69项新增本地语义回归；22个新增PG变体默认跳过，另有旧55跳过 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 212通过，10.90秒 | 新建/删除随机临时PG库；记忆、成长和语义套件，含SQLite对照，和全量重叠不相加 |
| `npm test --prefix frontend -- --run` | 71通过，1.83秒 | 更新中日记忆数据流/候选确认文案后原交互回归 |
| `npm run build --prefix frontend` | 类型检查和生产构建通过 | 不逐项打开网页，不称实际IME/视觉验收 |
| 封存校验、来源审计 | 24公开候选not_assessed、38例/34源通过，model_calls/api_calls=0 | 旧根参考、角色/源绑定Prompt/旧测试和封存v1/v2未改 |

覆盖：中日同一结构；问候/近期已足够/拒绝/未授权不读库；原文唯一引用、主体/引用/假设字段、非法/低置信/日期/重复/外部ID；日期时区、跨年/闰年/下周星期及未知；候选→确认→跨会话查询→纠正→删除→重启不复活/显式重加；同相对原文跨日不覆盖旧日期；姓名类型提示不靠同词、旧预约slot兼容；版本/CSRF/跨身份/撤回/过期/原子回滚；重要旧事无答案仍进入语言无关事实核对，普通问候不强制审查；SDK请求使用MockTransport而非外网。

合成追踪（不是实际LLM理解成绩）：today=2026-11-11、Asia/Tokyo，预置分析把「来週火曜日に面接があります。」标为weekday/1/1，程序算2026-11-17，候选fact保持原句；「我明天在合成北京市有面试。」或「明日、合成東京で面接があります。」标relative_days=1后得到2026-11-12。确认前不检索，确认后另会话仅使用白名单ID；回复固定fixture为「うん、ゆっくり話してね。」。**真实模型原回复、调用耗时、token/账单：未采集（本轮真实模型/天气/支付调用0）**。上述秒数是测试执行时间，不是模型推理速度。

初次新增单元测试收集因装饰器多写冒号产生1个SyntaxError/退出2，改正后44项通过；该失败保留，不视作生产接口失败。开发中先929/55原回归通过，之后随新用例/数据流改动到990/71、991/72、995/74，PG先198与200、206通过；补充跨日同原文、上下文只投影文本、日期保留范围、姓名/旧元数据兼容、语义回复入口后执行上述最终完整检查。重跑因这些具体变动，不反复采样模型挑成功；各轮计数重叠，不累计。

M5仍未整体验收，M6未开始。结构合法/置信阈值不是语义真实支持或日期解释准确率；SDK Mock只证明请求/解析边界，不证明真实Gemini接受所有schema或在4秒内完成。真实中日提取/否定/引用/时间/选择/审查质量、陌生表记与跨语言召回、成本/延迟、独立新集/评审、其余语言规则迁移均未验收。旧15漏检/5误拦截/1未决、503、8.003秒超时/CLI退出1及全部历史失败/未验证项保留。未上传密钥、真实对话/记忆、评分原件、数据库或运行导出。

提交前复查：手动修正旧记忆也在分析前检查30分资格、当前授权和epoch；新增未解锁/校验后撤回的SQLite/PG回归，不向模型发送修正文，仍可查看/删除。生成Prompt另明确旧原文的明天/明日/来週不按当前日期重算，只使用已保存event_date，null不猜。定向命令`PYTEST_ADDOPTS='-k cross_session_confirmation_retrieval_correction_delete_and_no_revival' .venv/bin/python scripts/test_postgres.py --semantic-memory`：4通过/208未选择，1.23秒，与整套212重叠。复查前996/75、PG208为开发记录；补充权限后998/77先16.69秒，最后日期Prompt合同加入后为15.11秒。一次临时文档here-doc因编码错误退出，改为文件补丁后更新成功，不作为功能/API失败。


### PR #31 合并审阅 · 2026-11-11

复现并修复原文去重缺陷：合成姓名「私の名前はA-Bです。」与「私の名前はABです。」此前被旧去标点比较合并，新增回归先1失败/1跳过/45未选（0.41秒）。semantic候选改用原文和事件日期判重；查看/确认同字段差异也按原文比较，明确替换或独立保留后才能确认。legacy历史比较不变，删除指纹仍保守防复活，不把原文比较当语义判断。定向修复后1通过/1跳过/45未选（0.51秒）；覆盖候选可见、确认409、显式替换、旧原文/向量不再检索。

- `.venv/bin/python -m pytest -q`：999通过/78跳过，16.90秒（新增70项本地语义回归；23个新PG变体默认跳过，另旧55跳过）。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：214通过，10.21秒；独立临时PG创建/删除，含SQLite对照，计数重叠不相加。
- `npm test --prefix frontend -- --run`：71通过，1.75秒；`npm run build --prefix frontend`：类型检查/生产构建通过。

本次无外部CI检查记录，以上为本地命令行验证；不将结构测试冒充真实模型/独立质量验收。按PR #31 squash交付main、快进同步并核对文件树后清理任务分支；历史封存v1/v2、失败和未验证项全部保留，M5未整体验收，M6未开始，真实API调用0次。

审阅附加检查：封存24条仍not_assessed，38例/34源离线审计通过，model_calls/api_calls=0；修改Python语法、本地Markdown目标、冲突标记、已跟踪敏感路径和本地秘密值边界均通过；人物/旧审查Prompt/封存与源绑定证据未改。一次检查误用系统python缺少dotenv而未完成，改用项目.venv重跑通过，不作为API/功能失败。

## 2026-11-12 · 中日天气语义理解（PR #32）

新增app/weather_understanding.py、multilingual-weather-v1及main接入，默认semantic；旧回归在conftest显式legacy，新tests/multilingual_weather固定semantic/companion/growth=true。迁移意图/地点/日期，不修改旧weather.py或旧源绑定测试/Prompt，不声称全部回复规则已迁移。

| 命令 | 结果 | 范围 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 最终1077通过/92跳过，17.54秒 | 原999/78加新增78本地/14PG变体跳过；不是全部生产默认覆盖 |
| `.venv/bin/python -m pytest -q tests/multilingual_weather` | 阶段76通过/12跳过，1.06秒 | 默认路径/缓存断言/自然日语fixture定向检查，早于最后pending补强；与全量重叠不相加 |
| `.venv/bin/python scripts/test_postgres.py --semantic-weather` | 最终220通过，6.69秒 | 随机临时PG创建/删除；旧天气/成长+新语义，含SQLite对照，和全量重叠 |
| `npm test --prefix frontend -- --run` | 71通过，1.56秒 | 原交互、日语字典及新增模型数据流提示断言 |
| `npm run build --prefix frontend` | TypeScript/生产构建通过 | 无网页逐项手测 |
| 封存校验与来源审计 | 24公开候选not_assessed、38例/34源通过，API0 | v1/v2与旧原文不改，不作为独立质量验收 |

覆盖：中日意图结构、问候/纯地名/隐喻/引用/拒绝不触发，低置信/非法字段/原文绑定/URL/控制字/外部地点拒绝；假名汉字城市、同名/无结果；目的地跨时区/年界、明确周偏移/日期、历史/超范围/模糊日期；缺城市→补充、跨午夜原日期锚点、10分钟过期/取消/设置删除清pending；资格与授权在分析前、epoch在分析/地名/预报边界；设置增查改删/CSRF/身份隔离/重启持久化/撤回与删除清缓存；无重试/假天气，非法理解仍能普通聊天。SDK与地名HTTP均MockTransport，不出网。未新增库表/索引，无新表CRUD或迁移。

合成追踪：固定2026-11-12T00:00Z、Asia/Tokyo；预设模型把「さいたま市の明日の天気は？」提为city=さいたま市、relative_days=1、expression=明日，或「广州明天下雨吗？」的广州/明天=1，程序算2026-11-13；预报数据来自mock，不是真实天气。**真实模型原回复、模型耗时/token/费用：未采集，真实Gemini/天气/支付API均0次**；上述秒数仅命令执行时间。

保留本轮失败：初次契约62通过/1失败（0.69秒），原因是测试helper为use_pending误填非null日期，修正为合法协议后63通过（0.40秒）；首次生命周期75通过/12跳过/1失败（1.13秒），重启fixture未先初始化/v1/session，补齐后76/12（0.94秒）。首个PG命令因本地DB未运行连接拒绝退出1，Docker daemon检查也失败；启动已有本地Docker/db后只用脚本临时库完成216通过（5.90秒），补强默认与缓存断言后216/6.80秒，最终更换自然日语fixture后216/5.91秒，重跑有具体变更且计数重叠。前端隐私文案初次修改后70通过/1失败（1.66秒），漏写明确GPS/IP措辞，补回并增加模型发送提示断言后71通过/构建通过。编辑文案的一次系统python here-doc编码错误、两次补丁上下文未匹配未落盘，改用准确文件补丁完成，保留为编辑失败，不冒充API故障。

**已确认的旧限制**：自然日语fixture「これはオフラインの合成デモの天気だよ。」会被旧weather_reply_conflicts要求中文“演示”的展示检查拦截，返回中文“这是演示天气…”回退。新天气理解不修复这套旧输出策略；测试显式记录该行为，不以混入中文标记掩盖。当前天气的日语不确定语气也仍待旧检查迁移；不声称日语天气回复全面完成。

收尾代码检查补强pending提交边界：语义天气先消费旧pending，仅在生成与记忆/成长原子提交均成功后保存新pending；失败既不新增也不复活旧日期请求。新增2项本地+2项PG合成回归，正常/已有pending两种生成504均不写本轮历史。检查后执行表内最终1077/92与PG220；之前全量1075/90、16.66秒及PG216是补强前阶段记录，保留不累计。

仍未验收：真实Gemini schema兼容/4秒可用率，中日意图/城市级隐私与主体/否定/引用/日期关系/澄清理解质量；高置信和原文字符合法不证明语义正确。独立新集/双标/盲评、完整消融、安全、真实延迟/费用、日语口吻/剩余规则与B01/B02/B03保留。旧15漏检/5误拦截/1未决、503、8.003秒超时/CLI退出1不关闭。M5未整体验收、M6未开始，不上传秘密、真实玩家资料或评分原件。

### PR #32合并审阅（2026-11-12）

审查结构/原文/日期范围与目的地时区、授权先于理解调用、工具边界epoch、pending成功提交/失败不复活及设置CRUD/缓存/删除隔离，未发现新的合并阻塞问题；未改功能代码。按本次PR squash交付main并快进同步、核对测试提交与main文件树后清理任务分支。远端main无新增提交，无需变基；GitHub无外部CI检查/评审记录，以下为本地CLI合成验证。

- `.venv/bin/python -m pytest -q`：1077通过/92跳过，17.55秒；旧legacy与新semantic覆盖口径不变。
- `.venv/bin/python scripts/test_postgres.py --semantic-weather`：220通过，6.68秒；脚本随机临时库创建/删除，与全量重叠。
- `npm test --prefix frontend -- --run`：71通过，1.80秒；`npm run build --prefix frontend`类型检查/生产构建通过。
- 封存校验仍24公开候选not_assessed，来源审计38例/34源通过，API/model_calls=0；中日本地文档引用、Python语法、暂存差异与秘密/运行数据边界检查通过。

自然日语天气说明被旧展示检查拦截并回退中文的已知限制继续显式保留，**未修复、未验收**；历史开发失败、503/8.003秒超时、封存v1/v2及全部未验证项不改写。真实模型原回复/耗时/费用本轮未采集（真实API0），M5仍未整体验收、M6未开始。

## 2026-11-12 · 中日天气回复修复（PR #33）

上述“未修复”为PR #32合并时的历史状态，不改原记录。本轮默认semantic天气路径采用weather_presentation.py的新策略multilingual-weather-care-v1，Prompt/数据流与边界见[天气综合文档](WEATHER.md)。旧weather.py、companion/semantic_review的Prompt和源绑定历史测试/封存v1/v2不改，legacy仍可复现旧限制。

| 命令 | 最终结果 | 口径 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 1127通过/97跳过，16.09秒 | 在1077/92基线上新增45项本地表达/SDK契约、5本地+5PG变体；总数非全为默认生产覆盖 |
| `.venv/bin/python scripts/test_postgres.py --semantic-weather` | 275通过，6.94秒 | 随机临时PG创建/删除；旧天气/成长、新理解/回复，含SQLite对照；与全量重叠 |
| `npm test --prefix frontend -- --run` | 71通过，1.68秒 | 未修改前端协议，既有中日交互回归 |
| `npm run build --prefix frontend` | 类型/生产构建通过 | 不逐个打开网页，不称实际设备验收 |
| 封存/来源审计 | 24公开候选仍not_assessed、38例/34源通过，API0 | 旧15漏检/5误拦截/1未决与v1/v2不关闭 |

合成前后（不是真实LLM效果）：给定forecast mock 12–18度，原回复fixture「これはオフラインの合成デモの天気だよ。」在旧函数仍触发误拦截、旧回退为「这是演示天气。那边这天预计12到18度。出门按自己舒服的节奏来，衣服也选方便增减的。」；新路径的模拟accept后原日语完整返回，1次生成/1次审查，无重写、guarded=false。current mock=15度时「これはデモの天気だよ。今は15度くらい。」也不再要求中文词。无judge/关闭review则1次生成后给安全的日语工具短句，status=weather_safe_fallback，不冒充自由文已核对。**真实模型原回复、模型推理耗时、token/费用均未采集，真实Gemini/天气/支付调用0次**；表中秒数仅命令耗时。

覆盖：中文旧回归保留；中日demo/估计/预报语义Prompt及locale证据；SDK MockTransport验证companion/audit版Prompt、结构/证据白名单；自然日语无多余重写；温度范围/单值/%错配即使模拟accept仍不能覆盖程序检查；数字只在纯天气归属片段核对，考试90%及混合来源不当湿度；缺湿度/预报冒充当前/虚构玩家事实模拟revise→同语言重写；事实supported但表达问题role_issues仍重写；默认工厂接入新judge；无judge/禁用review、13种失败/真实来源非演示、审查超时503不留本轮历史和pending、非法结构不泄露原异常。既有天气设置CRUD/身份/CSRF/撤回/缓存/删除重启由相同受影响套件复查；无新库表或资料持久化，新增表CRUD不适用。

本轮失败保留：首次新增套件17失败/104通过/14跳过（1.51秒），测试夹具漏填情绪status，修正为disabled后121通过/14跳过（1.00秒），不把夹具失败当Gemini问题。初次PG命令因DB未运行连接拒绝退出1，首次启动命令又因Docker尚未就绪失败；服务就绪后脚本临时库通过。阶段全量1124/96（15.62秒）→1126/96（16.69秒），PG272（6.37秒）→273（7.18秒）→275（6.60秒），新增数字归属/混合句、默认工厂和reply_locale证据后执行表内最终检查；重跑有具体变更，计数不累计，不存在真实API重采样挑成功。定向表达45通过（0.61秒）、天气全套128/19（1.17秒）均与全量重叠。

仍未验证：真实Gemini对新Prompt/schema的接受、中文/日语天气口吻与demo/估计遗漏判定、事实证据归属（特别混合句/汉字数字）、误拦截/漏检率、审查非ok新增调用的延迟/费用、独立新集/双标/盲评、正式消融/安全与情绪/其余回复迁移。数值语法校验不是语义裁判，高置信也不证明真实支持；新role_issues语义不可静默套用旧封存。B01/B02/B03、旧失败/503/8.003秒超时/CLI退出1继续保留。M5未整体验收，M6未开始，不上传秘密、真实玩家数据或评分原件。

### PR #33合并审阅（2026-11-12）

核对回答/审查Prompt的语言与事实边界、demo/locale证据投影、纯天气数值约束/混合来源处理、共享一次重写和同语言兜底、审查失败与授权/epoch撤回流程，未发现新的合并阻塞问题；未修改功能代码。main无新增提交，不需变基。GitHub无外部CI/评审记录，以下为本地CLI合成检查；按本次PR squash交付main、快进同步并核对文件树后清理任务分支。

- `.venv/bin/python -m pytest -q`：1127通过/97跳过，17.39秒；旧legacy和新semantic覆盖口径保持。
- `.venv/bin/python scripts/test_postgres.py --semantic-weather`：275通过，7.32秒；脚本随机临时库创建/删除，与全量重叠不相加。
- `npm test --prefix frontend -- --run`：71通过，1.71秒；`npm run build --prefix frontend`类型/生产构建通过。
- 封存24公开候选仍not_assessed、38例/34源离线审计通过，API/model_calls=0；Python语法、本地Markdown引用、差异及敏感文件/本地秘密值边界检查通过。

PR #32旧中文回退、初次17项夹具失败、环境启动失败及全部历史失败原文均保留，不将默认流程修复推定为真实Gemini事实/口吻验收。语义归属/复杂混合句/汉字数字、独立数据与评审、真实时延/费用等未验证项不关闭。真实模型原回复/推理耗时/token本轮未采集（真实API0），M5未整体验收、M6未开始。

## 2026-11-12 · 中日情绪自述与触发语义迁移（PR #34）

新策略multilingual-emotion-v1在app/emotion_understanding.py，main默认semantic接入；旧回归通过conftest明确legacy，新套件明确semantic/companion/growth=true。只迁移自述/否认/变化/陪伴请求的含义与完整估计协议，不将权限、调度、冷却、阈值、原文/ID、epoch和状态提交交给模型；旧emotion.py/Prompt、旧根测试及封存/源绑定资料不改。详见[情绪综合文档](EMOTION.md)。

| 命令 | 最终结果 | 范围 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 1184通过/108跳过，16.76秒 | 原1127/97加57本地语义回归，新增11PG变体默认跳过；不把全部称生产默认覆盖 |
| `.venv/bin/python scripts/test_postgres.py --semantic-emotion` | 172通过，6.32秒 | 脚本创建/删除随机临时PG，旧情绪/成长+新语义，含SQLite对照，与全量重叠 |
| `npm test --prefix frontend -- --run` | 71通过，1.48秒 | 中日每轮语义判断/完整分析频率及额外数据处理说明，既有CRUD交互 |
| `npm run build --prefix frontend` | TypeScript/生产构建通过 | 不手动逐项打开网页，不称原生设备验收 |
| 封存/来源校验 | 24公开候选仍not_assessed，38例/34源通过，model_calls/api_calls=0 | 旧v1/v2和15漏检/5误拦截/1未决不关闭 |

覆盖：中日混合/否认/引用/他人/假设/普通问候的预置决定；非空白唯一原文、严格字段/非法置信/标签/证据、窗口投影、低置信unknown、共享超时及耗尽后不启动第二调用；周期/提前/冷却、失败占冷却、手动纠正保护与瞬时偏好不改设置、缓存过期不续期；90分/授权先于调用、CSRF与身份隔离、设置/参考CRUD、物理删除设置/新实例无推测、模型边界撤回409、生成504不保存新参考也不复活被否认旧标签、基础聊天继续。SDK双步骤只用MockTransport及合成密钥。无新库表/向量迁移，额外表CRUD不适用；情绪解释不直接入长期记忆。

合成原文/结果（不是实际LLM成绩）：输入「悲しくない、ただ疲れてる」或「我不是难过，只是累了」，预设Decision将原文绑定report.labels=[tired]、confidence=.95；程序返回self_report、source=model、basis=self_report、当前u1证据。单独「悲しくない／我并不难过」预置为unknown，不自动变joy。回答fixture为「うん、ゆっくり聞かせて。」；其中没有真实模型的“前后效果”。**真实模型原回复、推理耗时、token/费用未采集；本轮真实模型/天气/支付API均0次**，表中时间仅命令执行耗时。

保留本轮失败：初次SDK契约测试41通过/1失败（0.60秒），测试将同一注入HTTP client跨两次parse复用，而SDK第一次后会关闭它；改为每调用独立的MockTransport client来复现生产边界，42通过（0.59秒），不是Gemini故障。纯空白source_text回归先失败1项/42未选（0.09秒），曾被误当自述，加入非空白校验后定向1通过（0.19秒）。共享预算耗尽回归先失败1项/44未选（0.22秒），asyncio.timeout(0)未阻止无挂起的模拟第二调用；加入remaining<=0的显式拒绝后通过完整检查。前端文案改为每轮语义入口后，旧文字断言70通过/1失败（1.73秒）；改为检查每轮发送及完整分析默认间隔说明后71通过/构建通过。

开发阶段全量1181/108（17.30秒）、1182/108（17.44秒）、1183/108（16.66秒），PG169/6.12秒、170/6.15秒、171/6.34秒保留为上述空白校验/冷却回归、投影和deadline补强前记录；最终值见表，不累加。定向新套件曾54/11（1.02秒）、56/11（0.90秒与0.87秒），与最终重叠。重跑因具体变化，不存在真实API连续重试或重采样挑成功。

来源收尾复查：新增断言先1失败/44未选（0.11秒），发现当前模型解释的listen虽未改缓存，却在返回副本上改了source=user的response_strategy。修正为手动assessment完整保持原样，本轮模型偏好独立support_preference投影；不将模型解释伪标玩家确认。自述API强度占位不进入回答上下文。补强前1184/108·16.14秒、PG172/6.01秒及前端71/1.70秒保留，之后执行表内最终后端/PG；日语UI措辞润色后前端71/1.48秒和构建通过。文件语法、本地文档引用、差异/暂存及敏感文件/本地秘密值边界检查通过，无运行数据提交。

未验收：真实中日主体/否定/引用/讽刺/自述与触发质量、schema兼容、入口0.8/结果阈值的可靠性、共享6秒下两次模型调用的可用率/费用、独立多标签集/双标/宏F1与校准/关怀盲评。模型解释的自述不伪标source=user；API intensity=.5是兼容占位，未作为心情强度注入。旧情绪回复局部检查/兜底未全面多语言化。高置信/原文ID合法不证明真实语义支持；新策略需另冻结，不改旧封存“刷通过”。B01/B02/B03、旧503/8.003秒timeout/CLI退出1和所有历史失败/未验证项保留。M5未整体验收，M6未开始，不上传秘密、真实对话/记忆、评分原件或数据库。

### PR #34合并审阅（2026-11-13）

核对语义入口和调度分工、90分/授权、原文与user ID、手动来源/本轮偏好分离、阈值/冷却/共享预算、临时状态/失败/epoch撤回，未发现新的合并阻塞问题；本轮未改功能代码。远端main无新提交，无需变基。GitHub无外部CI/评审记录，以下为本地CLI合成检查，按本次PR squash交付main、快进同步并核对文件树后清理任务分支。

- `.venv/bin/python -m pytest -q`：1184通过/108跳过，17.39秒；旧legacy和新semantic覆盖口径不混同。
- `.venv/bin/python scripts/test_postgres.py --semantic-emotion`：首次因本地DB未启动连接拒绝退出1；启动Docker和现有db服务后，脚本创建/删除随机临时库，172通过，5.89秒，与全量重叠。
- `npm test --prefix frontend -- --run`：71通过，1.81秒；`npm run build --prefix frontend`类型/生产构建通过。
- 封存24公开候选仍not_assessed，38例/34源离线审计通过，API/model_calls=0；中日本地文档引用、Python语法、差异/暂存及秘密/运行数据边界检查通过。

本次环境启动失败、SDK/空白/预算/来源回归的历史失败原文和旧503/8.003秒timeout/CLI退出1均保留。真实Gemini主体/否定/引用/讽刺/信号精度、独立F1/校准/盲评、费用/时延及剩余情绪回复检查不标完成；真实模型原回复/推理耗时/token本轮未采集，真实API0，M5未整体验收、M6未开始。

## 2026-11-13 · 中日情绪回复检查与兜底（任务分支）

策略multilingual-emotion-care-v1，设计、源码和双语兜底例子见[情绪](EMOTION.md)。默认semantic不再以中文词判断情绪回复；审查语义处理诊断/读心、引用/否定/医生归因，控制信息不作事实证据。旧emotion.py与源绑定/封存v1/v2保持不变。

| 命令 | 最终结果 | 范围 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 1231通过/115跳过，17.60秒 | 原1184/108增加40局部单元、7 SQLite；新增7 PG变体默认跳过；旧legacy与新semantic不混称生产默认覆盖 |
| `.venv/bin/python scripts/test_postgres.py --semantic-emotion` | 226通过，7.29秒 | 创建/删除独立随机临时PG，含SQLite对照，与全量重叠不相加 |
| `npm test --prefix frontend -- --run` | 71通过，1.86秒 | 无前端源码变更 |
| `npm run build --prefix frontend` | 类型检查及构建通过 | 生成产物忽略，不手改/提交 |
| `.venv/bin/python scripts/check_sealed_evaluation.py --validate-content` | 24公开候选，not_assessed，model_calls=0 | 不是独立质量验收 |
| 离线跨文件审计 `evaluate_audit()` | 38案例/34来源，api_calls=0 | 来源与封存未改 |

合成原文：`「你其实」と決めつけず、話を聞かせて。`、`我不会断定“你其实很焦虑”，先听你说。`和`うつ病だと決めつけることはしないよ。話したいことから聞かせて。`。旧函数对中文触发词可能误拦，新预置nonfactual/accept后原文一次生成返回；纯日语诊断旧词面防线可能漏检，新预置revise后改写或日语兜底。这是模拟协议对照，不是真实Gemini判断准确率。日语listen兜底为`うん、聞いているよ。急いで答えを出さなくていいから、話したいことから聞かせて。`，不回退中文、不报标签/分数。中文对应`我在听，你可以按自己的节奏说。不急着找办法。`。

覆盖：两语言四种偏好、手动纠正原样保留、模型解释自述占位强度不投影、最新否认、引用/否定/医生归因、关闭不送旧参考、waiting不额外强制情绪审查；无judge/关review、低置信/非法结构/外部ID/超时、共享重写上限、模型工厂、失败不保存历史/新参考、在途撤回409、天气与倾听合并且数值不能被accept覆盖。既有语义套件继续覆盖设置/参考CRUD、身份隔离、持久化/撤回；未改表/向量/钱包/前端，不新增相应迁移或UI CRUD。

开发失败保留：`...pytest -q tests/multilingual_emotion/test_emotion_presentation.py -k control_policy`先1失败/39未选（0.11秒）：审查把emotion_policy当支持心情的证据仍被放行。程序增加控制证据引用拒绝后1通过/39未选（0.22秒）。非诊断含义仍交模型，不为此增加语言正则。过程全量1227/115·19.08秒→1230/115·18.00秒，临时PG222·7.76秒→225·7.55秒，新增归因/否认/天气数字与控制证据回归后执行表内最终检查，计数不累计。

本轮真实模型/天气/支付API **0次**；未采集真实模型原回复、推理耗时、token或费用，不重采样挑成功。真实中日语义误判、诊断漏检、自然度/关怀盲评、复杂混合句与否定范围、schema兼容、真实调用预算/时延均未验证。普通无参考waiting仅Prompt与既有选择入口，不保证全回复均被审查；失败/拒绝状态可能新增审查成本。B01/B02/B03、旧15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1及所有历史失败/未验证项保留；M5未整体验收，M6未开始。

### PR #35合并审阅（2026-11-13）

核对中日回答/审查Prompt、引用/否定/归因与非诊断边界、手动来源/瞬时偏好、控制信息不得充当事实证据、关闭参考不外送、waiting不额外强制情绪审查、同locale及天气组合兜底、共享预算与epoch撤回，未发现新增合并阻塞问题。本轮未修改功能代码；main无新增提交，无需变基。GitHub无外部CI检查记录，以下是本地CLI合成验证。

- `.venv/bin/python -m pytest -q`：1231通过/115跳过，18.95秒，legacy与semantic覆盖口径不混同。
- `.venv/bin/python scripts/test_postgres.py --semantic-emotion`：226通过，7.60秒；仅创建/删除随机临时库，与全量重叠。首次沙箱内连接127.0.0.1:54329被拒（Operation not permitted，退出1），申请允许本机连接后执行通过，非模型失败。
- `npm test --prefix frontend -- --run`：71通过，1.96秒；`npm run build --prefix frontend`类型检查与构建通过。
- 封存v2内容检查：24公开候选、not_assessed、model_calls=0；差异、本地文档引用、敏感内容和源绑定资料检查通过。无新增库表/UI，适用CRUD/隔离/持久化/失败流程由现有合成回归覆盖。

按本次PR #35 squash交付main、快进同步并核对main与受测提交文件树后清理任务分支。本轮真实API0，未新增真实模型原回复/推理耗时/token；语义漏检/误判、复杂引用否定与诊断归因、中日自然度、实际schema/时延/费用和独立评审仍未验收。保留开发失败、全部历史失败及封存v1/v2；M5未整体验收、M6未开始，不上传秘密或真实玩家资料。

## 2026-11-13 · 中日正史、记忆来源时间与地点回复（任务分支）

策略multilingual-fact-care-v1，默认REPLY_UNDERSTANDING_MODE=semantic；设计/源码/失败边界集中在[M5](M5_EVALUATION.md#中日人物来源时间与地点回复)。旧人物/来源时间/地点/场景函数、旧Prompt和封存v1/v2不改；根conftest明确reply legacy保留全部旧回放（也包括此前多语言记忆/天气/情绪套件），新tests/multilingual_facts明确semantic/companion/growth=true并含去掉环境固定后的实际默认入口，不把全部计数称新默认覆盖。

| 命令 | 最终结果 | 说明 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 1305通过/129跳过，18.65秒 | 原1231/115加60单元+14 SQLite；新增14 PG变体默认跳过 |
| `.venv/bin/python scripts/test_postgres.py --semantic-reply` | 209通过，9.26秒 | 脚本创建/删除随机临时PG，旧记忆/成长+新回复套件，含SQLite对照；与全量重叠，不相加 |
| `.venv/bin/python -m pytest -q tests/multilingual_facts` | 71通过/12跳过，1.16秒 | 状态计数收尾前的阶段检查，最终全量含74项本地新回归 |
| `npm test --prefix frontend -- --run` | 71通过，1.80秒 | 无前端源码变化 |
| `npm run build --prefix frontend` | 类型检查及构建通过 | app/static生成产物忽略 |
| `.venv/bin/python scripts/check_sealed_evaluation.py --validate-content` | 24公开候选、not_assessed、model_calls=0 | 不算独立验收 |
| 离线 `evaluate_audit()` | 38案例/34来源、api_calls=0 | 保留旧来源和审计，不重新标为已解决 |

合成原文及对照（**没有调用真实Gemini**）：

| 原文 | 旧词面问题与新模拟流程 |
| --- | --- |
| `「我30岁」という設定にはしないよ。` | 旧conflicts把引用中的年龄当自我断言；新脚本supported/C01后一次返回。 |
| `僕は30歳の医師だよ。` | 旧中文检查可能漏检；预置contradicted后一次重写为`28歳で、栖川の古書店を営んでいるよ。`，非真实模型判断。 |
| `さっき合成桜ヶ丘市に住んでいると教えてくれたね。` | 旧来源词面可能漏检；跨会话确认记忆只支持地址，脚本unsupported后改为`合成桜ヶ丘市に住んでいることは覚えているよ。`，未知event_date保持null。 |
| `“你刚才告诉我住在合成桜ヶ丘市”这句话不能凭旧记录来断定。` | 旧source_time函数可能误拦否定引句，新模拟完整引用审查不由词面推翻accept。 |
| `“青禾市”不是“合成青禾市”的完整写法。` | 旧place函数可能把讨论的缩写当实际采用；新Prompt区分使用/引用/否定。 |

另覆盖中文对应错误、继承/职业/失忆、来源日期与当前转述、完整地名/代词和无据距离、日语到店预设/最新离开、混合句正确半句不能遮盖共同过去、氛围许可；测试断言新路径不调用旧角色/时间/地点/场景函数。SDK MockTransport覆盖companion/audit×weather semantic/legacy×emotion semantic/legacy组合、真实默认工厂、当前用户标记/助手非证据；完整可信短句直返但追加/引用/异语言不能获豁免，记忆/force_review时不跳过。保留role_issues独立和适用天气数字、情绪参考/倾听与共用一次重写。

失败/状态回归包括未知及控制ID、覆盖不完整、低置信、非法结构、审查timeout、无judge/关review同语言兜底、生成/审查次数；503不保存失败历史，审查中撤回409。记忆手动候选/确认/跨会话检索/纠正/删除、原文与向量不复活、CSRF/身份/旧版本拒绝、新实例持久化覆盖，无真实玩家库操作。没有新增表/向量算法/前端API或钱包功能，对其新建迁移及UI CRUD不适用。

开发失败保留：首次新生命周期套件1失败/58通过/11跳过（1.16秒），重新打开app只复制Cookie却漏调`GET /v1/session`初始化，读记忆响应无items；修正测试夹具后62/11（0.98秒）。初始局部48通过（0.55秒）；增加组合边界/混合句/默认入口后64/11（0.97秒）、65/12（1.18秒）。增加完整可信短句后1失败/70通过/12跳过（1.03秒）：旧“无judge回退”夹具恰是新可信短句，期望状态不再适用，改为确实含未验证年龄的回复后表内71/12通过，不改生产策略来迎合断言。中途全量1293/126（20.08秒）→1296/127（18.80秒）、PG194（9.39秒）→198（9.22秒），之后补齐可信短句边界并执行表内最终检查，次数不累计；重跑均有对应变更。

真实模型/天气/支付API **0次**，真实模型原回复/推理耗时/token/费用未采集，无重采样。错误高置信accept仍可能漏过正史、来源或地点矛盾，结构合法不证明语义支持；真实中文/日语复杂释义/否定/引用/别名/到店、口吻/自然度、schema、独立盲评未验收。自由回复更常审查（完整可信成品短句才有界免审查），实际时延/费用/503率可能增加，未用离线成功推定可用性。旧15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1、B01/B02/B03和全部封存/失败/未验证项保留，M5未整体验收，M6未开始。

收尾红绿回归：`...pytest -q tests/multilingual_facts/test_fact_presentation.py -k rewrite_to_trusted`先1失败/59未选（0.09秒），发现首轮错误改写为可信短句后误重置guarded=false和calls=0，可能让成长把已纠正轮误视为未拦截。将直返限定首次生成，重写轮保留审查/计数后1通过/59未选（0.24秒）。修复前全量1302/127（18.24秒）、PG204（8.81秒）保留；修复后全量1303/127（18.12秒）、PG205（8.73秒）为上表最终结果。除已有两次夹具失败外，本次真实状态缺陷及其失败也保留，不影响“不调用真实API”的边界。

组合收尾回归：`...pytest -q tests/multilingual_facts/test_fact_flow.py -k legacy_place_extraction`先1失败/1通过/2跳过/24未选（0.50秒），发现reply semantic+audit的生成Prompt仍调用旧grounding_prompt提取中文地点，companion没有此残留。两种对话模式统一使用新原文记忆投影，仅reply legacy保留旧提取；补充相对日期仍只用已保存event_date。修复后2通过/2跳过/24未选（0.71秒）。随后全量1305/129（18.65秒）、临时PG209（9.26秒）为最终结果，替代上段阶段1303/127、PG205的最新口径；历史阶段和失败不删除。语法/链接/暂存秘密值检查及封存完整性通过，默认和audit组合都不再调用旧地点提取。

### PR #36合并审阅（2026-11-13）

检查回答/审查/重写Prompt中的正史、引用/否定、事件日期≠讲述时间、地名原文/别名与到店状态；核对companion/audit组合不运行旧地点提取，可信短句仅首次完整匹配且受证据/force_review约束，重写不重置guarded或审查计数；检查共享预算、控制信息非证据、失败/epoch撤回与记忆确认/纠正/删除非复活流程，未发现新增合并阻塞问题。本轮未修改功能代码，main无新增提交，无需变基；GitHub无外部CI记录，以下为本地CLI合成验证。

- `.venv/bin/python -m pytest -q`：1305通过/129跳过，20.99秒；旧legacy与新semantic覆盖口径不混同。
- `.venv/bin/python scripts/test_postgres.py --semantic-reply`：209通过，9.95秒。脚本创建/删除随机临时库，与全量重叠，不相加。
- `npm test --prefix frontend -- --run`：71通过，1.97秒；`npm run build --prefix frontend`类型检查与构建通过。
- 封存v2内容：24公开候选，not_assessed，model_calls=0；离线审计38案例/34来源，api_calls=0。首次自写审计摘要命令误对整数调用len，TypeError退出1；改用整数/列表兼容打印后摘要成功，未改审计或案例，不是模型失败。
- 差异/本地文档引用/敏感内容及旧源绑定检查通过。无新增表/UI迁移，适用CRUD/权限/持久化/失败流程由合成回归覆盖。

按本次PR #36 squash交付main，快进同步并核对main与受测分支文件树后清理任务分支。真实API0，未采集真实模型原回复/推理耗时/token/费用。封存v1/v2、开发夹具失败、guarded/calls状态缺陷与audit残留提取的红绿回归、旧503/8.003秒timeout/CLI退出1和全部历史失败保留；真实中日复杂释义/引用否定/地点别名/在场、角色自然度/独立盲评、schema与审查增加的可用率/延迟/费用仍未验收。M5未整体验收，M6未开始。

## 2026-11-13 · 日语口吻/记忆v2与盲评材料（任务分支）

用户明确本轮不调真实API，且确认“暂时没有，先准备材料”。因此**没有实际独立日语母语评分、裁决或模型盲评结果**。新增12条公开作者编辑回复，只作标注流程校准，不是Gemini原回复、新旧Prompt生成对照或独立正式集；评分全空、reviewer=null。程序测试中的合成评分不计为人评结果，也不提交评分文件。日语Prompt设计/准备与导入命令见[日语适配](JAPANESE_LOCALIZATION.md)，记忆流程见[M2](M2_MEMORY.md)。

| 命令 | 结果 | 范围 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 1331通过/131跳过，19.88秒 | 原1305/129＋26本地新回归、2 PG变体常规跳过；旧套件仍显式legacy，不全称新默认覆盖 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 242通过，11.41秒 | 随机临时库创建/删除，记忆/成长/多语言及新增日语套件，含SQLite对照；与全量重叠 |
| `npm test --prefix frontend -- --run` | 71通过，1.87秒 | 无前端源码变化 |
| `npm run build --prefix frontend` | 类型检查/构建通过 | 产物忽略，不提交 |
| `.venv/bin/python scripts/check_sealed_evaluation.py --validate-content` | 24旧公开候选not_assessed，model_calls=0 | v1/v2与源绑定保持不变 |
| 离线 `evaluate_audit()` | 38案例/34来源、api_calls=0 | 不关闭旧误判 |
| `.venv/bin/python scripts/evaluate_japanese.py` | 实际字符候选召回成功，API0 | 不读.env/玩家库，只用一次性SQLite；人工改写/类型不是模型预测 |

开发集12记忆/12查询（9有答案、3无答案），每题候选保留。实际观察：

| 候选输入 | 有答案候选Recall@5均值 | 无答案问题有候选数 |
| --- | --- | --- |
| 原问题 | 1/9（11.11%） | 1/3 |
| 人工改写查询 | 8/9（88.89%） | 1/3 |
| 人工改写＋类型提示 | 9/9（100%） | **3/3** |

这些是作者已见小样本、人工oracle输入下的实际候选排序，不是v2模型生成query的成绩，更不是最终语义选择/上下文注入/回复准确率；不与旧legacy消融混比。保留低召回和负例结果，不因正例9/9删除3/3误候选，也未增关键词/正则来“刷通过”。后续应独立测query/类型预测与无答案选择，B01字符哈希并未解决。

新增回归：真实SDK MockTransport发送v2与保存v1文本、日语省略/他人/引用/假设的预置结构、相对日期计算但确认原文不改、候选→确认→跨会话检索→中文切换保留日文→纠正未知日期→删除/向量不复活、拒绝/撤回停止分析。原归属/CSRF/版本/epoch与失败回归由全量继续覆盖；没有新增表/索引/经济功能，相关新迁移不适用。导出/评分覆盖空白拒绝、双份/单份、任务/角色/证据/Unicode覆盖篡改、重复字段、数据/Prompt哈希漂移、母语/独立声明严格布尔、κ退化/分歧、输出不泄露原文/评论/评审ID、拒绝仓库内导出/报告与覆盖、not_assessed及验收退出3。真实评分与映射仅在仓库外，无自动对外发送。

开发失败保留：首次evaluate_japanese.py在临时库尚未创建身份即configure，安全返回身份401并CLI退出2；接续摘要尝试读取空输出导致JSONDecodeError（退出1）。随后只在临时库先建合成身份、再开启测试授权，保留生产身份校验不放宽；CLI成功得到上述结果，无真实模型失败。首次组合定向77通过（1.46秒），新增日语全套26/2（1.38秒）与绑定补充后26/2（1.12、1.11秒）。最终导出参考/日语字段指南及哈希追踪补齐后26/2再次通过（1.27秒）；全量/PG/前端见表，计数不累计，未因成功而删除失败。

仓库外已生成两位评审各12任务的匿名空包、保管者mapping和日语指南；已见编辑材料、独立性/母语性未认证、样本不足等原因使结果始终not_assessed。尚无真实评分可汇总、一致率/κ可报告或裁决可做；没有虚构人类身份/评分。新旧日语/记忆Prompt源码版本保留，实际自然度/语义改善、schema兼容/调用延迟/费用均未采集，API0。封存v1/v2、旧15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1和所有历史失败/未验证项保留；M5未整体验收，M6未开始。

CLI端到端准备命令也已执行：每位12任务、两份空包/日语指南和私有mapping成功写入仓库外；直接导入空包按预期退出2，未写评分汇总，不把未填评分当零分。

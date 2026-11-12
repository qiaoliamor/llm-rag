# 测试基线、失败与历史索引

[中文](TEST_HISTORY.md) · [日本語](ja/TEST_HISTORY.md)

更新：2026-11-12。PR #29–#32已合并；本轮中日天气回复修复在任务分支。最终1127通过/97跳过、前端71及构建、临时PG天气275通过（重叠）。真实API0，M5未验收、M6未开始；旧阶段、失败与未验证项保留。

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

## 2026-11-12 · 中日天气回复修复（任务分支）

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

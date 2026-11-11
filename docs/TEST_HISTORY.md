# 测试基线、失败与历史索引

[中文](TEST_HISTORY.md) · [日本語](ja/TEST_HISTORY.md)

更新：2026-11-11。PR #29/#30已合并；本轮多语言语义记忆在任务分支待PR审阅。分支最终996通过/75跳过、前端71及构建、临时PG208通过（重叠）。零真实API，M5未验收、M6未开始；下列旧阶段结果保留原版本。

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

## 2026-11-11 · 中日语义记忆与正则职责迁移（任务分支，待PR审阅）

策略`multilingual-memory-v1`，代码位于app/memory_understanding.py及main/memory/progression/reply_pipeline的接入。默认semantic；旧回归在conftest明确固定legacy，新tests/multilingual_memory显式semantic/companion/growth=true。只迁移本轮记忆相关含义判断，不声称项目所有正则都已删除。

| 命令 | 最终结果 | 范围 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 996通过/75跳过，17.73秒 | 包含67项新增本地语义回归；20个新增PG变体默认跳过，另有旧55跳过 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 208通过，11.27秒 | 新建/删除随机临时PG库；记忆、成长和语义套件，含SQLite对照，和全量重叠不相加 |
| `npm test --prefix frontend -- --run` | 71通过，1.83秒 | 更新中日记忆数据流/候选确认文案后原交互回归 |
| `npm run build --prefix frontend` | 类型检查和生产构建通过 | 不逐项打开网页，不称实际IME/视觉验收 |
| 封存校验、来源审计 | 24公开候选not_assessed、38例/34源通过，model_calls/api_calls=0 | 旧根参考、角色/源绑定Prompt/旧测试和封存v1/v2未改 |

覆盖：中日同一结构；问候/近期已足够/拒绝/未授权不读库；原文唯一引用、主体/引用/假设字段、非法/低置信/日期/重复/外部ID；日期时区、跨年/闰年/下周星期及未知；候选→确认→跨会话查询→纠正→删除→重启不复活/显式重加；同相对原文跨日不覆盖旧日期；姓名类型提示不靠同词、旧预约slot兼容；版本/CSRF/跨身份/撤回/过期/原子回滚；重要旧事无答案仍进入语言无关事实核对，普通问候不强制审查；SDK请求使用MockTransport而非外网。

合成追踪（不是实际LLM理解成绩）：today=2026-11-11、Asia/Tokyo，预置分析把「来週火曜日に面接があります。」标为weekday/1/1，程序算2026-11-17，候选fact保持原句；「我明天在合成北京市有面试。」或「明日、合成東京で面接があります。」标relative_days=1后得到2026-11-12。确认前不检索，确认后另会话仅使用白名单ID；回复固定fixture为「うん、ゆっくり話してね。」。**真实模型原回复、调用耗时、token/账单：未采集（本轮真实模型/天气/支付调用0）**。上述秒数是测试执行时间，不是模型推理速度。

初次新增单元测试收集因装饰器多写冒号产生1个SyntaxError/退出2，改正后44项通过；该失败保留，不视作生产接口失败。开发中先929/55原回归通过，之后随新用例/数据流改动到990/71、991/72、995/74，PG先198与200、206通过；补充跨日同原文、上下文只投影文本、日期保留范围、姓名/旧元数据兼容、语义回复入口后执行上述最终完整检查。重跑因这些具体变动，不反复采样模型挑成功；各轮计数重叠，不累计。

M5仍未整体验收，M6未开始。结构合法/置信阈值不是语义真实支持或日期解释准确率；SDK Mock只证明请求/解析边界，不证明真实Gemini接受所有schema或在4秒内完成。真实中日提取/否定/引用/时间/选择/审查质量、陌生表记与跨语言召回、成本/延迟、独立新集/评审、其余语言规则迁移均未验收。旧15漏检/5误拦截/1未决、503、8.003秒超时/CLI退出1及全部历史失败/未验证项保留。未上传密钥、真实对话/记忆、评分原件、数据库或运行导出。

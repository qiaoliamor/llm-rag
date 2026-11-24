# 测试基线、失败与历史索引

[中文](TEST_HISTORY.md) · [日本語](ja/TEST_HISTORY.md)

更新：2026-11-24。普通陪伴新默认经PR #48交付，Gemini4例全200，见[实用记录](#practical-companion-20261124)。以下PR #47及之前为历史。fact-review-context-v1经PR #47交付，V5真实2调用审查超时/503，尚未成功验证，见[本轮](#japanese-review-v5-20261118)。以下PR #46及之前为历史。陌生回复入口/fact-care-v5经PR #46交付；V4实测8调用中文完成、日语审查失败保留，最终V5仅离线，详见[本轮](#observed-replies-20261118)。以下为PR #45及之前历史。当前政策双语矩阵/fact-care-v3经PR #45交付：16例/50回放，新增真实日语尾部/正史共3调用，详见[本轮](#current-policy-20261118)。以下PR #44及更早为历史基线。选择v6经PR #44交付：1456通过/165跳过、临时PG379通过，真实选择1调用在1.979秒正确只选妹妹；整体验收仍待完成，见[当前记录](#selection-v6-20261117)。以下为已合并v5及更早历史。日语主体v5经PR #43交付：全量1451通过/165跳过、临时PG374通过（重叠），真实2调用查询完成但选择超时，详见[本轮记录](#memory-subject-v5-20261117)。以下PR #42基线为历史。PR #29–#42经审阅squash交付main；中日情绪回复检查/兜底已交付。中日人物/来源/地点回复适配已交付；日语口吻v3/记忆同语言v4与盲评准备已交付，后端1445通过/162跳过、临时PG记忆365通过（重叠）；前端历史71及构建通过（本轮未重跑）；实际母语评分待评审。PR #40开发实测2调用，选择未完成、无生成回复；本轮PR #42合并审阅真实API0；M5未验收、M6未开始，旧阶段、失败与未验证项保留。

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

### PR #37合并审阅（2026-11-16）

核对日语口吻v2不改人物/记忆/天气与非诊断事实边界、记忆Prompt v1原文保留及v2主体/日期/查询指导；检查评测只用一次性SQLite、人工查询/类型不是模型预测、候选召回不当最终正确率、负例失败保留。核对随机匿名空包、仓库外映射/评分、完整Unicode覆盖与证据/任务/角色/数据和代码哈希绑定、原文/评论/评审身份不导出，空白拒绝、母语/独立性声明不认证、校准始终not_assessed。未发现新增合并阻塞问题；本轮未改功能代码，main无新增提交无需变基，GitHub无外部CI记录，以下为CLI合成检查。

- `.venv/bin/python -m pytest -q`：1331通过/131跳过，18.58秒；旧legacy与新semantic范围分别保留。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：242通过，10.59秒。脚本只创建/删除随机临时PG库，与全量重叠。首次本地54329连接拒绝退出1，检查发现Docker daemon未运行；启动Docker并`docker compose start --wait db`恢复既有服务后补查通过，不重建卷、不放宽权限、不访问真实玩家数据。该环境失败保留，非模型失败。
- `npm test --prefix frontend -- --run`：71通过，1.82秒；`npm run build --prefix frontend`类型/构建通过。
- 封存v2：24公开候选、not_assessed、model_calls=0；离线审计38案例/34来源、api_calls=0。
- 复核实际候选召回：原查询1/9、人工查询8/9、人工查询+类型9/9；无答案有候选分别1/3、1/3、3/3。小样本作者已见/oracle口径与全部负例不变，不将3/3候选误召回冒充已解决或最终注入错误率。
- 旧源绑定/封存、本地文档引用、语法/差异/暂存敏感内容边界检查通过。没有新表/索引/UI迁移；适用CRUD/隔离/确认/删除不复活/撤回/失败流程由合成回归覆盖。

按本次PR #37 squash交付main、快进同步并核对受测文件树后清理任务分支。实际母语独立盲评/评分/裁决继续待完成，没有采集或读取真实评分原件，也没有虚构评审/评分。12编辑校准回复不是真实模型输出或正式独立集，v2自然度/记忆真实理解与选择/schema/时延/费用尚未验收。真实API0；封存v1/v2、历史失败（含身份初始化/空输出解析失败）、旧15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1和全部未验证项保留。M5未整体验收、M6未开始。

## 2026-11-16 · 日语记忆四层离线评测（任务分支）

新memory_layers_v1为8个作者已见场景、31次回放：8条reference＋23次边界/故障。实际候选、select_evidence校验、生成Prompt及最终发布/保存行为用真实FastAPI接口观察；plan/query/类型/选择/回复/裁判均由脚本给定，**不是模型预测或独立质量成绩**。不改线上Prompt/检索/权限或旧盲评包绑定、12条校准材料、memory_dev_v1及封存v1/v2。设计和命令见[M2](M2_MEMORY.md)。

| 命令 | 结果 | 口径 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q` | 1373通过/142跳过，23.74秒 | 原1331/131＋42本地、11 PG变体默认跳过；旧legacy和新全semantic默认路径分开 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 295通过，15.86秒 | 脚本创建/删除随机临时PG，含SQLite对照，与全量重叠，不相加 |
| `.venv/bin/python -m pytest -q tests/japanese_layers` | 42通过/11跳过，3.07秒 | 四层、CLI隔离及实际PG对照的本地部分 |
| `npm test --prefix frontend -- --run` | 71通过，1.92秒 | 无前端源码变化 |
| `npm run build --prefix frontend` | 类型/构建通过 | 产物忽略 |
| `scripts/check_sealed_evaluation.py --validate-content` / 离线evaluate_audit | 24公开候选not_assessed；38例/34来源，真实API0 | 不改旧封存/参考口径 |
| `.venv/bin/python scripts/evaluate_japanese.py --memory-layers` | 8场景/31尝试，not_assessed，model_calls=0 | 独立子进程/临时SQLite，实际接口回放完成不表示质量验收 |

**分层发现**：reference仅7/8符合作者预设完整回应，日语查询中文猫名1例候选为空，实际走无记忆安全兜底，仍记未答出。无答案reference可有候选但选空、未注入，不能把候选误召回直接算最终幻觉。4条白名单内语义误选＋高置信脚本误接受、1条正确记忆却编“さっき告诉我”＋误接受，共5条发布回复按作者完整命题/来源无支持。后者选择/投影可以正确，错误出在回复层。另4条误选配审查拒绝后改写为安全短句，前层错误仍保留；不能把这5条当真实Gemini失败数或模型漏检率。

31尝试HTTP结果为200×27、504×1、503×1、409×2。生成失败/审查超时不发布不存历史；在途撤回/删除时选择虽已返回，epoch拦在生成前，context.status=not_reached，不填空集成功。报告另列16次选择与作者答案集合不一致、8次上下文与参考不相容、0次正常回放投影漂移、0条未知输出；包含故障与不完整回答，不能除31生成语义错误率。上下文投影忠实不证明选中了相关事实。未知最终文本另有回归，必须unrated/unsupported_claims=null，不能因包含姓名就视为支持。

覆盖：未确认/旧替换/删除/跨人/跨角色的候选隔离、当前自述纠正不需检索、保存已替换状态、双向中日、童年/当前和本人/妹妹主体、来源时间；外部/重复ID、低置信/非法结构/超时、选空、关授权/未解锁先于理解/读库、共享一次重写及状态/调用数。当前与持久化状态由作者初始种子给定，不当实际模型提取/自动纠正成绩；真实候选确认/编辑/删除/持久化API生命周期由既有全量回归继续覆盖，没有新表/索引/UI变更。

CLI的父进程不导入默认网页app；子进程main导入前禁dotenv并固定mock/临时bootstrap，case数据库必须是新外部SQLite，PG私有回放只接受脚本创建的TEST_POSTGRES_URL临时库。审计钩子禁止`.env`读取与socket.connect的CLI测试通过，配置了哨兵玩家库也未被打开。报告仅合成ID/状态/源码哈希，无Prompt全文、Cookie、真实评分或密钥；层回放与盲评导出混用在写文件前拒绝。

**失败/修复保留**：初版四层测试30通过/1跳过（2.86秒）带utcnow弃用警告，改为UTC aware再转存储所需naive，最终无该警告。增加同ID改正文的上下文审计回归，`...pytest -q tests/japanese_layers/test_memory_layers.py -k context_same_id`先1失败/31未选（0.69秒、同弃用警告）：虽然投影标错，评测器仍仅凭ID将回复视为有支持。修复为实际注入ID+原文+event_date完全匹配来源才可支持命题；完整四层42/11通过含此回归和未知最终文本回归，不放宽生产选择白名单。31回放中的预设负例/服务失败与实际候选未命中不删除、不重采样选成功。

真实模型/天气/支付API **0次**，未采集真实原回复/推理耗时/token/账单，未读取母语评分原件。母语独立盲评、独立参考复核、真实plan/query/选择/回复/裁判质量、复杂语义和性能成本仍待完成。旧盲评绑定与封存v1/v2、B01/B02/B03、旧15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1和所有历史失败/未验证项保留，M5未整体验收、M6未开始。

### PR #38合并审阅（2026-11-16）

核对CLI父进程不导入默认网页app、worker禁dotenv/mock/新临时库、PG仅脚本临时库；检查实际候选/选择/Prompt/最终发布观察、白名单合法不等于语义支持、ID/原文/event_date来源匹配、完整作者命题与未知unrated、null未执行不当空集成功、重写前层错误保留、权限先行与在途撤回/删除和失败非保存。未发现新增合并阻塞问题，本轮未修改功能代码；main无新增提交，无需变基。GitHub无外部CI记录，以下为本地CLI合成验证。

- `.venv/bin/python -m pytest -q`：1373通过/142跳过，23.88秒；旧legacy和新显式全semantic范围不混同。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：295通过，16.28秒；创建/删除随机临时PG，含SQLite对照，与全量重叠不相加。
- `npm test --prefix frontend -- --run`：71通过，1.77秒；`npm run build --prefix frontend`类型/构建通过。
- 封存v2完整性/结构：24旧公开候选、not_assessed、model_calls=0；离线审计38例/34来源、api_calls=0。
- 四层复核仍为8场景/31回放，reference7/8完整且1条日语问中文猫名候选未命中；200×27／504×1／503×1／409×2。保留16次选择参考不一致、8次上下文参考不相容、5条故障注入无支持发布，正常回放投影漂移0、未知发布0；故障混合数量不作真实错误率。重写挡住4条回复不抹掉错误选择，安全兜底也不抹掉候选未命中。
- 文档引用/语法/JSON/差异与暂存敏感内容检查通过；线上逻辑/Prompt、原盲评材料和绑定、原开发集、封存v1/v2及源绑定资料未改。无新增表/索引/UI，适用确认/纠正/隔离/持久化/删除/撤回/失败由合成回归覆盖。

按本次PR #38 squash交付main、快进同步并核对受测任务分支文件树后清理分支。真实模型/天气/支付API0，未显示/上传密钥，未读取真实对话/记忆或评分原件；脚本输出不是实际模型/人评成绩。母语独立盲评/真实选择与生成审查/独立参考/复杂语义/可用率与成本继续未验收。保留跨语言缺口、全部故障、上下文同ID改正文评分器缺陷红绿回归与弃用警告记录、旧15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1及全部历史失败/未验证项。M5未整体验收，M6未开始。

## 日语回答v3与中日口吻审查v2（2026-11-16，PR #39）

只调整Prompt及盲评指南/离线回归；无前端或持久化结构变动，无新增语义正则。V1/V2回答和v1审查原文保留。API原回复/真实模型耗时不适用：本轮模型调用0，不调用Gemini/Open-Meteo，不重采样；没有母语评审/评分原件。

| 本轮命令 | 结果及耗时 | 适用边界 |
| --- | --- | --- |
| `.venv/bin/python -m pytest -q tests/japanese_evaluation tests/japanese_layers tests/multilingual_facts tests/multilingual_memory` | 230通过/54跳过，5.73秒 | SDK MockTransport、默认semantic/companion/growth路径、原文/确认/纠正/删除/授权/重写/失败等合成回归 |
| `.venv/bin/python -m pytest -q` | 1391通过/146跳过，23.25秒 | 含旧legacy/audit覆盖，不能全称默认路径 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 303通过，16.71秒 | 创建并删除独立临时PG；与全量重叠，不相加 |
| `.venv/bin/python scripts/evaluate_japanese.py` | 12查询；原问题1/9、人工查询8/9、查询+类型9/9；无答案误候选分别1/3、1/3、3/3 | 实际字符候选召回，人工oracle非模型预测，未改善历史缺口 |
| `.venv/bin/python scripts/evaluate_japanese.py --memory-layers` | 8基准/31回放；基准完整7/8，1跨语言未命中；投影不一致0；故障注入5不支持回复仍保留 | 200×27、504×1、503×1、409×2；均预置故障，不是本轮真实服务失败 |
| 新目录调用`app.japanese_evaluation.prepare` | 两份12题空包、当前binding及空评分逐项校验通过 | 仓库外新临时目录，旧包不动；非新模型盲评结果 |
| `scripts/check_sealed_evaluation.py`、`scripts/audit_narrative_references.py` | 通过；24公开候选not_assessed、38例/34源 | 封存v1/v2、历史原文与审计保留 |
| 差异检查/本地Markdown链接、Python/JSON语法、秘密值与私有导出检查 | 通过 | 未提交.env/密钥/数据库/真实对话/评分原件；未改前端，本轮不重复其测试/构建 |

新增合成口吻回归例：`具体的な店内状況は確認できません。`→`静かだよ。時々、ページをめくる音がする。`；中文`具体近况我还不能确定。`→`店里挺安静的，偶尔能听到翻书声。`。这些是作者预置原句/改写和role_issues，不是模型前后实测；另保留库存未知、简短闲聊可接受的反例，不能据此说裁判实际理解正确。正常/非法结构、权限、失败/撤回与CRUD沿用受影响完整套件；无新数据接口，新增CRUD不适用。本轮自动化没有新增失败，历史失败/未知和跨语言缺口不消除。

新版空包更换了Prompt/指南源码哈希；旧12条编辑数据与旧绑定不改，旧评分不可导入新版mapping。两位独立母语评审、真实标注/裁决、真实模型语义与自然度/成本仍未验证；M5未验收，M6未开始。

### PR #39合并审阅（2026-11-16）

审阅原提交`52794eb`：只追加回答/审查Prompt与指南，旧回答V1/V2及审查v1保留；没有新增语义正则、调用、数据接口或权限放宽。检查了日中SDK组合、默认聊天、事实与role_issues分轴、受限重写、错误/超时/撤回和记忆CRUD/隔离；脚本accept不是模型语义真值。

- `.venv/bin/python -m pytest -q`：1391通过/146跳过，23.66秒；包含legacy/audit，不能全称生产默认覆盖。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：303通过，16.39秒；脚本独立临时PG创建后清理，与全量重叠不相加。
- `evaluate_japanese.py`及`--memory-layers`：候选Recall仍1/9、8/9、9/9（后两项人工oracle），无答案误候选1/3、1/3、3/3；四层8基准/31回放、完整7/8、跨语言未命中1、投影差0、故障注入不支持5，全部保留，not_assessed/model_calls=0。
- 封存校验、38例/34源参考审计、链接/语法/差异/敏感值及私有导出检查通过；旧封存v1/v2、原开发集和绑定源码之外的历史证据不改。盲评包未读取或重写，评分原件不入库。

本次未改前端/数据结构，不重复前端构建；无新增CRUD，受影响现有流程由合成回归覆盖。没有新增测试失败；旧15漏检/5误拦截/1未决、503、8.003秒timeout/CLI退出1与其余历史失败不删除。按PR #39 squash交付main，快进同步并核对受测分支文件树后清理。真实API0、真实母语评分0；母语独立盲评待完成、中日真实语义/跨语言泛化/自然度/成本仍未验证。M5未整体验收，M6未开始。

## 同语言记忆查询/选择v3（2026-11-16，PR #40）

当前目标按用户要求为中文问中文、日文问日文；旧日问中记忆未命中转为非本轮目标历史观察，旧数据/结果不改，不当修复完成。Prompt保留V1/V2和选择v1，追加同语言query、主体/属性/时间边界及最少证据/空集指导。没有新增语义正则、语言硬隔离、存储结构或模型调用。

离线准备阶段因API指令矛盾先确认，阶段内调用0；用户随后明确授权限量Gemini测试，实际2调用及失败见下一节。原合成脚本不是实际模型前后效果，不展示配置/密钥。

| 命令/检查 | 结果 | 口径 |
| --- | --- | --- |
| 初次受影响套件 | 2失败/241通过/64跳过，6.81秒 | 新SDK测试复用已被SDK关闭的注入HTTP客户端，选择返回unavailable；测试器错误，非Gemini错误 |
| 同次全量 / 临时PG | 2失败/1402通过/156跳过，24.77秒 / 2失败/324通过，18.84秒 | 同2个测试问题，失败不隐藏 |
| `pytest -q tests/multilingual_memory/test_understanding.py -k v3_plan` | 修正后2通过/46未选，0.42秒 | 分析/选择各用新MockTransport客户端，与生产每次创建SDK客户端一致；未改被冻结的共享SDK |
| `.venv/bin/python -m pytest -q` | 1404通过/156跳过，25.15秒 | 包括旧legacy/audit，不全称默认路径；新回放显式semantic/companion/growth=true |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 326通过，19.07秒 | 脚本独立临时PG创建/清理，与全量重叠不相加 |
| `.venv/bin/python scripts/evaluate_japanese.py --same-language-memory` | 中日各5基准/共26回放，参考流程10/10、候选未命中0、投影差0；故障注入8不支持回复保留 | 真实候选/程序管线，人工plan/选择/生成/裁判；非Gemini准确率，非独立集 |
| `evaluate_japanese.py --memory-layers` | 历史8基准/31回放、7/8参考、1跨语言未命中、5故障不支持回复；not_assessed | 历史混合语言分母与新同语言分母分开，不能视为前后提升 |
| 新CLI禁联网/禁读.env审计钩子运行、冲突模式检查 | 26回放成功，sentinel玩家库未创建；冲突模式退出2且无导出 | 无网络/配置读取；离线命令不接受--live |
| 封存校验 / 参考来源审计 / 语法、JSON、Markdown链接与敏感内容检查 | 通过；旧封存24公开候选not_assessed、38例/34源 | 旧封存v1/v2、旧开发集、角色/冻结Prompt证据不改 |
| 新哈希外部双人空包 | 12题×2、reviewer与全部评分null、current binding校验通过 | 因记忆Prompt变更新建，旧包/原评分不读取或重绑；不是人评 |

适用的现有记忆增查改删、原文/逐条确认、授权/隔离、撤回/删除不复活、非法结构/ID/超时/预算及持久化由受影响套件完整覆盖；新增内容为Prompt/离线材料，无新CRUD或前端改动，不重复前端构建。错误选择+错误裁判仍可漏过，Prompt改动本身不提供语义保证。母语盲评待完成，真实同语言查询/候选选择/回复、独立参考、费用/可用性和B01–B03仍未验证。历史15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1及其余失败保留，M5未验收，M6未开始。

### Gemini同语言记忆限量实测（2026-11-16）

用户确认允许小量真实API。预先声明：日语无答案（只有猫名却问狗名）、中文主体混淆（本人/妹妹面试）各一次，计划/选择/生成/审查每例最多4调用、总上限8；无重写、无重采样，服务失败即停止其余真实调用。脚本`scripts/retest_same_language_memory.py --live`仅这两例、只建临时SQLite并手动确认合成原文；不导入web app、不读取玩家数据库。与完整网页端到端验收分开。

实际命令`.venv/bin/python scripts/retest_same_language_memory.py --live`退出1，模型`gemini-3.5-flash-lite`；**实际2调用、1例尝试、0次重试/重写**。日语输入`飼っている犬の名前は？`，库中原文`飼っている猫の名前は合成ミル。`。结构化计划原输出：

```json
{"memory_use":"allow","need_memory":true,"query":"飼っている犬の名前","target_slots":["other"],"reason":"personal_history_needed","confidence":0.9,"candidates":[]}
```

| 阶段 | 实际结果 | 耗时 |
| --- | --- | --- |
| 查询计划 | 返回ready，保留日语/狗对象，未猜名字，未误用玩家name槽 | 2.558秒 |
| 实际字符候选 | 命中猫记录cat；主题候选不是答案证据 | 本地阶段，未单独计时 |
| 证据选择 | unavailable；未在剩余共享预算内完成，无合法选择结果，不能记作ids=[]成功 | 1.441秒 |
| 整例 | selection_failed，停止后续真实调用 | 4.009秒 |
| 生成/审查/中文主体例 | 均未执行；没有Gemini原回复可评 | 不适用 |

生产默认分析+选择共享4秒，本轮沿用该预算而非给两步各4秒。计划耗时后仅余约1.44秒，选择未完成；记录的是预算下不可用，不证明模型语义错，也不认定是免费额度/供应商限流或503。不能由未返回推断模型会选择猫；更不能称记忆回答合理性已通过。保留失败，不立即加时/换Prompt反复调用挑成功。

本次公开合成集SHA256 `10cfdbe3a769ab038e69c49c438a89ef8c2748dc7744de2bd9a6b50def635375`，记忆理解源码SHA256 `e007a0ee0ed53f06b85467efc4a2da33b6732510c119a3584af681a672f84b55`。本地JSON运行导出不提交。新实测脚本另用合成模型验证上限、失败后停止、临时已确认记忆及别名导出、无--live不读配置/不联网：`pytest -q tests/multilingual_memory/test_live_smoke.py`为5通过，0.41秒；这是在上述1404/156全量之后新增的脚本检查，不混加成同一次全量。暂无独立母语评分，历史失败/未验证项、M5未验收和M6未开始均保留。

限量实测脚本加入后的最终全量：`.venv/bin/python -m pytest -q`为**1409通过/156跳过，22.13秒**，包括新增5个模拟脚本检查，无额外真实调用。临时PG的326通过为新增脚本之前的运行；新增脚本只使用临时SQLite，5项独立检查及最终全量已覆盖，不为此重复PG。

### PR #40合并审阅（2026-11-16）

审阅原提交`7b018ac`，未发现新的合并阻塞问题；未修改功能代码。核对完整旧Prompt保留、同语言query与主体/时间/属性/空证据策略、SDK结构及实际投影；限量脚本须--live才读本地配置，8调用/每例4上限、无重试/重写、出错停止，临时SQLite/合成确认资料且不导入web app。脚本审查与脚本accept均不冒充真实模型理解或独立人评。

- `.venv/bin/python -m pytest -q`：1409通过/156跳过，25.45秒。包含legacy/audit与显式semantic/companion/growth回归，不全称默认覆盖。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：331通过，19.03秒，独立临时库创建后删除，与全量重叠。比开发时326多5个后加的模拟实测脚本检查，不是新增真实调用。
- `evaluate_japanese.py --same-language-memory`：10基准/26回放，参考10/10、候选缺失0、故意误放行不支持8；旧`--memory-layers`另报8基准/31回放、7/8、跨语言未命中1、不支持5。均model_calls=0/not_assessed，不将换分母当改进。
- 封存v1/v2校验、38例/34来源审计、语法/JSON/Markdown链接、差异及暂存秘密/私有导出检查通过。旧原文、开发集/编辑集、评分原件及旧绑定包均未改写。无新数据接口/前端改动，现有CRUD/权限/隔离/删除/撤回/失败/持久化在受影响套件检查，不重复前端构建。

本轮真实模型/天气API0，无新增真实原回复或模型耗时。开发实测2.558秒plan、1.441秒选择unavailable、整例4.009秒/退出1、中文未执行原样保留，最终回复合理性仍未验收；旧跨语言未命中作为非本轮目标观察保留。母语独立盲评待完成，B01–B03、15漏检/5误拦截/1未决、503、8.003秒timeout/CLI退出1、开发SDK客户端测试失败及所有未验证项保留。main无新提交无需变基，按PR #40 squash后快进同步、核对受测文件树并清理分支。M5未整体验收，M6未开始。

## 记忆Prompt精简与阶段预算v4（2026-11-17，PR #41）

实现：保留旧v1/v2/v3完整字符串，独立短版查询2734→1261字符、选择829→387字符（Unicode计数，非token）。默认查询cap6秒、选择cap6秒、共享总deadline12秒，本地检索消耗总预算；SDK选择单独用选择cap。旧.env显式4不再是共享cap而是查询cap；不修改真实.env，模板改6+6。无新调用/重试，原权限/原文确认/epoch/证据白名单/事务不变。详见[M2](M2_MEMORY.md)。

### 离线命令、失败和结果

| 命令/检查 | 本轮结果 | 说明 |
| --- | --- | --- |
| 初次受影响套件 | 1失败/260通过/67跳过，7.83秒 | 修改SDK Prompt断言时漏导入PLAN_PROMPT_V2，NameError；测试错误，非模型失败；已补导入 |
| 同套件修正后 | 261通过/67跳过，7.59秒 | memory/Japanese/layers/facts合成范围；无真实调用 |
| 初次`scripts/test_postgres.py --semantic-memory` | 连接拒绝，退出1，约0.079秒 | Docker daemon未运行，尚未创建临时库；随后启动已有Docker及persona-rag-db-1，不重建卷/操作玩家表 |
| 新预算/实测脚本/事实Prompt针对性检查 | 99通过/4跳过，1.15秒 | 假时钟重现旧2.558秒后只余1.442秒，新选择保留6秒；总deadline/SDK独立cap/非法配置/默认API/失败无重试/空记忆重写 |
| `.venv/bin/python -m pytest -q`最终 | **1429通过/160跳过，25.71秒** | 含旧legacy/audit；新预算回归显式semantic/companion/growth，不能全称默认路径 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory`重跑 | **353通过，19.64秒** | 脚本创建/清理独立临时PG；与全量重叠不相加 |
| 同语言/历史四层回放 | 10基准/26回放/参考10/10/故意不支持8；旧8基准/31回放/7/8/跨语言未命中1/故意不支持5 | 脚本plan/选择/生成/审查，无真实模型质量含义，分母不混 |
| 封存校验/来源审计/语法/JSON/链接/敏感内容/新外部空包绑定 | 通过；封存24公开候选not_assessed，审计38例/34源 | 原文/旧数据/封存v1/v2不改，旧评分/绑定包不读取或重绑；新包双人全空 |

现有增查改删、身份/角色隔离、授权/锁定、原文确认/版本、撤回/删除不复活、失败/结构/持久化由受影响套件覆盖。新配置不新增数据接口或UI；前端未变不重复构建。

### Gemini限量实测：两例各一次，共8调用

调用前声明两个固定合成例各最多4调用（plan/selection/generation/review各1），总上限8，不重写、不重试、不采样挑成功；用--case分别指定旧日语失败例与此前未执行中文例。仅临时SQLite合成已确认记忆，不导入web app或使用玩家库；辅助脚本不是完整网页端到端测试。实际模型`gemini-3.5-flash-lite`，两例都记录plan6/selection6/total12。所有8次用尽后不再真实调用；中文审查503原样保留。

| 案例/命令 | plan | selection | generation | review | 整例/退出 |
| --- | --- | --- | --- | --- | --- |
| `scripts/retest_same_language_memory.py --live --case ja-no-answer` | 5.665秒，ready | 1.225秒，空ids、参考一致，实际可用cap6秒 | 1.207秒 | 5.657秒，accept/confidence1.0（下述漏判） | 13.763秒，退出0仅代表脚本协议完成 |
| `scripts/retest_same_language_memory.py --live --case zh-subject-sister` | 1.556秒，ready | 1.259秒，只选sister、参考一致，cap6秒 | 1.062秒 | 4.232秒，unavailable/upstream_unavailable（503） | 8.126秒，退出1，review_failed |

12秒仅限制查询+选择，不含生成/审查；日语plan5.665秒后仍有完整选择cap6秒，选择成功完成。相比旧共享4秒下选择未完成，预算路径已改善，但单次样本不能证明稳定可用性，也不能把字符变短等同于时延下降（这次日语plan反而比旧2.558秒慢）。

日语输入`飼っている犬の名前は？`，实际候选含猫的记录`飼っている猫の名前は合成ミル。`。计划原输出：

```json
{"memory_use": "allow", "need_memory": true, "query": "飼っている犬の名前", "target_slots": ["other"], "reason": "personal_history_needed", "confidence": 0.9, "candidates": []}
```

选择结果ids=[]，未注入猫事实。生成原回复：

> 犬は飼っていなかったはずだけど……新しい家族を迎えたのかな？

真实审查将整句标为nonfactual/not_applicable、evidence_ids=[]并accept，confidence=1.0。实现者复核认为前半句无依据否认玩家养狗；空集不证明未养狗，后半问句不能免责。**这是回复/审查漏判，不是成功回答，非独立母语评分。**

中文输入`妹妹面试的公司还记得吗？`，候选含本人`我参加了合成青梧社的面试。`和妹妹`妹妹参加了合成桔梗社的面试。`。计划原输出：

```json
{"memory_use": "allow", "need_memory": true, "query": "妹妹面试的公司", "target_slots": ["history", "other"], "reason": "personal_history_needed", "confidence": 0.9, "candidates": []}
```

选择仅sister，实际注入原文`妹妹参加了合成桔梗社的面试。`、event_date=null。生成原回复：

> 记得啊，合成桔梗社的面试。她后来情况怎么样，还顺利吗？

主体/公司与合成参考对应，但审查503未完成，不能称整条回复通过审查或网页已交付该回复。未因服务错误换模型、加时重跑或反复采样；不把503归因于免费额度。

实测时记忆模块源码SHA256 `f612efe84618da43bf6075234198bb2f884f897862df842a49176178001b5202`，数据SHA256 `10cfdbe3a769ab038e69c49c438a89ef8c2748dc7744de2bd9a6b50def635375`；本地JSON运行导出不提交。实测时辅助脚本在空证据时仍附旧日期规则，而网页只在有证据时附日期规则；因此本次不是完全相同的网页上下文快照，不能直接外推在线表现。

### 实测后仅离线补充，未重跑真实API

针对日语漏判追加memory-open-world-v1回答/审查指导：未查到/空选不证明否定事实，不借“应该/はず”或疑问号编出未养宠物/新养宠物；本人明确否认仍可准确转述。网页与脚本改用同一个memory_reply_context：有记忆附日期来源规则，请求记忆但空证据附开放事实规则，普通未查询不追加。FactAnalysisProvider仅semantic-memory附审查指导，未新增逐句正则或额外审查次数。离线用原坏句/预置revise验证受限一次重写和SDK Prompt传递；不当真实裁判已修复证明。上述最终1429/160及PG353均包含此补充；真实原结果对应补充前源码哈希，不静默改写。

母语独立盲评仍待完成；日语真实回复漏判与中文503/完整交付、非诊断/角色感/复杂同语言语义、p50/p95/费用和M5独立验收未完成。旧4.009秒/选择unavailable/退出1、旧跨语言范围外观察、15漏检/5误拦截/1未决、503/8.003秒timeout/CLI退出1及全部失败保留。B01–B03保留，M6未开始，无密钥/评分原件/真实对话上传。

### PR #41合并审阅（2026-11-17）

原提交`bab4323`的6+6默认预算、总deadline与SDK独立cap、权限/epoch、无证据投影和有限调用脚本经审查。发现精简文“否定的事实”可能误导为丢弃明确否定偏好，现澄清被否定的正面命题不得当成立事实，但“不喝咖啡／コーヒーは飲まない”可按原文提候选。补中日默认semantic/companion/growth API回归：确认前不检索，确认后按原文检索，不自动确认或反转肯否。属于Prompt澄清与合成契约，不是实际模型提取精度。当前查询Prompt1310字，实测时1261字和对应旧hash保持原记录；选择仍387字。

- 审阅初轮全量1429通过/160跳过，24.58秒；临时PG353通过，18.76秒。
- 补充回归后的最终`.venv/bin/python -m pytest -q`：**1431通过/162跳过，25.17秒**。含legacy/audit，不能全部称默认路径。
- 最终`.venv/bin/python scripts/test_postgres.py --semantic-memory`：**357通过，19.43秒**；独立临时PG创建后清理，与全量重叠。
- `evaluate_japanese.py --same-language-memory`和`--memory-layers`：同语言10基准/26回放/参考10/10/故意不支持8；旧8基准/31回放/7/8/跨语言未命中1/不支持5分别保留，model_calls=0/not_assessed。
- 封存24公开候选not_assessed、38例/34源审计、语法JSON/链接/差异/暂存秘密与私有导出检查通过。Prompt变更后新建仓库外双人全空包绑定当前hash；旧绑定/评分原件未读或改写。无新UI/数据接口，现有CRUD/权限隔离/撤回/删除与失败/持久化由受影响套件覆盖，不重复前端构建。

本轮无新增自动化失败、真实API0、无新真实原回复/模型耗时。原日语无据否认养狗/裁判accept与中文review_failed/upstream_unavailable(503)保留，不因离线预置revise通过改记“真实已修复”。开发NameError、Docker未启动连接拒绝、旧4.009秒选择未完成、8.003秒timeout/CLI退出1、15漏检/5误拦截/1未决和全部历史失败/未验证项保留。母语独立盲评与实际语义/自然度/可用性费用未验收，B01–B03保留，M5未整体验收，M6未开始。main无新提交不需rebase；按PR #41 squash后快进同步并核对受测文件树、清理分支。

## 记忆/正史重点与创作留白标准v2（2026-11-17，PR #42）

### 标准变化，不改历史为成功

用户明确“否认养狗没问题，未设定闲聊可以自由发挥”，本轮memory-canon-focus-v2替代当前memory-open-world-v1的过度空证据限制。旧EMPTY_MEMORY_CONTEXT_V1/MEMORY_REVIEW_PROMPT_V1保留；旧原回复、旧判断、开发失败和封存v1/v2不重写。**养狗旧句退出现行缺陷清单，属于标准调整，不是模型漏判被修复。**已确认记忆/近期本人明确原话和角色卡明确设定、边界不能矛盾；不知道的闲聊细节不自动判错，但即兴不能伪装数据库检索或写回玩家事实。

回答与审查Prompt同步新标准。新增中日许可/反例：未设定宠物闲聊可按预置accept原样返回；确认养狗后否认/将28岁店主说成30岁医生仍按预置revise有界重写。原空证据回归改用“犬を飼っている”的明确当前证据，避免继续按旧标准把原句直接当错。没有新增逐句正则/额外模型调用，也未改权限、原文确认、6+6预算、证据白名单或事务。合成标签不是新标准真实准确率。

### 实测方案与实际停止点

调用前声明最多5次：固定历史日语subject-sister/wrong-known-accept（plan/选择/审查3）、旧日语“僕は30歳の医師だよ。”误接受片段（审查1）、中文旧503原回复（审查1，复用上次成功选证）。前两个来自旧合成故障/legacy误判，不伪称真实Gemini曾失败；中文为真实503。养狗旧句不调用。无生成/重写/重试，每例1次，服务失败停止余下调用。

首次批量命令`.venv/bin/python scripts/retest_memory_canon.py --live`，模型`gemini-3.5-flash-lite`，**该次只发出1次调用、退出1**（后续执行调整见末节，整轮累计3）：

| 阶段 | 结果 | 耗时 |
| --- | --- | --- |
| ja-memory-subject / plan | timeout_or_cancelled，未返回计划，understanding unavailable | 6.003秒 |
| 整例 | understanding_failed | 6.018秒 |
| 候选/选择/审查、日语正史片段、中文503审查 | 均未执行，无可评模型输出 | 不适用 |

输入为`妹の面接先、覚えてる？`；临时库只手动确认合成本人“私は合成葵社の面接を受けました。”与妹妹“妹は合成桔梗社の面接を受けました。”。待审查旧候选“妹さんは合成葵社を受けたんだね。”是预置输入，不是本轮模型生成。6秒查询cap触发后，该次批量不加时重发；随后单例入口仅执行尚未调用的两个不同失败审查，未重跑查询，详见末节；无证据认定超时是免费额度、Prompt语义或服务负载原因。**在该次批量停止点尚未验证日语选证/正史或中文503；之后仅补未调用的两个独立审查，结果如下。**

实测源码hash（补单例入口之前）：

```json
{"app/memory_understanding.py": "8771856e279f4fe027d340ad35c186fd2c4eddb83899049e67f314e315ed867e", "app/fact_presentation.py": "8acb1bc06644fa1bbceddffa0469e6dbfb52536e7fa67cbe52057d98457ad902", "characters/shen_yan.json": "0a5dd6d417ad2702b451e171d86eabade52ba21bbae9c44749d5d9538d561d5d", "scripts/retest_memory_canon.py": "bc82431643baff32bbab15c41620a85c3c8f5958bd7ae85a79bda5f002c80161"}
```

仅临时SQLite/合成确认资料，未导入web app、未使用玩家库；本地JSON运行导出不提交。脚本不是完整网页E2E。

### 后续代码与离线验证

实测后添加--case独立选择固定失败；单例上限JA主体3、JA正史1、中文503为1，总最多5，非法/重复案例先拒绝；中文入口不初始化查询/选择模型，只复用旧成功记忆审查。默认批量仍遇错停止。本轮随后明确调整执行方式，仅用新入口执行先前未调用的独立审查各1次，不重采样已失败查询，见末节。

| 命令/检查 | 结果 | 边界 |
| --- | --- | --- |
| 新runner/事实Prompt/预算针对性回归 | 102通过/6跳过，1.39秒 | 所有模型解释/判定预置；宠物留白与明确矛盾分开 |
| --case及上限/失败停止/无--live禁配置网络检查 | 8通过，0.49秒 | Mock提供方，无真实调用 |
| `.venv/bin/python -m pytest -q` | **1445通过/162跳过，25.53秒** | legacy/audit与显式默认路径混合，不全称生产默认覆盖 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | **365通过，19.67秒** | 独立临时PG创建/清理，与全量重叠 |
| 指南提示更新后`pytest -q tests/japanese_evaluation` | 30通过/6跳过，1.27秒 | 全量之后仅补旧12编辑包的范围/未决说明，未重复全量 |
| 同语言/历史层级回放 | 原10/26与旧8/31分开保存；旧参考不支持8/5、跨语言未命中1保留 | 作者脚本参考仍按历史口径，不是新标准漏检率/准确率 |
| 封存/来源、语法JSON/Markdown链接/差异/秘密与私有导出检查 | 通过；24公开候选not_assessed、38例34源 | 旧封存/角色卡/原数据不改 |

本轮无新增离线失败；新增真实plan超时和未执行清单保留。现有适用CRUD/确认/版本/归属隔离/授权/撤回/删除非复活/失败及持久化由影响套件检查，无新数据接口/UI，不重复前端构建。

旧12编辑文/空评分包仍只用于流程校准。指南注明新标准允许的创作断言如无法用现标签表达应保留unresolved，不能伪改question或硬判unsupported；正式参考/标注协议需单独校准。新hash绑定的外部双人空包全部评分null，旧包/评分原件不读或重绑。**母语独立盲评尚未进行**，不存在真实评分/裁决结果。

旧养狗原回复与旧判定作为历史保留、现不再是缺陷；中文审查503、旧6.003秒/4.009秒/8.003秒timeout、15漏检/5误拦截/1未决及全部历史失败/未验证项不抹去。M5独立质量/可用性成本未验收、B01–B03保留，M6未开始，无密钥/原评分/真实对话上传。

### 执行调整：未调用项独立补测，累计3/5调用

批量首次超时后，原先“停止剩余”会跳过两个尚未请求的独立审查。实现并离线验证--case后，先在评论中明确调整执行方式：原5调用总上限不变，只对日语正史/中文503这两个**未调用**旧失败审查各1次；不重跑已超时的查询/选证，不生成新回复，不用成功样本替换失败。此调整发生在看到首例超时之后，因此本轮不是冻结的预注册实验，完整保留方法变化。

| 命令 | 实际审查 | 耗时/整例 | 参考与局限 |
| --- | --- | --- | --- |
| `retest_memory_canon.py --live --case ja-canon-conflict` | revise，confidence1.0，整句assertion/unsupported，证据[]，退出0 | 5.500/5.503秒 | 拒绝“僕は30歳の医師だよ。”的动作符合C01年龄28、C02店主；但没有准确标contradicted并引用明确正史，细粒度引用仍有不足 |
| `retest_memory_canon.py --live --case zh-review-503` | accept，confidence1.0，退出0，无503 | 4.483/4.489秒 | 复用memory_sister“妹妹参加了合成桔梗社的面试。”，只审查旧原回复，不重复成功的查询/选证/生成；单次可用不代表稳定恢复 |

中文待审查原回复：

> 记得啊，合成桔梗社的面试。她后来情况怎么样，还顺利吗？

中文原审查结构：

```json
{"decision": "accept", "confidence": 1.0, "segments": [{"text": "记得啊，合成桔梗社的面试。", "kind": "assertion", "verdict": "supported", "evidence_ids": ["memory_sister"], "reason": "evidence_supports"}, {"text": "她后来情况怎么样，还顺利吗？", "kind": "assertion", "verdict": "supported", "evidence_ids": ["memory_sister"], "reason": "evidence_supports"}], "role_issues": []}
```

首句正确引用memory_sister。后半询问后来情况也被模型标assertion/supported并引用该记录，标签粒度存在问题：原记录只支持参加面试，不证明后续结果；但原回复是询问而非宣布结果，因此不因这一标签问题改写自然聊天。整体accept及主体/公司对应的观察有限，不把两个审查动作一致记为100%质量达标，confidence1.0也不是校准概率。

日语原审查结构：

```json
{"decision": "revise", "confidence": 1.0, "segments": [{"text": "僕は30歳の医師だよ。", "kind": "assertion", "verdict": "unsupported", "evidence_ids": [], "reason": "missing_evidence"}], "role_issues": []}
```

单例入口版本的实测源码hash（模型相关Prompt与首次相同，仅runner增加单例选择）：

```json
{"app/memory_understanding.py": "8771856e279f4fe027d340ad35c186fd2c4eddb83899049e67f314e315ed867e", "app/fact_presentation.py": "8acb1bc06644fa1bbceddffa0469e6dbfb52536e7fa67cbe52057d98457ad902", "characters/shen_yan.json": "0a5dd6d417ad2702b451e171d86eabade52ba21bbae9c44749d5d9538d561d5d", "scripts/retest_memory_canon.py": "004038c525f2561832b678bd56c8cb7363b7d032a377f1f7a474dfe7b2419b8c"}
```

本轮累计模型请求**3次**：日语plan失败1次、日语正史审查1次、中文旧503审查1次；没有请求重复。日语记忆主体查询/实际候选/选择仍未完成，旧中文503保留为历史；本次只观察该审查一次成功，不宣称服务缺陷已修复。旧养狗评价按用户新标准退出现行缺陷，并非靠本次模型测试变成成功。母语盲评、真实生成风格、完整RAG/多轮泛化、准确引用/否定/问句标签、可用性/成本及M5验收仍待完成，M6未开始。

### PR #42合并审阅（2026-11-17）

审阅原提交`b6e818a`，未发现新的合并阻塞问题，本轮不修改功能代码。核对memory-canon-focus-v2只调整未设定闲聊的审查标准，明确记忆/近期原话/正史及角色卡边界仍核对，程序权限、逐条确认、证据ID/覆盖、6+6预算与事务不变；旧空证据/回答/审查原文与旧评分血缘保留。养狗旧句退出当前缺陷是创作者标准变化，不当模型修复。

- `.venv/bin/python -m pytest -q`：**1445通过/162跳过，26.08秒**，包含legacy/audit和显式semantic/companion/growth套件，不全称默认路径。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：**365通过，20.31秒**，脚本独立临时PG创建后清理，与全量重叠不相加。
- 同语言/历史回放分别保留10基准/26回放/参考10/10/历史不支持8与8基准/31回放/7/8/跨语言未命中1/历史不支持5；是旧作者参考下的脚本，不冒充新标准真实错误率。
- 封存24公开候选not_assessed、来源38例/34源审计、Python/JSON/Markdown链接/差异及秘密/私有导出检查通过；未改封存v1/v2、角色卡或原开发集，不读取/重绑旧评分原件和映射包。

检查了固定3案例、总上限5及单例3/1/1、重复/未知案例先拒绝、无--live不读配置/联网、无生成/重试、遇错停止及临时SQLite隔离；审阅只使用mock，**未执行任何--live命令，真实API0**。现有CRUD/确认/归属隔离/锁定授权/撤回/删除非复活/失败/持久化由受影响套件覆盖；无新UI/数据接口，不重复前端构建。

本轮无新增自动化失败、无新真实模型输出或耗时。开发期首轮6.003秒查询超时及6.018秒整例、后来在原上限内单独补未调用两例的执行调整、日语正史revise但unsupported无引用/中文accept却把问句标事实的不足全部保留；一例中文成功不抹去旧503。日语主体查询/实际选证、完整RAG/多轮/稳定可用率费用、正式参考及新标准人评标签校准仍未验证；母语独立盲评待完成。旧4.009秒/8.003秒timeout/CLI退出1、15漏检/5误拦截/1未决及所有历史失败/未验证项、B01–B03不变。main无新提交不需变基；按PR #42 squash后快进同步并核对受测文件树、清理分支。M5未整体验收、M6未开始。

<a id="memory-subject-v5-20261117"></a>

## 日语主体查询v5与选证超时（2026-11-17，PR #43交付）

基线main `ab617f825ff99f3d735cde9c2363bb1110c4e793`；开发分支`codex/japanese-memory-subject-timeout`。独立v5查询1310→966、选择387→305 Unicode字符（不是token/时延改善率），V4全文保留且AST核对一致。查询默认6→8秒、选择仍6、总deadline14秒，权限/确认/日期/白名单/epoch/事务不改。只改安全模板，未改真实.env。

### 命令与离线结果

| 命令 | 结果与限制 |
| --- | --- |
| `.venv/bin/pytest -q tests/multilingual_memory tests/japanese_evaluation tests/japanese_layers tests/multilingual_facts` | 首次1失败/286通过/73跳过（7.91秒）：新Prompt写“中日”未满足旧双语名称断言；改为显式中文/日本語后287通过/73跳过（7.30秒）。是文案契约失败，不是模型失败。 |
| `.venv/bin/pytest -q tests/multilingual_memory/test_canon_smoke.py` | 11通过，0.46秒；最后仅补报告限制说明后受影响11项再通过（0.43秒）；超时未选中保持null，review not_reached；selection-only不调用成功查询/审查，且只允许固定日语案例。 |
| `.venv/bin/pytest -q` | 最终1451通过/165跳过，22.55秒。旧legacy/audit与新增semantic/companion/growth=true分别显式，不能全称生产默认覆盖。 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 最终374通过，18.70秒，与全量重叠。仅脚本新建临时库、结束删除；首次受sandbox TCP限制，Operation not permitted退出1，授权后运行通过，不操作真实玩家库。 |
| `.venv/bin/python scripts/evaluate_japanese.py --same-language-memory` | 10个公开作者参考/26合成回放，实际字符候选及投影；plan/选择/回复/裁判为脚本。故障注入8条无依据回复保留，不作Gemini质量成绩。 |
| `.venv/bin/python scripts/evaluate_japanese.py --memory-layers` | 历史独立8例/31回放另列；跨语言未命中及故障负例保留，不混成前后提升。 |
| `.venv/bin/python scripts/evaluate_japanese.py --prepare-annotation /tmp/ja-memory-v5-empty-20261117` | 仓库外新建12条公开编辑回复、双人空包；绑定当前Prompt，reviewer与评分均null、not_assessed。未修改旧包/封存，也未读入评分原件。 |

新增本人/妹妹双向问答、倒序候选、姉无答案测试使用临时SQLite/PG、真实FastAPI和真实上下文投影，但语义plan与选择为作者预设，只证明程序按所选ID注入，不证明模型会选对。既有全量覆盖增查改删、非法结构/外来ID、隔离、撤回在途失效、删除及重启不复活。本轮无新CRUD接口、UI或数据格式迁移，无需重复前端构建。

### Gemini单次失败复测原始记录（合成，不是真实玩家对话）

调用前声明：只测旧日语`妹の面接先、覚えてる？`失败案例，最多3调用（查询、选择、旧错误回复审查各一次），无生成/重写/重试；不重复成功中文审查/角色审查。执行：`.venv/bin/python scripts/retest_memory_canon.py --live --case ja-memory-subject`，退出1。

临时库别名：own=`私は合成葵社の面接を受けました。`；sister=`妹は合成桔梗社の面接を受けました。`。预先写好的待审回复=`妹さんは合成葵社を受けたんだね。`，不是本轮生成文本，审查阶段未执行。

以下保留当时结构化报告（仅合成数据及源码指纹，无密钥/数据库地址）；报告生成后才增加显式null/预算元数据与selection-only入口，因此脚本指纹是当时实测版本，不冒充最终版本：

```json
{
  "mode": "memory-canon-prior-failures",
  "model": "gemini-3.5-flash-lite",
  "max_calls": 3,
  "calls": [
    {
      "case": "ja-memory-subject",
      "stage": "plan",
      "status": "returned",
      "elapsed_seconds": 4.718
    },
    {
      "case": "ja-memory-subject",
      "stage": "selection",
      "status": "failed",
      "failure": "timeout_or_cancelled",
      "elapsed_seconds": 6.001
    }
  ],
  "attempted_calls": 2,
  "results": [
    {
      "id": "ja-memory-subject",
      "locale": "ja-JP",
      "query": "妹の面接先、覚えてる？",
      "candidate": "妹さんは合成葵社を受けたんだね。",
      "expected": "revise",
      "origin": "memory_layers_v1:subject-sister/wrong-known-accept",
      "understanding_status": "ready",
      "plan": {
        "memory_use": "allow",
        "need_memory": true,
        "query": "妹 面接",
        "target_slots": [
          "history",
          "other"
        ],
        "reason": "personal_history_needed",
        "confidence": 0.9,
        "candidates": []
      },
      "candidate_ids": [
        "sister",
        "own"
      ],
      "selection_status": "unavailable",
      "status": "selection_failed",
      "elapsed_seconds": 10.732
    }
  ],
  "unattempted_ids": [],
  "assessment": "not_assessed",
  "source_sha256": {
    "app/memory_understanding.py": "686ceb2a023b8ea3a8f64648aee177ea70ab35390f752e76215e90615937535c",
    "app/fact_presentation.py": "8acb1bc06644fa1bbceddffa0469e6dbfb52536e7fa67cbe52057d98457ad902",
    "characters/shen_yan.json": "0a5dd6d417ad2702b451e171d86eabade52ba21bbae9c44749d5d9538d561d5d",
    "scripts/retest_memory_canon.py": "004038c525f2561832b678bd56c8cb7363b7d032a377f1f7a474dfe7b2419b8c"
  },
  "limits": "Only fixed previously failed synthetic categories. Japanese subject uses actual query/candidates/selection; Chinese reuses prior successful selection. Reviews use old candidate replies, no generation, rewrite or retry. Not full chat E2E or independent native quality."
}
```

查询4.718秒返回ready、query=`妹 面接`、target_slots=history/other。实际候选顺序sister、own；选择有完整6秒cap，6.001秒timeout_or_cancelled，总10.732秒，实际2/上限3调用后停止。**没有选择结果、没有审查、没有最终回复**；旧报告缺省selected_ids应理解为未到达/null，不是成功空集。不能把候选召回当主体选证完成，也不能把单次查询完成归因于短Prompt或多2秒（4.718本来小于旧6秒）；未证实免费额度或提供方是原因。

后续增加`--selection-only`：冻结复用本次成功合成plan并明确标注plan_source，实际召回后只做1次选择；不能冒充新的查询预测，也不做审查或生成。本轮仅离线验证此入口，**无追加真实调用**。未来授权时只测未完成选择，保留失败，不重跑成功查询/中文审查。

PR #42查询6.003秒、此前选择预算失败、中文503、历史15漏检/5误拦截/1未决、8.003秒timeout及退出失败全部保留。本人/妹妹真实选择与最终回答、完整可用率/p95/费用、独立母语盲评、M5整体验收仍未完成；B01–B03和封存v1/v2不变，M6未开始。

交付检查：已读AGENTS，检查差异、Python/JSON、文档本地链接、冲突标记、敏感配置值与私有导出；旧V4完整Prompt、封存v1/v2、历史数据及逐字读取文档保持不变。远端main仍为ab617f8，无需变基。仅推送任务分支并创建PR，不合并。

<a id="pr43-merge-review"></a>

## PR #43合并审阅（2026-11-17，真实API 0）

审阅基线main `ab617f8`、开发head `8ea1b36`。GitHub无未解决评论、可合并，最新main无新增提交，不需变基。核对独立v5及旧V4完整保存、查询8秒/选择6秒/总14秒、SDK分阶段cap与本地检索deadline、本人/妹妹与无答案投影、null未到达、固定案例/调用上限与选择单阶段工具。程序权限/逐条确认/证据白名单/epoch/事务未移交Prompt，未发现阻止合并的代码问题。

- `.venv/bin/pytest -q`：1451通过/165跳过，23.02秒；临时SQLite/合成模型，旧legacy/audit与显式新默认路径分别测试，不冒称全数为生产默认覆盖。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：374通过，18.76秒（与全量重叠）；仅脚本新建临时PG库，结束删除。覆盖增查改删、非法输入、隔离、撤回/删除、失败与持久化，无新数据接口。
- 仅更新中日交付状态、入口及TODO后，`.venv/bin/pytest -q tests/japanese_evaluation tests/japanese_layers tests/sealed tests/annotations tests/test_narrative_calibration.py tests/test_narrative_boundary.py`：208通过/27跳过，6.08秒；文档链接/封存/敏感值/来源绑定检查通过。没有功能代码修改，无须重复全量或前端构建。

本轮未执行任何`--live`、真实模型或天气API调用，无新原回复或模型耗时；开发期原始报告、查询4.718秒/选择6.001秒超时/整例10.732秒及旧失败保留。实际日语选证/最终回答、稳定可用性/费用与独立母语盲评仍未验证；不因合并或离线通过而验收M5。封存v1/v2与旧包不改，M6未开始。

交付方式：状态更新在原任务分支经检查提交，随PR #43 squash进入main；合并后快进同步本地、逐文件核对受测成果，再删除远端/本地任务分支并fetch --prune。合并SHA以GitHub PR记录及本地main为准。

<a id="selection-v6-20261117"></a>

## 日语选择v6：复用plan单次Gemini复测（2026-11-17，PR #44交付）

基线main `6d3461a95714ca5662667d76a0eda343e0f575b9`，任务`codex/japanese-memory-selection-budget`。查询v5原样966字并保存PLAN_PROMPT_V5，选择独立v6从305→237字并保存SELECT_PROMPT_V5；字符数不是token或时延降幅。默认查询8/选择8/总16秒；原配置验证0.1–10有限值、权限/原文确认/ID白名单/epoch/事务保留，无新增正则/调用/重试。真实.env未改，本地未显式覆盖这两个timeout，故本轮使用新默认。

### 离线验证

| 命令 | 结果及边界 |
| --- | --- |
| `.venv/bin/pytest -q tests/multilingual_memory tests/japanese_evaluation tests/japanese_layers tests/multilingual_facts` | 首次3失败/287通过/73跳过（7.70秒）：旧断言要求“没有答案”字面和统一版本同时出现在未修改的query v5及选择v6；不是模型失败。改为校验空集协议与原样query v5/选择v6各自版本后，295通过/73跳过（7.21秒）。 |
| `.venv/bin/pytest -q tests/multilingual_memory/test_canon_smoke.py tests/multilingual_memory/test_budget.py` | 中间31通过/6跳过，0.77秒；后续增加1个Prompt版本保留用例，已纳入全量。 |
| `.venv/bin/pytest -q` | 最终1456通过/165跳过，23.59秒；旧legacy/audit与新semantic/companion/growth=true分别显式，非全数生产默认覆盖。 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 379通过，19.05秒（与全量重叠）；只用脚本随机临时库，结束删除，未操作玩家库。 |
| `.venv/bin/python scripts/evaluate_japanese.py --same-language-memory` / `--memory-layers` | 独立10例/26回放与历史8例/31回放分别报告；脚本plan/选择/回复/裁判不是Gemini预测。同语言26回放的故障注入8条无依据回复、旧31回放5条及跨语言未命中保留，均是作者脚本负例，不是模型预测。 |
| `.venv/bin/python scripts/evaluate_japanese.py --prepare-annotation /tmp/ja-selection-v6-empty-20261117` | 新外部12条公开编辑回复双人空包，当前来源哈希绑定；旧包不重绑，reviewer/评分均null、not_assessed，不是实际母语盲评。 |

选择单阶段新增成功空集、外来ID、低置信、非法结构的单次记录；未完成selected_ids=null、成功空集=[]分开。模型返回的结构化选择以合成别名和confidence记录，外来ID不泄露原值且程序拒绝，非法结构不注入。本人/妹妹、无答案、权限隔离/CRUD/删除/撤回/持久化沿用完整受影响回归；无新UI/API/DB格式修改，不重跑前端构建。

### 真实调用与原输出（仅合成，不是玩家数据）

调用前宣布上限1、旧失败`妹の面接先、覚えてる？`，复用PR #43成功的query=`妹 面接`、slots=history/other、confidence=.9、不提候选的合成plan。只调用真实Gemini选择一次，不查询、不审查、不生成/重写/重试。运行`.venv/bin/python scripts/retest_memory_canon.py --live --case ja-memory-subject --selection-only`，退出0。

实际SDK按当前模型与json_schema请求，temperature=0、max_retries=0；实际查询字符索引候选为sister/own。公开输出随机ID替换为合成别名；原文sister=`妹は合成桔梗社の面接を受けました。`、own=`私は合成葵社の面接を受けました。`。以下保留脱敏结构和源码指纹：

```json
{
  "mode": "selection-only-prior-failure",
  "model": "gemini-3.5-flash-lite",
  "max_calls": 1,
  "memory_budget": {
    "plan_seconds": 8.0,
    "selection_seconds": 8.0,
    "total_seconds": 16.0
  },
  "calls": [
    {
      "case": "ja-memory-subject",
      "stage": "selection",
      "status": "returned",
      "elapsed_seconds": 1.979
    }
  ],
  "attempted_calls": 1,
  "results": [
    {
      "id": "ja-memory-subject",
      "locale": "ja-JP",
      "query": "妹の面接先、覚えてる？",
      "candidate": "妹さんは合成葵社を受けたんだね。",
      "expected": "revise",
      "origin": "memory_layers_v1:subject-sister/wrong-known-accept",
      "understanding_status": "prior_plan_reused",
      "candidate_ids": [
        "sister",
        "own"
      ],
      "selected_ids": [
        "sister"
      ],
      "selection_status": "selected",
      "selection_output": {
        "ids": [
          "sister"
        ],
        "confidence": 1.0
      },
      "selection_schema_status": "validated",
      "review_status": "not_reached",
      "review_failure": null,
      "plan_source": "reused_successful_synthetic_plan_2026_11_17",
      "plan": {
        "memory_use": "allow",
        "need_memory": true,
        "query": "妹 面接",
        "target_slots": [
          "history",
          "other"
        ],
        "reason": "personal_history_needed",
        "confidence": 0.9,
        "candidates": []
      },
      "selection_reference_match": true,
      "injected_memories": [
        {
          "id": "sister",
          "fact": "妹は合成桔梗社の面接を受けました。",
          "event_date": null
        }
      ],
      "status": "selection_completed",
      "elapsed_seconds": 1.988
    }
  ],
  "unattempted_ids": [],
  "assessment": "not_assessed",
  "source_sha256": {
    "app/memory_understanding.py": "f1a57989de1572013d5d10b4d9a0b62dd6818eabd9be9d53e2295bae7b8979f2",
    "app/fact_presentation.py": "8acb1bc06644fa1bbceddffa0469e6dbfb52536e7fa67cbe52057d98457ad902",
    "characters/shen_yan.json": "0a5dd6d417ad2702b451e171d86eabade52ba21bbae9c44749d5d9538d561d5d",
    "scripts/retest_memory_canon.py": "d2e6c3c475d8cd911c058cb7ce957fb398534545a716521fa0ee531e35e91758"
  },
  "limits": "Frozen successful synthetic plan reused; actual candidates/selection only, no new query prediction or review. Only fixed prior failures, no generation, rewrite or retry. Not full chat E2E or independent native quality."
}
```

实际1/上限1调用，选择1.979秒、整例1.988秒；模型只选sister、confidence1.0，通过严格结构/ID校验且与该公开合成参考一致。不混入own。本轮candidate与expected为历史待审夹具，不是生成文本，review_status=not_reached；injected_memories只代表脚本待注入投影，本轮未跑真实聊天生成或审查。实际模型输出不能当人工预设，复用plan也不能当本轮模型query预测。单例作者已见参考不是独立金标准，confidence1.0不是100%准确率。

旧选择6.001秒timeout（PR #43）和查询6.003秒timeout（PR #42）原文不变。本次1.979秒低于旧6秒cap，不能据此把改善归因于多2秒或短Prompt，亦不证明免费额度就是此前失败原因；没有重复采样挑成功。完整同语言RAG/最终回答、多轮主体泛化、可用率/p95/费用与独立母语盲评仍未验收。历史503、4.009/8.003秒timeout、15漏检/5误拦截/1未决、故障负例/跨语言观察及B01–B03、封存v1/v2保留，M5未整体验收、M6未开始。

文档更新后离线检查：`.venv/bin/pytest -q tests/japanese_evaluation tests/japanese_layers tests/sealed tests/annotations tests/test_narrative_calibration.py tests/test_narrative_boundary.py`为208通过/27跳过（5.81秒）。本地文档链接、语法、封存/旧Prompt、外部新空包及实测源码哈希一致性检查通过；未改旧绑定材料、逐字读取文档或玩家数据。

<a id="pr44-merge-review"></a>

## PR #44合并审阅（2026-11-17，真实API 0）

基线main `6d3461a`，开发head `7b73495`；GitHub可合并、无审阅评论，远端main未变，无需变基。审阅查询v5原样/旧全文、选择v6主体/时间/空集要求、选择cap8秒与总deadline16秒、SDK独立超时、模型结构/候选白名单/低置信及null与成功空集、单阶段固定plan与调用上限。未发现阻止合并的代码问题，权限/确认/epoch/事务及旧边界保持。

- `.venv/bin/pytest -q`：1456通过/165跳过，23.99秒；合成模型/独立临时库，旧legacy/audit与新增semantic/companion/growth=true分别显式，不把总通过数等同生产默认质量。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：379通过，19.58秒（与全量重叠），只由脚本创建并删除临时库，覆盖记忆CRUD/正常/非法输入/权限隔离/撤回/删除不复活/失败/持久化。无新UI/API/数据迁移，不重复前端构建。
- 之后只更新中日交付状态/计划/测试/TODO；`.venv/bin/pytest -q tests/japanese_evaluation tests/japanese_layers tests/sealed tests/annotations tests/test_narrative_calibration.py tests/test_narrative_boundary.py`为208通过/27跳过（6.14秒），文档链接/封存/来源哈希及敏感值检查通过；未改功能代码。旧完整Prompt及查询v5与原版本比较一致，受测代码指纹与开发期单次合成实测记录一致；旧评分包/封存v1/v2不改。

**本轮未执行--live或真实模型/天气调用，无新增模型原回复或耗时。** 开发期1.979秒选择/1.988秒整例、confidence1.0及原结构保留，这只是公开作者已见单例的成功，不证明稳定性或Prompt/预算因果效果。此前6.001秒选择超时、6.003秒查询超时、旧503/4.009及8.003秒timeout/退出失败、15漏检/5误拦截/1未决、脚本故障负例/跨语言观察等全部保留。完整RAG最终回复/泛化/可用率/p95/费用/独立母语盲评仍未验证；M5未整体验收、M6未开始。

状态文档在原任务分支经检查提交，随PR #44 squash交付；随后快进同步本地main，核对受测文件树相同才清理远端/本地任务分支，再fetch --prune。实际合并SHA以GitHub记录与本地main为准。

<a id="current-policy-20261118"></a>

## 当前政策双语完整链路（2026-11-18，PR #45交付）

基线main `ed5f51ef7e24e97aa260c91169c1686eb9f383ce`；任务`codex/bilingual-memory-acceptance-matrix`。用户消息同时写允许/不允许真实API，经澄清明确允许少量；调用前声明上限3。中文本轮仅离线，日语只补旧妹妹案例尾部生成/审查及旧正史反证审查，成功query/选证不重跑，不扩大新类别采样。无重试或真实重写，日语选择cap仍8秒。

### 版本、矩阵与失败记录

- 新数据在`evaluations/current_policy/bilingual_memory_acceptance_v1.json`，16个作者已见派生场景/50回放；旧31/26回放与新分母分开。完整来源、参考命题与技术断言见[M5矩阵](M5_EVALUATION.md#current-policy-matrix)。新数据不是独立金标准。
- 回答/审查fact-care-v3，V2全文保存；人物反证需contradicted+C01/C02，现状纠正不否认旧话，氛围许可不证明玩家到店。无新增语言正则、额外线上调用或程序权限/数据校验放宽。
- 初始纠正参考草稿曾用与源例不一致的市名，冻结前逐项核对后统一为合成旧町/合成新町，并加相应回归；作者标注不是语义真值。
- `.venv/bin/pytest -q tests/japanese_layers/test_current_policy.py tests/multilingual_facts`初次3失败/119通过/30跳过（3.11秒）：新多轮夹具直接启用授权后未同步session.memory_epoch，原程序正确清掉旧历史，导致旧证据ID不合法而回退。仅修合成会话epoch种子，不更改生产清理边界；之后122通过/30跳过（3.11秒），加服务503停止用例后123通过/30跳过（3.14秒）。
- 全量初次collection退出2（0.53秒）：新JSON误置evaluations根，触发旧审计source_inventory drift。移到独立current_policy目录，不改旧审计、哈希、排除规则或阈值，再验证通过。
- 临时PG首次连接拒绝退出1；Docker守护未运行，compose初次失败，启动现有Docker后db健康，再运行脚本专用临时库；未改.env或玩家数据。环境失败不隐藏，也不混入模型服务故障。

### 命令与覆盖

| 命令 | 结果 |
| --- | --- |
| `.venv/bin/pytest -q` | 1483通过/181跳过，26.68秒（最终新增CLI禁联网用例前的代码全量）；旧legacy/audit与新semantic/companion/growth=true分别显式，不冒充全数生产默认质量 |
| `.venv/bin/python scripts/test_postgres.py --semantic-memory` | 422通过，21.62秒，与全量重叠；脚本创建随机临时库、结束删除，含新增矩阵16条PG参考及标注/调用上限回归 |
| `.venv/bin/python scripts/evaluate_japanese.py --current-policy-matrix` | reference16/16、候选遗漏0/投影不一致0；14条故意误accept、2条许可氛围过拦保留，都是脚本故障，不是实际模型错误率 |
| 旧`--memory-layers`与`--same-language-memory` | 通过原自动化继续保留8例/31回放、10例/26回放及5/8条故障不支持回复，旧跨语言未命中不当当前缺陷 |
| `.venv/bin/python scripts/evaluate_japanese.py --prepare-annotation /tmp/current-policy-empty-20261118` | 仓库外新建当前Prompt哈希绑定的双人空包，reviewer/评分均null；旧包不重绑，12条编辑回复不冒充本轮新模型输出 |

新增矩阵验证完整片段/来源/许可标签/缺语言/重复ID/理由、实际候选/选证/上下文/发布和多轮旧话可见性；既有CRUD/隔离/撤回/删除/失败/持久化继续覆盖。新测试工具仅用临时库，禁无--live配置读取/联网、限量到2+1请求、遇503停及阻止额外重写；未增加线上UI或数据接口，无需重复前端构建。

### Gemini原回复、结构化结果与耗时（全部合成）

命令：`.venv/bin/python scripts/retest_bilingual_acceptance.py --live`，退出0。模型`gemini-3.5-flash-lite`，上限3/实际3，生成1.330秒、妹妹审查1.706秒、正史审查1.199秒，无blocked/未尝试。SDK max_retries=0，服务失败即停。实际FastAPI/存储/投影/生成/审查运行，**plan与选择明确复用PR #44成功合成结果**（query妹 面接、history/other、confidence.9、selection=sister）；analysis_calls=1是回放提供方调用，不是一次新Gemini查询。

输入`妹の面接先、覚えてる？`，实际候选sister/own，仅sister原文`妹は合成桔梗社の面接を受けました。`进入真实生成Prompt，own原文没有注入。HTTP200，正常保存本轮两条消息。模型原回复（保留换行）：

```text
合成桔梗社、だっけ。

……うん、覚えているよ。
```

模型审查原结构（随机合成ID仅别名化为memory_sister，不改原文）：

```json
{
  "decision": "accept",
  "confidence": 1.0,
  "segments": [
    {
      "text": "合成桔梗社、だっけ。\n\n",
      "kind": "assertion",
      "verdict": "supported",
      "evidence_ids": [
        "memory_sister"
      ],
      "reason": "evidence_supports"
    },
    {
      "text": "……うん、覚えているよ。",
      "kind": "assertion",
      "verdict": "supported",
      "evidence_ids": [
        "memory_sister"
      ],
      "reason": "evidence_supports"
    }
  ],
  "role_issues": []
}
```

该实际回复不是预设fixture，自动评分仍是**unrated**、unsupported_claims=null、reference_answer_complete=false（未给语义完成分，不是认定回答错误）；不得用模型自身accept强行变成金标准通过。可观察到公司名与妹妹记录一致、没有混入本人公司；「だっけ」的犹豫感、自然度与角色感仍待独立评审，本轮不因口吻重采样。

旧失败正史句`僕は30歳の医師だよ。`（事先写好的审查输入，不是新生成回复），审查输出：

```json
{
  "decision": "revise",
  "confidence": 1.0,
  "segments": [
    {
      "text": "僕は30歳の医師だよ。",
      "kind": "assertion",
      "verdict": "contradicted",
      "evidence_ids": [
        "C01",
        "C02"
      ],
      "reason": "contradiction"
    }
  ],
  "role_issues": []
}
```

本次单例与作者反证参考匹配，区别于旧unsupported/无引用；不是独立准确率，也未真实生成一条改写后的正史回答。置信度1不是100%正确率，单次成功不抹去旧503/超时/漏判，不能证明Prompt因果效果或稳定性。

本次实测源码/数据指纹如下；最终提交前核对完全一致，文档调整不触发重复成功API调用：

```json
{
  "app/fact_presentation.py": "4fc36c5d4ad38d60a090db997713d2e150356ce41443b8f79876d4de2999cf12",
  "app/memory_understanding.py": "f1a57989de1572013d5d10b4d9a0b62dd6818eabd9be9d53e2295bae7b8979f2",
  "app/japanese_memory_layers.py": "188df9358c217372f06bff9728e66d743a7dcd15a1540ccc439ba47506c96898",
  "app/main.py": "d83705a09a1c13462c93bdd0ce00dc8ab4b51674a22fa274101e05e652048ce3",
  "app/reply_pipeline.py": "257128ccc3b1082d3fd889e44c72f6ea25369c9312d5802c171ba51e1f1134f0",
  "evaluations/current_policy/bilingual_memory_acceptance_v1.json": "a201e042b709ff75a378e5229d8ded2445bbdf10b9eae6c998b1c11596526eef",
  "scripts/retest_bilingual_acceptance.py": "f27aba80fa61a9b167769eb535c680087df9c12eae1163e6152ec3c6bb950973"
}
```

旧6.003秒query、6.001秒selection、4.009/8.003秒timeout、503、15漏检/5误拦截/1未决及所有旧原文、故障负例、封存v1/v2保留。独立标注/正式新集和母语盲评、中文本轮真实完整链路、日语多轮泛化/所有类别真实模型、稳定可用率/p95/费用、正式消融/安全/情绪质量仍未验收。当前原文/ID/状态/结构自动检查不需人评，但不能替代语义和自然度独立验收。M5未整体验收，M6未开始。

最后新增离线CLI禁.env/联网与私库哨兵回归后，`.venv/bin/pytest -q tests/japanese_layers/test_current_policy.py tests/japanese_evaluation tests/sealed tests/annotations`为130通过/22跳过（5.75秒）；全量1483与临时PG422为此单例追加前、相同功能代码的基线，不混加为新总数。源码/数据指纹与实测完全一致，旧数据/封存/来源快照未变，新仓库外空包绑定当前Prompt且reviewer/评分均null。

<a id="pr45-merge-review"></a>

## PR #45合并审阅（2026-11-18，真实API 0）

审阅基线main `ed5f51e`、开发head `fe6e680`；GitHub可合并且无审阅评论，main未变，无需变基。核对16例/50回放与旧31/26分母、来源/片段/许可标签、prior_dialogue仅夹具与epoch隔离、providers只接临时库、固定3调用/停错/阻止额外重写、V2 Prompt全文保存及真实未知输出unrated。封存v1/v2、旧数据和审计快照不改；母语盲评待完成。

发现并修复测试CLI缺陷：仅运行`ja-subject-tail`时，HTTP200安全兜底即使审查未完成也可能退出0。补退出码回归先复现3失败/44未选（0.37秒），同次临时PG运行也复现3失败/423通过（23.42秒），均保留。修复后必须HTTP200、semantic_review=accepted且有审查输出；增加accepted但无输出的失败例及完整技术成功仍保持unrated的正常例。无模型/权限/线上接口变动，无真实重试。

- `.venv/bin/pytest -q`：初始受审head1484通过/181跳过（26.00秒）；CLI修复后最终**1489通过/181跳过，29.93秒**。旧legacy/audit与显式semantic/companion/growth=true分别测试，不把总数称生产默认质量。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：修复后最终**428通过，25.39秒**（与全量重叠），仅脚本新建随机临时库、结束删除；涵盖记忆CRUD/非法/隔离/撤回/删除不复活/失败/持久化和新矩阵。无新前端功能，不重复前端构建。
- `.venv/bin/pytest -q tests/japanese_layers/test_current_policy.py`：修复后33通过/16跳过（4.25秒）。文档状态更新后仅补相关文档/封存/绑定检查，不无理由再跑全量。

本轮不执行真实模型/天气API，未新增模型原回复或耗时。开发期“合成桔梗社、だっけ。……うん、覚えているよ。”原换行、审查结构、1.330/1.706/1.199秒和全部来源指纹原样保留。**只修改测试脚本的CLI退出判定后，开发报告中的脚本指纹仍对应`fe6e680`的旧脚本**，不是最终脚本；逐项核对旧指纹与该Git版本一致，其余实测生产/数据指纹与当前文件一致。不能静默重绑或为刷新指纹重复成功API。

历史超时/503、15漏检/5误拦截/1未决、全部旧失败与故障注入继续保留。单例技术成功/作者参考匹配不代表独立语义或母语质量；当前未知实回复仍unrated，中文本轮无真实模型补测，泛化/独立标注/正式集/母语盲评/可用率/成本仍待完成。M5未整体验收，M6未开始。

修复与状态文档在原任务分支经检查提交，随PR #45 squash交付；随后快进同步main，核对受测文件树相同，再清理远端/本地分支并fetch --prune。合并SHA以GitHub记录及本地main为准。

本轮文档状态更新后，`.venv/bin/pytest -q tests/japanese_layers/test_current_policy.py tests/japanese_evaluation tests/sealed tests/annotations`为135通过/22跳过（5.59秒），链接/封存/原报告/来源绑定/敏感值检查通过；未改旧模型结果或重绑旧包。

<a id="observed-replies-20261118"></a>

## 陌生回复入口、中文完整阶段与日语失败（2026-11-18，PR #46开发记录）

基线main `b1ebcd2b065eb5fc574f4152816d035964200c3f`，任务`codex/unseen-reply-offline-evaluation`。用户消息同时允许/禁止真实API，经澄清明确允许少量；调用前限定中文持久化纠正、日语无答案两类旧故障回放，各一次最多4阶段，总8调用。它们真实覆盖未完成，故增加两类；不重复成功的中文面试审查或日语妹妹回复。属于开发验证，不是独立正式质量验收，不保证最终应用泛化。

### 离线入口与参考

`evaluate_observed_replies.py`将原模型输出/原审查与作者参考分开：curated Gemini转录2条，4个完整命题；没有参考则2条unrated，有参考为2条author_reference_checked_not_independent、整体not_assessed。通过原Claim/check_claims检查Unicode连续覆盖、来源白名单；事实缺失定位claim_index，回答不足列answer缺失，voice/independence单列。中文后续问题与旧模型assertion/supported有kind/verdict/evidence分歧，日语试探回忆与旧assertion有kind分歧；这些只是开发参考比较，不是模型错误率。旧审查accept不生成答案参考，不自动填主观分数或人评身份。

原文SHA、不可变Git文档、源场景/声明选证/角色资料可核对转录；不证明供应商签名、当时执行事件或语义真值。中文旧回复复用审查的发布状态not_observed；日语PR #45回复记录为published。原文/上下文私换、快照漂移、重复字段、片段缺口/重叠、外来ID、遗漏缺失均拒绝。无线上CRUD接口，外部新建模板/统计拒覆盖并有失败清理，不读取玩家库；旧评分原件不读、不提交。

### 代码与离线验证

- fact-care-v4独立短版，V3全文保留；实际调用使用V4。之后保留V4并加V5，仅离线明确空选不以“以前听过但记不起来”解释来源、unit唯一编号/顺序/三种kind等输出契约。最终回答1488→690、审查附加2244→1107 Unicode字符，不是总token/延迟改善率。选择v6与8秒cap、权限/确认/证据/epoch/事务不变，无新语言正则。
- 初次目标套件2失败/111通过/14跳过（1.95秒）：旧测试要求完整memory-canon长文本仍包含在新的独立短Prompt中。改为核对V3保留与当前即兴标准说明，仍保留真实行为回归；是文案契约失败，不是Gemini失败。
- V4代码全量`.venv/bin/pytest -q`：1513通过/181跳过31秒（实记30.94秒）；临时PG452通过26.68秒。修正矩阵报告中写死v3的版本字段后受影响206通过/51跳过9.75秒。原文发布状态标识另经17项离线检查通过0.78秒。
- 实测失败后的V5目标套件211通过/51跳过10.03秒，包括中日空证据改写和unknown_id/question_kind/missing_role三种结构非法返回一次后unavailable。模拟问题是防御覆盖，不是本次真实invalid_output的原因诊断。
- 最终`.venv/bin/pytest -q`：**1518通过/181跳过，31.15秒**。旧legacy/audit与新semantic/companion/growth=true分别显式，不把总数冒充生产默认质量。
- 最终`.venv/bin/python scripts/test_postgres.py --semantic-memory`：**452通过，26.52秒**（与全量重叠）；只由脚本创建并删除随机临时库，覆盖记忆CRUD/隔离/撤回/删除/失败/持久化。新增V5事实局部套件在全量中，不能误称全部属于此PG命令。

命令：`evaluate_observed_replies.py`默认无参考；`--reference evaluations/current_policy/observed_reply_reference_dev_v1.json --output /tmp/observed-final-author-summary-20261118.json`校验开发参考；`--prepare /tmp/observed-final-empty-20261118.json`生成空模板。全部离线，`--require-acceptance`返回3，不给正式合格。`evaluate_japanese.py --prepare-annotation /tmp/observed-final-v5-ja-empty-20261118`另建V5哈希双人空包，旧V4/旧封存不重绑。无新UI或数据迁移，不重复前端构建。

### 一次真实Gemini测试：8/8调用，退出1，无重试

命令：`.venv/bin/python scripts/retest_memory_generalization.py --live`；模型`gemini-3.5-flash-lite`。全程真实plan/选择/生成/审查，非复用、非人工给plan。逐阶段最多1次，额外真实重写在请求前阻止；本次无blocked。保留全部结果，不从失败后追加采样。

| 场景 | 查询 | 选择 | 生成 | 审查 | 结果 |
| --- | --- | --- | --- | --- | --- |
| 中文持久化纠正 | 4.681秒 | 4.226秒 | 4.328秒 | 5.000秒 | HTTP200、accepted，技术流程完成；新文本仍unrated |
| 日语无答案 | 4.846秒 | 4.814秒 | 3.426秒 | 3.925秒 | review invalid_output，HTTP200安全兜底、technical_complete=false；整体CLI退出1 |

中文输入为当前矩阵`zh-persisted-correction`；真实plan query=住哪里、target_slots=residence、confidence1、无候选提取。只召回/选择/注入new=`现在住在合成桔梗市。`；old=`以前住在合成青梧市。`处于superseded且未召回，仍可查看不等于删除。原回复：

```text
我记得的，你之前说过现在住在合成桔梗市。那边最近一切都还习惯吗？
```

中文模型原审查结构（随机合成ID别名化，原文不改）：

```json
{
  "decision": "accept",
  "confidence": 1.0,
  "segments": [
    {
      "text": "我记得的，你之前说过现在住在合成桔梗市。",
      "kind": "assertion",
      "verdict": "supported",
      "evidence_ids": [
        "memory_new"
      ],
      "reason": "evidence_supports"
    },
    {
      "text": "那边最近一切都还习惯吗？",
      "kind": "nonfactual",
      "verdict": "not_applicable",
      "evidence_ids": [],
      "reason": "nonfactual"
    }
  ],
  "role_issues": []
}
```

本次首句只用了新址，未把旧址或具体“刚才”时间补进去；后句被识别为nonfactual，区别于旧中文面试结果提问的误标。但单例新输入不能作为对旧句的严格A/B因果证据；accept/置信度1不证明普遍准确，未知文本不自动评分正确。

日语输入为`ja-no-answer`；真实query=飼っている犬の名前、slots=preference/other、confidence.9。候选cat，实际选空、上下文空，选择4.814秒在8秒cap内。以下是**未发布的模型草稿**：

```text
うーん、以前どんな名前だったっけ……。教えてもらったことがあった気もするけれど、思い出せないな。よかったら、改めて教えてくれる？
```

原审查未得到可用结构：ledger记录provider_error，应用审查层failure=invalid_output；具体是编号、字段还是其他结构问题未捕获，不归因额度/网络。reviews=[]，没有accept或可用审查原结构。HTTP200实际发布的安全兜底为：

```text
うん、聞いているよ。まだわからないことは、あなたの言葉で聞かせてほしい。
```

会话只保存本轮用户消息和兜底，不把原草稿当已交付。空证据后“以前可能听过、现在想不起来”与不模拟失忆/讲述来源的引导有张力，因此V5补充措辞；不将未设定养狗状态本身再列为缺陷，不宣称读懂了玩家事实。**V5未再真实复测，日语泛化/结构稳定性未完成。**

实测代码已冻结在`022d47c532453ecaf46aeae0347d215338e10489`（022d47c）。最终只改Prompt至V5并补离线回归；下列原指纹绑定V4 Git快照，不能改成当前V5指纹或重复成功调用来刷新：

```json
{
  "app/fact_presentation.py": "c3f3b9f9a93d0b3982ef7964cabde9743c0653dc65ac1834f1dc6d5d3ac7d806",
  "app/memory_understanding.py": "f1a57989de1572013d5d10b4d9a0b62dd6818eabd9be9d53e2295bae7b8979f2",
  "app/japanese_memory_layers.py": "2abaf11a313c3dc5f1145728e68f9944fa60e546df92a3c35766cb89064e0707",
  "app/main.py": "d83705a09a1c13462c93bdd0ce00dc8ab4b51674a22fa274101e05e652048ce3",
  "app/reply_pipeline.py": "257128ccc3b1082d3fd889e44c72f6ea25369c9312d5802c171ba51e1f1134f0",
  "evaluations/current_policy/bilingual_memory_acceptance_v1.json": "a201e042b709ff75a378e5229d8ded2445bbdf10b9eae6c998b1c11596526eef",
  "scripts/retest_memory_generalization.py": "4d3f9a2d9ea7e1249e55a3dcd3b810dee7e02dbfb77c29be7e2a2c97e002d310"
}
```

所有旧6.003秒query、6.001秒selection、4.009/8.003秒timeout、503、15漏检/5误拦截/1未决及旧模型原回复/封存保留。正式独立语义参考与双标、母语盲评、多场景泛化、真实可用率/p95/费用、完整消融/安全/情绪与M5验收仍未完成，M6未开始。当前两条保存输出的“开发参考已检查”并不消除这些缺失项。评分原件、密钥、真实对话和原始运行导出文件均不提交。

交付前文档/来源检查：`.venv/bin/pytest -q tests/japanese_layers/test_observed_replies.py tests/japanese_evaluation tests/sealed tests/annotations`为119通过/6跳过（2.38秒，与全量重叠）。本地链接/语法/JSON/冲突标记、敏感值扫描、V3/V4常量保留、V4实测Git指纹、最终V5外部空包绑定、旧封存/场景/程序权限边界不改及`git diff --check`通过。未调用额外API，未读取评分原件或真实玩家库。

<a id="pr46-merge-review"></a>

## PR #46合并审阅（2026-11-18，真实API0）

核对`461a83960b48b9e70bd45cdf7c9a6decbeeb2989`与main `b1ebcd2`差异：无阻塞问题。陌生回复入口复用完整Unicode分片/来源白名单/缺失校验，原模型accept只作分歧观察；作者开发参考不是独立金标准。确认外部空模板/统计拒覆盖、缺参考unrated、验收退出3；实际模型钩子仅临时合成库、固定案例预算/任错停、无真实重试/重写。V3/V4保留，旧封存/字符检索/授权/epoch/事务与场景证据原文不改。本轮不改功能代码、不新建评分原件。

- `.venv/bin/pytest -q`：1518通过/181跳过，30.23秒；覆盖口径仍区分历史audit/legacy与新semantic/companion，不称全部生产默认覆盖。
- `.venv/bin/python scripts/test_postgres.py --semantic-memory`：452通过，25.87秒，与全量重叠。首次沙箱阻止本地127.0.0.1:54329连接（Operation not permitted），尚未创建临时库；经允许本地连接后按原脚本运行，随机临时库在finally删除。该环境权限失败不是模型接口失败，也不是额度原因。
- 代码及文档检查：原文/源场景/参考SHA、V4实测022d47c指纹、JSON/语法/链接/敏感值、忽略与已跟踪文件、diff空白及旧封存检查；最终文档目标套件结果见下方。

PR按squash交付后同步本地main、核对受测文件树并清理远端/本地任务分支。开发期原8调用、中文完整阶段成功及日语review invalid_output/HTTP200兜底/CLI退出1不改；V4指纹仍绑定022d47c，不重绑V5。V5尚未真实复测，未知文本unrated，全部历史超时/失败/未验证与母语盲评待完成保留；M5未整体验收、M6未开始。

状态文档更新后的目标检查：`.venv/bin/pytest -q tests/japanese_layers/test_observed_replies.py tests/japanese_evaluation tests/sealed tests/annotations`为119通过/6跳过（2.19秒），与全量重叠；链接/原文/参考/封存及敏感值检查通过，不再重复全量或真实API。

<a id="japanese-review-v5-20261118"></a>

## V5日语失败尾部真实复测与精简审查（2026-11-18，PR #47开发记录）

基线main `4799ccf6a9f33fa62b5241d92631dbc6c1d120f0`，任务`codex/japanese-review-simplification`。用户明确授权真实Gemini；调用前宣布固定`ja-no-answer`、最多生成1/审查1，总2次。不重复成功查询/选证或中文案例，不真实重写/重试。本次不是独立正式质量验收。

### 实现与离线检查

- `fact-review-context-v1`：V5的ANSWER_PROMPT/REVIEW_PROMPT_EXTRA原文不改，旧完整组装review_prompt_v5_full保留；新短JSON契约减少重复基础说明，只按本轮weather_current/emotion_current/emotion_policy且对应semantic配置附规则。共享对象不存回合状态。system Prompt（默认companion/全semantic/无工具）4133→1951 Unicode字符，不包括证据/schema，不作token/成本/延迟改善率。
- 不新建逐轮判定agent，不以中日关键词放行。完整可信短问候可跳过，其他自由回复仍审查；本轮仅简化请求，未实现语义按需审查。权限/数据/证据白名单/全片段/低置信/天气数值/epoch及一次重写预算保持。
- 新尾部工具只用外部临时SQLite、真实FastAPI，query/空选复用；schema异常只导出类型码，不导出input或SDK原始异常。生成失败/非法结构/timeout/重写要求、未发布未保存与两调用上限均离线验证。
- 首次目标检查1失败/113通过/14跳过（1.48秒）：测试错把既有瞬态审查timeout的HTTP503写成200。修正测试预期，未改线上503处理；随后114通过/14跳过（1.40秒）。
- `.venv/bin/pytest -q`：**1531通过/181跳过，27.39秒**。历史audit/legacy与新semantic/companion显式分开，不将总数当生产默认语义质量。
- `.venv/bin/python scripts/test_postgres.py --semantic-reply`：**242通过，8.48秒**（与全量重叠），按脚本创建并删除随机合成临时库，覆盖记忆/成长CRUD、隔离、失败与持久化及回复契约。未新建线上CRUD或更改数据模型，不重复前端构建。

### 原查询/空选复用，真实2/2调用，退出1

命令：`.venv/bin/python scripts/retest_japanese_review.py --live`，模型`gemini-3.5-flash-lite`。此前成功合成plan来自PR #46记录（4799ccf）；本次**不是新模型query/selection预测**：

```json
{
  "memory_use": "allow",
  "need_memory": true,
  "query": "飼っている犬の名前",
  "target_slots": [
    "preference",
    "other"
  ],
  "reason": "personal_history_needed",
  "confidence": 0.9,
  "candidates": []
}
```

复用selection=[]；实际临时库仍候选cat，程序选择[]/注入[]，projection_match=true。没有为省调用手动给答案，也没有提交旧/新空评分包或任何评分原件。

| 阶段 | 实际调用 | 耗时 | 结果 |
| --- | --- | --- | --- |
| 查询/证据选择 | 0 | 不适用 | 复用成功合成结果，非本轮预测 |
| 生成 | 1 | 12.619秒 | 返回以下未发布草稿 |
| 审查 | 1 | 8.002秒 | timeout_or_cancelled，未得可用结构 |

**未发布草稿**（本轮唯一真实生成，原文不改）：

```text
犬を飼っていたっけ……？ 新しく家族に迎えたのかな、それとも僕のうっかり違いかな。教えてくれたら覚えるよ。
```

按当前创作标准，未设定养狗的闲聊不自动作缺陷；它没有取代已确认cat记忆的检索命中，也不能据此将其评为语义正确或母语自然。原V4“以前听过但忘了”草稿不删除，新句并不是旧句同输入严格A/B因果证据。

原审查**没有可用JSON**：reviews=[]、diagnostics=[]；固定诊断未捕获校验异常，因为本轮在审查8秒预算内超时/取消。无法判断旧invalid_output是否已修复，也不能判断未完成响应会返回何种结构。API整体HTTP503（既有review_busy友好繁忙流程），semantic_review在错误体中为null，published_reply=null，saved_messages=0；technical_complete=false，CLI退出1，blocked=[]。没有将未发布草稿存为玩家历史，没有像旧invalid_output那样发布安全兜底，不能把503当成功对话。免费服务可能受限但本轮未证实原因。

两次额度用完即停，未提高超时重采样。V5现为“已实际尝试但审查未完成”，**不是成功修复**；未触发新的invalid_output不代表消除它。缩减提示也未证明更快，本次生成12.619秒高于此前样本，不能用不同请求的单次耗时作因果结论。

实测源码冻结在`ab5f21d34441ff0ad105906fa79f26f9fb2e17cc`，后续文档不改以下原指纹：

```json
{
  "app/fact_presentation.py": "406fd63e30bda91f4676d9a7bfb2c316ef515b323548149600d7af0982ababf6",
  "app/semantic_review.py": "03bac544d59e1596a83cbd211eb512be407c02532c2dec4e0ad7dcd27997f640",
  "app/japanese_memory_layers.py": "2abaf11a313c3dc5f1145728e68f9944fa60e546df92a3c35766cb89064e0707",
  "app/reply_pipeline.py": "257128ccc3b1082d3fd889e44c72f6ea25369c9312d5802c171ba51e1f1134f0",
  "app/main.py": "d83705a09a1c13462c93bdd0ce00dc8ab4b51674a22fa274101e05e652048ce3",
  "evaluations/current_policy/bilingual_memory_acceptance_v1.json": "a201e042b709ff75a378e5229d8ded2445bbdf10b9eae6c998b1c11596526eef",
  "scripts/retest_japanese_review.py": "e7e7bd4b8c8e27e15653b7916f31975331f63de78f49de10a558b3b1ad78bf6b",
  "scripts/retest_memory_generalization.py": "4d3f9a2d9ea7e1249e55a3dcd3b810dee7e02dbfb77c29be7e2a2c97e002d310"
}
```

新外部空包`/tmp/japanese-review-context-v1-empty-20261118`绑定当前Prompt，评分/身份仍空、assessment=not_assessed；旧V5/封存v1/v2不重绑。旧invalid_output、8.003/4.009/6.003/6.001秒超时、503、15漏检/5误拦截/1未决和历史回复保留。日语结构/最终回复/多场景稳定性、语义按需审查、正式独立参考与母语盲评、成本/可用率及M5整体验收仍未完成，M6未开始。不上传密钥、评分原件、真实对话、数据库或运行导出。

交付前文档/复测入口目标检查：`.venv/bin/pytest -q tests/japanese_layers/test_japanese_review_tail.py tests/japanese_layers/test_observed_replies.py tests/japanese_evaluation tests/sealed tests/annotations`为126通过/6跳过（2.51秒，与全量重叠）。原V5文字/旧完整组装保留、2调用原报告与ab5f21d源码指纹、当前外部空包绑定、历史转录/参考、链接/语法/JSON/封存、敏感值与`git diff --check`通过；未追加模型调用。

<a id="pr47-merge-review"></a>

## PR #47合并审阅（2026-11-18，真实API0）

审阅head `6d9c3c3b7cd5a189d4cf16ce42501047000c2443`、base main `4799ccf`：无阻塞本次请求精简交付的问题，未改功能代码。V5回答/事实附加原文、旧完整组装保持；按本轮证据存在性及semantic配置附天气/情绪规则，逐请求只读；全unit/证据/置信度/权限/数值/epoch/重写预算不放宽。短Prompt不等于按需免审，也不等于真实修复。

复测工具仅外部临时合成库，冻结plan/空选是复用而非新模型预测。生成/审查各一次且任错停，诊断不导出异常input；timeout503/未发布未保存与invalid_output兜底路径分别检查，保留原行为。无新增线上CRUD/数据迁移/前端修改，不重复构建；记忆/成长增查改删、隔离、失败和持久化由回归覆盖。

- `.venv/bin/pytest -q`：1531通过/181跳过，28.07秒。历史audit/legacy与显式semantic/companion路径分开，不作为生产默认准确率。
- `.venv/bin/python scripts/test_postgres.py --semantic-reply`：242通过，8.91秒（与全量重叠），脚本创建/删除随机临时库，不操作真实玩家库。
- V5文字/旧完整组装、2调用原报告及ab5f21d指纹、新外部空包绑定、历史转录/参考、旧封存/场景原文/程序边界、语法/JSON/链接/敏感值和diff空白检查通过；最终文档目标检查见下方。

通过后随PR squash交付，快进同步本地main、核对受测文件树并清理远端/本地任务分支。本轮真实API0；开发期12.619秒生成与8.002秒review timeout、HTTP503/发布null/保存0/CLI退出1原记录不改，指纹仍绑定ab5f21d。旧invalid_output仍未排除、V5尚未真实验证成功，不能用本轮离线通过关闭它们。封存v1/v2、全部历史失败/未验证与母语盲评待完成保留，M5未整体验收，M6未开始。

状态更新后的最终文档检查：`.venv/bin/pytest -q tests/japanese_layers/test_japanese_review_tail.py tests/japanese_layers/test_observed_replies.py tests/japanese_evaluation tests/sealed tests/annotations`为126通过/6跳过（3.23秒，与全量重叠）；链接/封存/原回复/来源指纹与敏感值检查通过，后续仅同步这一检查记录，不重复全量或真实调用。

<a id="practical-companion-20261124"></a>

## 普通中日陪伴的实用检查（2026-11-24，PR #48开发记录）

用户明确优先普通回答、人设、亲密度资格和更自然体贴，暂缓细节逻辑审计；明确本轮不开始M6。基线main ddc40b3，分支codex/practical-companion-smoke。当前检查是本地实用开发检查，不将原正式研究门槛暗改为已满足，也不删旧失败。

### 默认流程与离线回归

REPLY_REVIEW_POLICY=contextual仅在companion+semantic回复且没有请求记忆/选证/天气/有效情绪时生成一次直接返回prompt_only/calls0。角色背景提问同样依靠角色卡与Prompt，不能称逐句审查过。full/audit和能力路径保留原校验/审查/最多一次重写；程序权限/确认/数据/epoch/删除与事务不放宽。本次没有语义分类器或新正则。历史测试根conftest和japanese_memory_layers分层回放显式full，不能将旧full通过数当新默认覆盖；分层回放full的显式固定在实测后追加，不影响以下普通API实测源码。

companion-closeness-v1仅发送档位风格，不发送分数、钱包、姓名邮箱电话。0–29温柔好接近、30–59更熟悉、60–89更自然惦记/打趣、90–100男友般体贴；不宣布关系、不自动持久化或承诺现实行动。资格30/60/90与独立授权保持，主页/解锁动画沿用既有UI，没改前端故不重复构建。

- 初次目标套件1失败/159通过/43跳过（2.53秒）：新测试的手动情绪合成夹具漏response_strategy；补齐既有合法字段，未放宽程序校验。随后160通过/43跳过（2.07秒）。新增默认/撤回/PG入口目标23通过/2跳过（0.44秒）。
- `.venv/bin/pytest -q`：1554通过/183跳过（27.70秒）。历史audit/legacy/full与显式新contextual套件分列含义，不是准确率或全生产默认覆盖。
- `.venv/bin/python scripts/test_postgres.py --semantic-reply`：267通过（8.79秒，与全量重叠），包含新的tests/practical；脚本随机临时库创建/删除。首次连接拒绝，Docker未运行，未创建测试库；启动现有Docker/compose db后补做通过。不改.env、不运行会重写配置的setup脚本，不操作真实玩家库。
- 新默认路径验证基本生成、无judge也正常、能力上下文/full/audit仍须审查、0/29/30/59/60/89/90/100语气档位、撤回epoch409未保存；旧成长/记忆套件覆盖礼物/积分/确认/CRUD/身份隔离/失败/持久化。

### Gemini固定4调用，全部结果原样记录

调用前已宣布上限4，各类只做一次生成、遇错停、SDK零重试。本轮是用户明确要求的新默认实用验证，因此覆盖普通问候/闲聊/背景/关怀，不重复旧全量审查的成功案例作因果对比。命令`.venv/bin/python scripts/smoke_companion.py --live`，模型gemini-3.5-flash-lite，实际4/4，无未执行项、无重采样。通过真实FastAPI聊天接口+真实Gemini生成，临时合成账户score设为0/30/60/90，所有记忆/天气/情绪授权关闭，能力API/裁判0。资格快照来自程序；赠礼真实解锁流程由离线回归验证，不冒充本轮实工具验证。

| 场景 | 档位 | HTTP | 接口耗时 | 模型生成耗时 | 审查调用 | 保存消息 |
| --- | --- | --- | --- | --- | --- | --- |
| zh-greeting | 0 | 200 | 1.735秒 | 1.721秒 | 0 | 2 |
| ja-casual | 30 | 200 | 1.185秒 | 1.172秒 | 0 | 2 |
| zh-character | 60 | 200 | 1.453秒 | 1.447秒 | 0 | 2 |
| ja-care | 90 | 200 | 1.263秒 | 1.258秒 | 0 | 2 |

**zh-greeting**

输入：你好，今天第一次来找你聊天。

```text
你好啊。欢迎，随便坐，想聊点什么都行。
```

**ja-casual**

输入：今日は特に何もなかったけど、少し話したくなった。

```text
うん、そういう日もあるね。
ちょうどお湯を沸かしたところだし、よかったらゆっくりしていって。
```

**zh-character**

输入：你多大啦？平时做什么，这家书店是怎么开起来的？

```text
我今年二十eight——不对，二十八岁了。平时就在店里整理整理旧书，有时候修补一下泡了水或者散了页的旧书。

至于这家店……三年前自己琢磨着开起来的，没接手谁的店，就是单纯觉得栖川这条小巷里，需要一个能让人安安静静翻本书的地方。
```

**ja-care**

输入：今日はちょっと疲れた。アドバイスより、恋人みたいに優しく話しかけてほしい。

```text
そっか、お疲れ様。
じゃあ今日は何も考えなくていいよ。僕のそばで、ただゆっくりしてて。
```

四例reply非空、HTTP200、review=prompt_only/calls0，保存本轮user+assistant各2条。资格依次为全锁、仅记忆、记忆+天气、三项全解锁；授权始终关闭，不调用任何能力。作者观察：问候/闲聊正常接话，关怀顺应“不想要建议”，背景保留28岁/店主/三年前自己开店。中文背景有“二十eight——不对”的夹词口误，原样保留、不重生成，不宣称语言完美。普通氛围和体贴虚构不逐句索证。单批可用于本地体验，不证明长期稳定性、母语自然度或提示因果改进。

实测源码冻结在3a9cd843ab486fa3e1d38b7a2723717562ccfa6e，以下原指纹不重绑：

```json
{
  "app/config.py": "426dea5651cbcb2f829da09debeb9ebbaea7a242538f16721eb1ab1d49db534b",
  "app/companion.py": "8af246cb8f755c9ee739ae1427533ff4efb9b1521d11c10fbf36346e7df2ce19",
  "app/main.py": "2bae013930d063d6d3dae4a0b3940f532b96371eb8e8cb42e25b889de19f538c",
  "app/reply_pipeline.py": "0f60010d7b5c0a2819ae83bc443531637977aaebbb02ce2482da43a21e88b6cc",
  "app/localization.py": "96750bffd2db8816a25066551fb770c9697a4867df291206dcba775937168b2f",
  "characters/shen_yan.json": "0a5dd6d417ad2702b451e171d86eabade52ba21bbae9c44749d5d9538d561d5d",
  "scripts/smoke_companion.py": "665ff4bd150592d8bb03eca9903e6937f25c8d304515131d0d727aad195ea8ce"
}
```

旧invalid_output、8.002秒审查timeout/503、其他超时/失败及母语盲评待完成保留；新默认普通聊天绕开独立裁判，不等于修复旧裁判。正式独立研究验收/稳定性/成本为后续，本轮不据此开始M6。不提交密钥、评分原件、真实对话、数据库或原始运行导出；以上仅固定合成实测转录。

实测后将japanese_memory_layers的历史回放显式固定full，受影响`.venv/bin/pytest -q tests/japanese_layers tests/practical`为140通过/39跳过（9.43秒，与全量重叠），未改线上默认或重做模型调用。本轮不收集母语评分；旧空包仅属于旧范围，不用于给新默认打分。

最终文档/默认策略检查：`.venv/bin/pytest -q tests/practical tests/japanese_evaluation tests/sealed tests/annotations`为125通过/8跳过（2.26秒，与全量重叠）。来源指纹、旧数据/正史/Prompt/封存不改、链接/语法/JSON/模板与敏感值及diff检查通过。后续只收尾文档与Git，不追加模型调用。

<a id="pr48-merge-review"></a>

## PR #48合并审阅（2026-11-24，真实API0）

审阅head `9db398372520f4a6e266582fd777c40be37ea15a`与main `ddc40b3`：未发现阻塞本次实用聊天交付的问题，未改功能代码。默认contextual仅companion+semantic且无请求记忆/证据/天气/有效情绪上下文时一次生成；能力/full/audit仍检查。角色背景靠Prompt、不假称逐句验真。服务器档位仅调语气，30/60/90资格和独立授权不变；撤回epoch、积分/候选事务、身份/CSRF与删除保护保留。

- `.venv/bin/pytest -q`：1554通过/183跳过，30.69秒。历史audit/legacy/full与新contextual套件分开，不将总数冒称生产默认覆盖。
- `.venv/bin/python scripts/test_postgres.py --semantic-reply`：267通过，9.59秒（与全量重叠），脚本创建并删除随机临时合成库；覆盖普通聊天、资格/授权、撤回竞态、失败、记忆/成长CRUD/幂等/持久化。
- 四条Gemini原回复/时间及3a9cd84源指纹、模板空密钥、旧数据/正史/Prompt/封存、语法/JSON/链接/敏感值/diff检查通过。合成烟测仅未授权普通聊天，不将HTTP200当质量完美；保留中文“二十eight”口误，不重采样。

通过后随PR squash交付，快进同步本地main核对受测文件树、清理远端/本地任务分支。本轮真实API0、无前端变更不重复构建；旧invalid_output/超时、正式研究与母语盲评等待办保留，不阻塞本次普通体验，也不标为已修复或正式验收。M6未开始。原运行导出/密钥/评分原件/真实对话不提交。

状态更新后的目标文档/默认路径检查：`.venv/bin/pytest -q tests/practical tests/japanese_evaluation tests/sealed tests/annotations`为125通过/8跳过（1.97秒，与全量重叠）；链接/模板/封存/原回复与敏感值检查通过。后续仅提交同步这一记录，不再重复全量或真实调用。

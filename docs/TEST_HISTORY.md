# 测试基线、失败与历史索引

更新：2026-11-10。代码基线PR #28（`68b08f5`）。本轮只改文档，零真实模型/天气/支付API；不读取真实对话或评分原件，不开始M6。

## 最近功能验证（PR #28历史结果，本轮不冒充重跑）

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

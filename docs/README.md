# 项目文档入口

[中文](README.md) · [日本語](ja/README.md)

更新：2026-11-10。M1–M4功能闭环已交付，M5仍在验证，M6未开始；功能基线为PR #28（`68b08f5`），PR #29文档整合经本次squash交付main。

| 阅读目的 | 唯一维护入口 |
| --- | --- |
| 当前进度、后续顺序 | [实施计划](PLAN.md)、[任务清单](../TODOLIST.md) |
| 总体技术与本地运行 | [架构](ARCHITECTURE.md)、[项目README](../README.md) |
| M1 · 角色聊天与网页 | [功能、Prompt、React与测试](M1_CHAT.md) |
| M2 · 长期记忆与检索 | [授权、生命周期、检索与测试](M2_MEMORY.md) |
| M3 · 天气关怀 | [供应商适配、上下文、关怀与测试](WEATHER.md) |
| M4 · 情绪参考 | [结构化输出、校验、注入与测试](EMOTION.md) |
| M5 · 质量评测与审查 | [路由/裁判、消融、标注、验收与未验证项](M5_EVALUATION.md) |
| 日语版UI与适配计划 | [中日切换、实现及待验证](JAPANESE_LOCALIZATION.md) |
| 成长、账户与礼物 | [分数、解锁交互、钱包与测试](RELATIONSHIP_GROWTH.md) |
| 数据使用和删除 | [隐私边界](DATA_PRIVACY.md) |
| 版本、失败和旧文档原文 | [测试与历史索引](TEST_HISTORY.md) |

每个模块只维护一份综合文档，包含功能、设计、实现入口和验证边界；不再向多个总表复制同一轮长报告。旧文档的完整原文由测试索引固定到上述Git提交，包含当时回复、耗时、Prompt、失败和审计记录，可联网查看或通过`git show`离线读取。索引中的历史资料不代表当前实现。

例外：[旧场景/地名报告](https://github.com/qiaoliamor/llm-rag/blob/68b08f525fe3c444b3cc2b4992f58c26ea2980a5/docs/SCENE_PLACE_GROUNDING.md)被回归测试直接读取以逐字核对历史合成回复，保留原字节；它是历史证据，不是当前叙事规则。固定封存数据中的旧文档路径按测试索引查找，不为整理文档改写封存材料。

兼容入口：`M3_TEST_REPORT.md`只保留旧Prompt文档的链接与锚点，转向天气综合文档/固定版本原文，不继续维护独立报告；避免改动被来源哈希绑定的`prompts/DESIGN.md`。

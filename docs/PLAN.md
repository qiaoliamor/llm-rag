# 实施计划

## 1. 实施原则

先用合成数据构建单角色闭环，再验证长期记忆、外部工具和情绪策略。检索与提示优化属于待验证的研究假设：预期降低无依据事实和正史矛盾，但必须同时观察自然度、成本及延迟。

## 2. 拟议技术方案

以下是待原型验证的初始方案，不代表已安装依赖或完成供应商选型。

| 层 | 初始方案 | 选择依据 |
| --- | --- | --- |
| 后端 | Python + FastAPI | 清晰组织异步对话和工具接口 |
| 结构化与向量存储 | PostgreSQL + pgvector | 玩家事实、权限、删除与向量索引保持同一事务边界 |
| 检索 | 向量 + 关键词融合，随后重排 | 同时覆盖语义相似与人名、日期等精确匹配 |
| 模型 | 可替换的生成、嵌入、情绪分析适配器 | 先用 mock 验证流程，再依据质量和成本选型 |
| 天气 | 可替换 WeatherProvider | 供应商接入前验证目标地区、预报能力、条款和配额 |
| 原型界面 | 简单聊天页 + 记忆管理页 | 验证对话和玩家控制能力 |
| 验证 | pytest + 固定合成场景集 | 回归业务约束及外部服务失败路径 |

## 3. 对话链路

1. 校验身份、请求 ID、输入和授权配置，加载角色版本与短期历史。
2. 判断天气与情绪分析是否触发；补齐必需地点或时间，独立调用设置超时。
3. 从本轮消息生成检索查询，保留专名、日期、否定与人物关系；必要时拆为角色事实与玩家事件两个查询。
4. 数据库先施加 user_id、character_id、授权及删除状态过滤，再分别检索角色正史和玩家记忆。
5. 融合关键词和向量候选，按相关性、时效、重要度、来源可信度重排；去重、处理冲突、按令牌预算裁剪。
6. 组装系统约束、角色卡、来源证据、工具结果、情绪策略、历史和当前消息，生成回复。
7. 检查正史矛盾、无来源事实与失效工具信息；最多重写一次，失败或超时返回保守回应。
8. 返回回复，后台提取记忆候选并应用授权规则；写入必须幂等、支持删除期间的取消和重试检查。

MVP 先缓冲完整文本并检查后返回；流式输出后置，避免校验前展示冲突内容。

## 4. 最小数据模型

| 实体 | 关键字段 |
| --- | --- |
| UserSettings | user_id、timezone、city、memory_enabled、emotion_enabled、consent_version |
| Character | character_id、canon_version、persona、style、boundaries |
| CanonChunk | chunk_id、character_id、canon_version、source、text、embedding |
| Conversation / Message | conversation_id、user_id、character_id、role、content、created_at |
| Memory | memory_id、user_id、character_id、type、fact、subject、source_message_ids、event_time、timezone、importance、confidence、consent_status、expires_at、supersedes_id、deleted_at、embedding、embedding_version |
| EmotionAssessment | assessment_id、user_id、conversation_id、window_message_ids、labels、intensity、confidence、created_at、expires_at |
| RelationshipState | user_id、character_id、state、version、evidence_event_ids |
| ToolCall | request_id、provider、city、target_time、status、fetched_at、expires_at、source |

原始聊天、记忆与情绪结果分开保存。角色正史与个人记忆使用独立表和检索入口；数据库权限与服务鉴权双重隔离。嵌入不视为匿名数据。

## 5. 检索与提示工程实验

- 固定生成模型、采样参数、数据与上下文预算，保留直接提示、基础向量 RAG 两组基线。
- 逐步比较查询改写、混合检索、重排、时间衰减、冲突处理和证据约束提示；查询改写不得改变玩家原意。
- 初始候选参数：每路 top_k=20、最终上下文最多 8 条证据；参数仅作实验起点。
- 数据库中角色事实与玩家事实分开检索；向量相似度阈值按嵌入模型校准，不跨模型照搬。
- 生成前记录证据 ID；输出评测时判断事实是否得到证据支持，而非仅判断语气像角色。
- 对重要角色事实采用结构化约束与冲突规则；LLM 校验只能作为额外检测，不能作为保证。

## 6. 阶段与交付

工作量为单人开发的初步估计，不是交付承诺；合计约 20–28 个工作日，依选型和评测结果调整。

| 阶段 | 估计 | 交付物 | 完成门槛 |
| --- | --- | --- | --- |
| M0 规划 | 本次 | 需求、计划、清单、评测、隐私与提示设计、开源仓库 | 文档可追踪，仓库不含密钥与玩家数据 |
| M1 最小对话 | 3–4 日 | 后端、配置、模型 mock、原创角色卡、聊天入口、基线场景 | 可本地启动；正史约束与服务失败路径可验证 |
| M2 记忆与检索 | 5–7 日 | 数据迁移、候选提取、授权、检索、查看/纠正/删除 | 跨会话召回、隔离和删除验收通过 |
| M3 天气工具 | 2–3 日 | 意图触发、城市与日期处理、缓存、真实供应商适配 | 预报与实况可区分，异常不编造天气 |
| M4 情绪策略 | 3–4 日 | 多轮分析、置信度、触发/冷却、纠正、个性化回应 | 不确定表达、玩家纠正和关闭分析通过验收 |
| M5 优化评测 | 4–6 日 | 消融实验、对抗测试、性能记录、人工盲评报告 | 达到 MVP 指标或明确披露差距及修复项 |
| M6 开源发布 | 3–4 日 | 安装说明、容器、演示数据、CI、版本说明 | 新环境可复现；数据删除和安全隔离通过检查 |

## 7. 接口草案

- `POST /v1/chat`：输入 conversation_id、character_id、message；返回 reply、request_id、memory_candidates 和必要的地点澄清提示。
- `GET /v1/memories`：分页查看当前玩家记忆。
- `PATCH /v1/memories/{id}`：确认或纠正记忆。
- `DELETE /v1/memories/{id}`：删除单条记忆与检索资格。
- `DELETE /v1/memories`：清空当前玩家全部记忆，阻止历史任务重建。
- `PATCH /v1/settings`：更新城市、时区、记忆与情绪分析开关。

user_id 必须从认证上下文取得，不能信任请求体传入的身份。记忆操作检查所有权；完整账户删除还需清除聊天记录及派生数据。天气工具由服务端调用，前端不接触供应商密钥。

## 8. 风险与处理

- 不相关记忆影响体验：提高重排质量、加入过期策略，召回不足时不强行引用。
- 情绪误判：保留未知、开放式询问和玩家纠正；避免将推测固化为身份标签。
- 正史与玩家输入冲突：按事实域处理来源；正史升级后重建对应索引和回归评测。
- API 成本与延迟：限制分析频率、请求时长、重试次数和每日预算，保留 mock 回放。
- 依赖及供应商变化：真实接入前核验官方文档和条款，并固定依赖版本；不在规划阶段承诺兼容性。

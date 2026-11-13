# 系统架构

[中文](ARCHITECTURE.md) · [日本語](ja/ARCHITECTURE.md)

默认情绪回复新增emotion_presentation.py：组合EmotionAnalysisProvider复用companion/audit和可用天气Prompt，再追加情绪非诊断/偏好/语言规则。参考emotion_current与控制emotion_policy分离；后者不得作事实证据。reply_pipeline共享一次重写/总预算，按locale回退；普通waiting不额外强制审查。天气+情绪兜底保留工具事实、尊重listen；旧每模块legacy和原Prompt留作回放。失败/拒绝轮可能新增审查调用，实际延迟/费用未测。

情绪默认`emotion_understanding.py`：90分+授权→每轮严格EmotionDecision→当前原文绑定→自述解释/旧手动纠正优先，或程序按间隔/冷却决定SemanticEstimate→窗口user ID/阈值校验→必要字段上下文。两阶段共用6秒默认预算，模型不控制轮次/权限；新结果成功提交后只留会话，模型边界核对epoch。旧emotion.py仅显式legacy，数据库设置CRUD不变。

默认天气语义模式的回复新增`weather_presentation.py`：生成Prompt扩展→WeatherAnalysisProvider的版本化审查Prompt→完整结构/证据ID验证→纯天气归属片段的数字/单位检查→共享一次重写或当前locale回退。模型按语义区分表达与事实，不要求中文词。无judge/关闭review走weather_safe_fallback；天气结果非ok也核查，可能增加审查调用/延迟，真实成本未验证。旧weather.py/companion/semantic_review策略及显式legacy留作历史对照。

天气新增`weather_understanding.py`：60分资格+授权→本轮原文结构化计划→原文/字段校验→城市搜索（唯一匹配）或缺省本人已选城市→按目的地时区计算七天范围→已有forecast与必要字段投影。模型不产生天气数据/坐标/ID；epoch在理解和工具边界复查。旧weather.py数据供应商/缓存/数值保护保留，legacy语言规则只明确回放；详见[天气](WEATHER.md)。

更新：2026-11-10；功能基线PR #28。模块需求、设计和测试统一由[文档入口](README.md)导航。

## 技术与职责

| 层 | 当前实现 | 源码 |
| --- | --- | --- |
| 网页 | React + TypeScript + Vite；首页角色选择/个人账户、角色聊天、解锁说明与隐私管理 | `frontend/src/App.tsx`、`frontend/src/components/` |
| API编排 | FastAPI、Pydantic输入校验、Cookie归属/CSRF、单会话发送锁及授权撤销 | `app/main.py` |
| 回复 | Gemini/OpenAI/mock适配，角色资料、自然Prompt、局部事实检查、选择性结构化裁判、最多一次重写 | `dialogue.py`、`companion.py`、`reply_pipeline.py`、`semantic_review.py` |
| 记忆 | SQLAlchemy；PostgreSQL + pgvector，本地SQLite备用；按需检索、确认、纠正和删除 | `memory.py`、`memory_query.py`、`memory_routing.py` |
| 工具 | Open-Meteo/mock天气；复用当前模型的情绪估计 | `weather.py`、`emotion.py` |
| 成长 | 账户、分角色积分、演示钱包/流水，SQLite写锁或PG所属Player行锁 | `progression.py` |
| 离线评测 | 合成回归、检索消融、参考审计、封存与双人标注评分 | `app/*evaluation.py`、`scripts/`、`evaluations/` |

表中省略的Python路径前缀均为`app/`。角色正史及虚构环境分别在`characters/shen_yan.json`、`characters/shen_yan_scene.json`。

## 一轮聊天

1. 校验本浏览器身份、CSRF和会话发送锁；读取授权、epoch及亲密度资格。
2. 普通聊天优先近期上下文；确实需要已授权的跨会话事实时检索。天气/情绪分别满足资格、授权及触发条件后才调用。
3. 角色Prompt + 相关确认记忆 + 必要天气/情绪投影传给生成模型；完整记忆库、账户联系方式和天气原始JSON不进入Prompt。
4. 默认`companion`保留自然氛围，只对重要事实选择性审查；硬正史/工具边界仍检查。规则与语义审查共用一次重写预算；重要审查不可用不发布未经核对的草稿。
5. 再查epoch；开启成长时，候选记忆和积分共用事务，提交成功后保存最近12轮内存聊天并返回。失败不留下积分、候选或本轮历史。

授权/记忆变更会递增epoch，撤销旧在途回复并清理相关短期历史。完整聊天不落库，服务重启清除；另一窗口已显示的旧文字需要刷新。Cookie身份尚无跨设备恢复；单进程会话/缓存不能冒充多实例架构。

## 运行与配置

- 根目录`./scripts/start.sh`；网页`http://127.0.0.1:8000/`。先启动Docker数据库；构建产物发布到忽略的`app/static/`，不要手改产物。
- `app/config.py`为默认值来源：`CHAT_PROVIDER=gemini`、`DIALOGUE_MODE=companion`、`GROWTH_ENABLED=true`、`WEATHER_PROVIDER=openmeteo`。默认模型名`gemini-3.5-flash-lite`，只是本项目配置，不保证外部可用性；本地`.env`可覆盖。
- 需要完全离线时将聊天与天气都设为`mock`，数据库用独立临时SQLite。测试不要导入默认真实库后再改配置。
- 密钥和数据库地址仅后端读取，不显示或提交。正式部署、登录、真实支付、备份及多实例仍未完成。

PR #30合并审阅：后端929通过/55跳过、前端71通过和类型/构建通过；PG233为PR #28历史结果，本轮未执行、不累加。真实API调用0，M5质量未验收，详见[测试记录](TEST_HISTORY.md)。

## 语言适配

`frontend/src/i18n.ts`和`locales/ja.json`集中管理应用文案，UI语言偏好仅保存在本机；可选chat.locale由服务端枚举校验，`app/localization.py`追加固定生成语言指令。默认中文兼容，日语不改变角色/玩家ID、授权、表结构、记忆原文或时区。当前适配覆盖UI和基础生成；语言规则和独立质量边界见[日语版](JAPANESE_LOCALIZATION.md)。

## 多语言记忆理解

`memory_understanding.py`在解锁/授权后、读取记忆库前生成中日共用结构化计划。只有需要时，按本人确认记忆与模型给出的固定类型提示做数值召回（最多20条），语义选择后最多5条/1200字符进入生成。理解/选择共用4秒预算、最多2次，无重试；失败不检索/自动提候选，普通聊天继续。手动新增/修正文也发模型作元数据，失败保留原文和未知日期。数据库表与向量版本不变，ExactMemory元数据复用既有候选/积分事务。细节唯一入口[M2](M2_MEMORY.md)。

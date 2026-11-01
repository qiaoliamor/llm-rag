# 心语 · Persona RAG

面向女性玩家游戏的个性化角色对话系统。通过可追溯记忆、检索增强生成与提示工程，让角色持续关心玩家，并保持稳定的人格与背景。

**当前进度：M3 天气工具原型，前端 React + TypeScript。** 已实现原创角色沈砚、Gemini API 与 OpenAI Responses API 接入、多轮短期上下文、独立浏览器会话、清空对话、基础角色事实检查及离线演示。已增加确认式长期记忆、混合检索及网页查看/纠正/删除；新增默认关闭的天气查询与关怀；独立情绪分析仍待 M4。

## 在哪里查看计划

根目录 [TODOLIST.md](TODOLIST.md) 是完整任务清单，[docs/PLAN.md](docs/PLAN.md) 是阶段计划。网页顶部新增 **“计划与进度”**，可直接查看这两份文档；完成项显示 `[x]`，待办显示 `[ ]`。

开发前先阅读 [项目操作规则](AGENTS.md)：任务分支、命令行检查、PR合并与秘密保护。

## 本地打开

需要 Python 3.11+ 与 [uv](https://docs.astral.sh/uv/getting-started/installation/)。本项目已提交 `uv.lock`，启动时按锁定版本安装依赖。前端需要 Node.js 22.12+ 和 npm（本机已安装）。启动脚本在依赖缺失或锁文件更新时执行 `npm ci`，每次启动执行类型检查、前端构建并交给 FastAPI 提供页面。前端依赖锁定在 `frontend/package-lock.json`，首次安装需要网络。

```bash
cd /Users/qiaoli/Desktop/program/llm-rag
# 首次启用 PostgreSQL：先启动 Docker Desktop，再执行一次
./scripts/setup-memory-db.sh
./scripts/start.sh
```

浏览器打开 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**。保持终端运行，按 `Ctrl+C` 停止。其他电脑克隆后先进入自己的项目目录，再运行 `./scripts/start.sh`。本机 PostgreSQL 已配置，后续直接运行 `./scripts/start.sh`；先保证 Docker Desktop 在运行。数据库只监听本机 54329，数据在专用 Docker 卷。初始化会在本地 `.env` 生成数据库凭据，不显示或提交。若端口已占用，先停止原服务，或用 `uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8001` 后打开对应地址。

## 配置 Gemini（默认）

首次启动会自动从 `.env.example` 创建仅本地使用的 `.env`；本机已经创建好。用编辑器打开 `.env`，填入自己在 [Google AI Studio](https://aistudio.google.com/apikey) 创建的 Gemini API Key：

```dotenv
CHAT_PROVIDER=gemini
GEMINI_API_KEY=在本地填写你的Gemini密钥
GEMINI_MODEL=gemini-3.5-flash-lite
API_TIMEOUT_SECONDS=30
```

修改后重启服务。此次账号真实测试中，旧模型 `gemini-2.5-flash-lite` 返回“不再向新用户开放”；本地改用 `gemini-3.5-flash-lite` 后成功。M2 已将源码、模板和回归断言统一为新模型；现有本地密钥不被覆盖。模型权限、地区和实际限额以账号为准。代码不负责开通付费或切换计费档，但同一模型也有付费价格，因此不要把模型名称当作强制免费的开关；使用自己的 Free Tier 项目。达到配额后会提示错误，不自动切换其他服务或模型。

使用 Google 官方 [OpenAI 兼容接口](https://ai.google.dev/gemini-api/docs/openai)，复用现有 SDK，无需安装额外 Gemini 依赖。这里的兼容性指接口格式，请求实际发往 Google，使用独立的 `GEMINI_API_KEY`。免费档内容可能用于改进 Google 产品，当前建议只使用合成对话测试。[官方价格与数据说明](https://ai.google.dev/gemini-api/docs/pricing)

### 可选：继续使用 OpenAI

```dotenv
CHAT_PROVIDER=openai
OPENAI_API_KEY=在本地填写你的OpenAI密钥
OPENAI_MODEL=gpt-4.1-mini
```

两个供应商的密钥互相独立，只使用当前 `CHAT_PROVIDER` 对应的密钥。OpenAI 模型名称可改为账号支持且兼容 Responses API 的模型，不读取 ChatGPT 网页登录态。

密钥仅由 Python 后端读取，不进入网页、Cookie 或 API 响应。`.env`、日志及运行数据已加入 `.gitignore`；不要把真实密钥填入 `.env.example`、源码、Issue 或聊天。公开仓库保留 API 接入代码和空配置模板，以便他人运行，不含个人凭据。

接入方式参考 [OpenAI 官方快速开始](https://developers.openai.com/api/docs/quickstart) 和 [API 认证说明](https://developers.openai.com/api/reference/overview)。OpenAI 模式使用 `store=False`，但这不等同于对供应商所有数据保留行为的承诺，真实接入前请核对账号的数据设置。

## 不填密钥也能试用网页

```bash
CHAT_PROVIDER=mock ./scripts/start.sh
```

网页会明确显示“离线演示 · 非真实模型回复”。它使用固定规则，用来检查网页交互及故障路径，不能代表真实模型质量；API 模式缺少密钥或调用失败时会明确报错，不自动切换成模拟回复。

## 长期记忆如何使用

1. 打开网页 **“长期记忆”**，点击“开启长期记忆”（默认关闭），按需要选择事件时区。
2. 在聊天中明确表达重要经历，例如“我下周二有面试”。系统只提取本轮的保守候选，不自动记为长期事实。
3. 点击候选提示，逐条点击“确认记住”；没有被规则覆盖的经历可手动添加候选。未经确认不参与检索。
4. 点击“开始新对话”后，仍可询问“你记得我的求职安排吗”。同一浏览器身份下，已确认记忆保存在本机，服务重启后仍可恢复。
5. 可纠正内容、单条删除或清空全部；同类事实冲突时明确选择替换旧内容，或作为独立经历保留两条。

纠正、确认、删除及授权变更会清空当前身份的短期聊天，防止旧事实继续影响回复。删除会物理移除记忆原文/向量，保留无原文的撤销指纹与动作版本；重复旧消息不会自动重建已删除记忆，手动重新添加并确认代表重新授权。关闭只停止提取/检索，保留已确认内容，可继续删除。

记忆归属浏览器的随机 HttpOnly Cookie，不是跨设备账号；清除 Cookie、换浏览器或隐私窗口会变成另一个身份。不要清除 Cookie 来测试“新对话”，使用网页按钮即可。当前不提供遗失身份恢复。聊天原文只在内存中，不保存完整聊天日志；候选摘录和确认事实会保存到本地数据库。

### 数据库与检索方式

推荐按上述脚本使用 PostgreSQL + pgvector。`migrations/001_memory.sql` 是初始 schema v1 的参考 SQL（应用同时执行v2时区列与v3天气设置表升级），应用首次启动自动建立缺失表并执行幂等升级、登记版本。测试脚本使用独立临时库，不写真实记忆库。不要执行 `docker compose down -v`，它会删除本项目记忆卷。

不使用 Docker 时，本地 `.env` 可以设置 `MEMORY_DATABASE_URL=sqlite:///data/memory.sqlite3`，使用 SQLite 持久化及进程内精确向量评分；不要把它称为 pgvector 模式。切换数据库不会自动搬运已有记忆，应保持当前配置。两种模式都支持本地记忆管理；当前按单 Uvicorn worker 使用。

检索采用768维本地字符特征哈希与限定同义词扩展，不调用额外嵌入 API。PG 模式在身份、角色、确认状态和有效期过滤后执行精确余弦向量查询，再结合关键词、时效和重要度重排；最多5条、约1200字符记忆进入提示。它是可重复基线，尚未实现训练模型的深层语义嵌入，不能保证任意换一种说法都能召回。

## 天气关怀如何使用

天气使用 Open-Meteo 非商业免费端点，**无需注册、无需天气密钥**。在网页“天气关怀”中开启授权，搜索并选择城市，保存后回到聊天询问“明天天气怎么样？”；也可在消息中明确临时目的地。地点不明或重名会澄清，不通过IP/GPS或记忆猜测位置。天气设置支持查看、修改和删除，与长期记忆授权分开。

当前天气为模型估计，未来天气为当地整日预报；支持今天起七天，不提供小时级或历史查询。工具只发送城市/坐标，不发完整聊天给天气供应商；投影后的天气和相关确认记忆才进入对话模型提示。可用 `WEATHER_PROVIDER=mock CHAT_PROVIDER=mock ./scripts/start.sh` 完全离线演示，所有天气会标明合成。商业化前需重新确认天气许可。详见 [天气API与上下文设计](docs/WEATHER.md)。

## 当前行为与边界

- 原创角色沈砚，28岁，栖川旧书店店主；固定角色正史与玩家记忆分开，记忆不能改写正史。
- 聊天输入上限2000字符，内存保留最近12轮；新对话清空短期历史，长期记忆另行管理。
- 默认关闭记忆；候选24小时有效。明天/后天/下周某日和明确年月日可解析，模糊日期保留未知；健康、创伤等也需逐条确认。
- 面试、考试、手术类未来预约到日期后31天退出检索，仍可查看删除；一般历史经历和偏好不按预约规则过期。
- 角色检查仍是局部规则与一次重写，不能保证杜绝幻觉。天气查询已实现但复杂表达和真实关怀质量仍待评估；独立情绪分析尚未实现。
- API 模式向当前供应商发送提示、短期历史与相关已确认记忆；默认不把所有记忆发送出去。记忆关闭时不检索。
- 仅本地使用：会话/CSRF/Host 检查不替代生产账户、HTTPS、备份擦除和完整审计。数据库没有新增应用级加密，请谨慎保存敏感内容。

## 前端开发与构建

源代码在 `frontend/src/`，采用 React 组件、TypeScript 严格类型检查与 Vite 构建。原有旧书店风格及聊天交互保留。React 迁移时保留原聊天接口；M2 在兼容旧字段的基础上增加记忆与设置接口，不需要额外启动前端服务或设置 CORS。

```bash
npm ci --prefix frontend
npm run build --prefix frontend
```

构建输出先进入 `frontend/dist/`，再发布到 `app/static/`。这两处生成文件与 `node_modules/` 均不提交；不要直接编辑生成文件。修改前端后重新 build 并刷新网页即可；后端已经运行时无需为了前端构建重启。全新克隆后直接运行 `./scripts/start.sh` 也会自动安装和构建。

Vite 关闭 `.env` 文件加载，前端代码不读取根目录秘密；供应商密钥继续只由 Python 后端加载。不要把密钥放入前端源码或任何 `VITE_*` 变量。

## 测试与实验

```bash
npm ci --prefix frontend
npm run build --prefix frontend
npm run test --prefix frontend

uv run --frozen pytest -q
uv run --frozen python scripts/evaluate.py --limit 100
```

M2 历史结果为20项前端、174项默认后端通过；M3当前为25项前端、227项默认后端通过/19项PG跳过、临时库专项103项通过，验证范围见 [M3测试记录](docs/M3_TEST_REPORT.md)。数据库专项脚本 `uv run --frozen python scripts/test_postgres.py` 只创建并删除临时库，不操作真实记忆数据。后端测试前必须先构建前端。原有 100 条合成场景及接口、隔离、重写、密钥缺失、配额、超时等回归保留；新增静态资源检查验证 React 构建能通过现有路径和 CSP 加载。离线评测只验证 mock 链路，不衡量情感理解或幻觉率。脚本提供 direct（直接提示）、rag（简单关键词正史检索）、canon（完整正史）三个对照入口。实际聊天现已检索已确认玩家记忆；该脚本仍是角色正史的三组简易对照，不等于完整记忆评测。

本地填好密钥后可执行下列小规模真实测试；会消耗当前供应商额度，付费档可能产生费用；每组最多 `limit` 次、共三组：

```bash
uv run --frozen python scripts/evaluate.py --live --limit 5
```

真实测试中的字面片段命中只是初筛，语义正确性仍需人工评审。后续已用本地密钥和 Gemini 3.5 Flash-Lite 完成六轮真实连续对话及一次网页真实交互；发现未知童年回应有无依据解释，尚未做正式质量对照或账单核验。M2 另完成真实跨会话召回、纠正与删除链路。详见 [M2 测试记录](docs/M2_TEST_REPORT.md) 和 [Gemini 适配测试记录](docs/GEMINI_TEST_REPORT.md) 和 [M1 测试记录](docs/M1_TEST_REPORT.md)。

实际 PostgreSQL 回归（先确保本地数据库就绪）：

```bash
uv run --frozen python scripts/test_postgres.py
```

脚本创建随机命名临时数据库，执行专项用例后删除该临时库。普通 pytest 强制使用临时 SQLite；两者不使用真实记忆库。

## 项目文档

| 文档 | 内容 |
| --- | --- |
| [M2 测试记录](docs/M2_TEST_REPORT.md) | 记忆授权、持久化、检索、删除与真实链路 |
| [React 迁移记录](docs/FRONTEND_MIGRATION.md) | 组件结构、构建流程、兼容性和本次测试 |
| [阶段总结](docs/PROJECT_STATUS.md) | 用户意见、设计决策、已完成工作与已知问题 |
| [前后端架构](docs/ARCHITECTURE.md) | 当前实现、接口、数据流及 M2–M4 目标设计 |
| [版本测试总表](docs/TEST_HISTORY.md) | 提交对应的测试范围和真实验证结果 |
| [功能需求](docs/FEATURES.md) | 四项核心功能与验收条件 |
| [实施计划](docs/PLAN.md) | 架构、数据结构与里程碑 |
| [任务清单](TODOLIST.md) | 当前进度与后续开发 |
| [评测方案](docs/EVALUATION.md) | 幻觉、角色一致性和个性化评测 |
| [数据与隐私](docs/DATA_PRIVACY.md) | 后续持久化阶段的授权和删除设计 |
| [提示设计](prompts/DESIGN.md) | 提示分层与模板 |
| [参与贡献](CONTRIBUTING.md) | 开发与贡献约定 |

采用 [MIT License](LICENSE)。仅提交原创或已获授权的角色设定与数据；第三方 API、模型与素材遵守各自条款。

# 心语 · Persona RAG

面向女性玩家游戏的个性化角色对话系统。通过可追溯记忆、检索增强生成与提示工程，让角色持续关心玩家，并保持稳定的人格与背景。

**当前版本：M1 本地单角色网页原型，前端已迁移到 React + TypeScript。** 已实现原创角色沈砚、Gemini API 与 OpenAI Responses API 接入、多轮短期上下文、独立浏览器会话、清空对话、基础角色事实检查及离线演示。长期记忆、天气和专门情绪分析将在 M2–M4 实现。

## 本地打开

需要 Python 3.11+ 与 [uv](https://docs.astral.sh/uv/getting-started/installation/)。本项目已提交 `uv.lock`，启动时按锁定版本安装依赖。前端需要 Node.js 22.12+ 和 npm（本机已安装）。启动脚本在依赖缺失或锁文件更新时执行 `npm ci`，每次启动执行类型检查、前端构建并交给 FastAPI 提供页面。前端依赖锁定在 `frontend/package-lock.json`，首次安装需要网络。

```bash
cd /Users/qiaoli/Desktop/program/llm-rag
./scripts/start.sh
```

浏览器打开 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**。保持终端运行，按 `Ctrl+C` 停止。其他电脑克隆后先进入自己的项目目录，再运行 `./scripts/start.sh`。若端口已占用，先停止原服务，或用 `uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8001` 后打开对应地址。

## 配置 Gemini（默认）

首次启动会自动从 `.env.example` 创建仅本地使用的 `.env`；本机已经创建好。用编辑器打开 `.env`，填入自己在 [Google AI Studio](https://aistudio.google.com/apikey) 创建的 Gemini API Key：

```dotenv
CHAT_PROVIDER=gemini
GEMINI_API_KEY=在本地填写你的Gemini密钥
GEMINI_MODEL=gemini-3.5-flash-lite
API_TIMEOUT_SECONDS=30
```

修改后重启服务。此次账号真实测试中，旧模型 `gemini-2.5-flash-lite` 返回“不再向新用户开放”；本地改用 `gemini-3.5-flash-lite` 后成功。源码及 `.env.example` 的旧默认值暂未修改，新环境请在本地 `.env` 明确填写上面的模型覆盖项。模型权限、地区和实际限额以账号为准。代码不负责开通付费或切换计费档，但同一模型也有付费价格，因此不要把模型名称当作强制免费的开关；使用自己的 Free Tier 项目。达到配额后会提示错误，不自动切换其他服务或模型。

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

## 当前行为与边界

- 角色：28 岁的沈砚，在虚构城市栖川经营旧书店；角色卡和来源见 `characters/shen_yan.json`。
- 聊天：Enter 发送、Shift + Enter 换行，支持中文输入法；消息上限 2000 字符。
- 会话：匿名本地会话 Cookie，服务端内存保存最近 12 轮，闲置 2 小时过期；刷新可继续，清空或重启后消失。不同浏览器或独立浏览器配置互相隔离，同一浏览器的标签页共享会话。
- 生成：每轮发送角色约束与近期上下文，完整回复校验后展示；最多重写一次。基础规则只覆盖部分数字年龄、职业与书店来源冲突，无法保证检测所有幻觉、否定语义或设定冲突。
- 安全范围：仅绑定本机回环地址，含 Host、同源与 CSRF 检查、输入限制、并发保护和会话数量上限。这是本地开发原型，没有生产账户系统或公网部署能力。
- 本阶段不保存长期记忆，不查询真实天气，也不运行专门情绪分析；API 模式的对话会发送到当前选择的供应商（Gemini 发往 Google，OpenAI 发往 OpenAI）。

## 前端开发与构建

源代码在 `frontend/src/`，采用 React 组件、TypeScript 严格类型检查与 Vite 构建。原有旧书店风格及聊天交互保留。后端 Python 代码和 `/v1/session`、`/v1/chat` 接口未改动，不需要额外启动前端服务或设置 CORS。

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

迁移后 14 项前端交互测试与 143 项后端/静态资源测试通过。后端测试前必须先构建前端。原有 100 条合成场景及接口、隔离、重写、密钥缺失、配额、超时等回归保留；新增静态资源检查验证 React 构建能通过现有路径和 CSP 加载。离线评测只验证 mock 链路，不衡量情感理解或幻觉率。脚本提供 direct（直接提示）、rag（简单关键词正史检索）、canon（完整正史）三个对照入口；向量检索在 M2 实现。

本地填好密钥后可执行下列小规模真实测试；会消耗当前供应商额度，付费档可能产生费用；每组最多 `limit` 次、共三组：

```bash
uv run --frozen python scripts/evaluate.py --live --limit 5
```

真实测试中的字面片段命中只是初筛，语义正确性仍需人工评审。后续已用本地密钥和 Gemini 3.5 Flash-Lite 完成六轮真实连续对话及一次网页真实交互；发现未知童年回应有无依据解释，尚未做正式质量对照或账单核验。详见 [Gemini 适配测试记录](docs/GEMINI_TEST_REPORT.md) 和 [M1 测试记录](docs/M1_TEST_REPORT.md)。

## 项目文档

| 文档 | 内容 |
| --- | --- |
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

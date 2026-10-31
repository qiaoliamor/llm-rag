# 心语 · Persona RAG

面向女性玩家游戏的个性化角色对话系统。通过可追溯记忆、检索增强生成与提示工程，让角色持续关心玩家，并保持稳定的人格与背景。

**当前版本：M1 本地单角色网页原型。** 已实现原创角色沈砚、OpenAI Responses API 接入、多轮短期上下文、独立浏览器会话、清空对话、基础角色事实检查及离线演示。长期记忆、天气和专门情绪分析将在 M2–M4 实现。

## 本地打开

需要 Python 3.11+ 与 [uv](https://docs.astral.sh/uv/getting-started/installation/)。本项目已提交 `uv.lock`，启动时按锁定版本安装依赖。本机已安装 uv 和依赖。

```bash
cd /Users/qiaoli/Desktop/program/llm-rag
./scripts/start.sh
```

浏览器打开 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**。保持终端运行，按 `Ctrl+C` 停止。其他电脑克隆后先进入自己的项目目录，再运行 `./scripts/start.sh`。若端口已占用，先停止原服务，或用 `uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8001` 后打开对应地址。

## 配置你的 OpenAI API

首次启动会自动从 `.env.example` 创建仅本地使用的 `.env`；本机已经创建好。用编辑器打开 `.env`，填入自己 OpenAI Platform 项目的 API Key：

```dotenv
CHAT_PROVIDER=openai
OPENAI_API_KEY=在本地填写你的密钥
OPENAI_MODEL=gpt-4.1-mini
API_TIMEOUT_SECONDS=30
```

修改后重启服务。模型名称可改成你的 API 项目有权使用且支持 Responses API 的模型；默认名称是可配置的初始选择，不保证账号权限。这里使用 OpenAI Platform API Key，不读取 ChatGPT 网页登录态。

密钥仅由 Python 后端读取，不进入网页、Cookie 或 API 响应。`.env`、日志及运行数据已加入 `.gitignore`；不要把真实密钥填入 `.env.example`、源码、Issue 或聊天。公开仓库保留 API 接入代码和空配置模板，以便他人运行，不含个人凭据。

接入方式参考 [OpenAI 官方快速开始](https://developers.openai.com/api/docs/quickstart) 和 [API 认证说明](https://developers.openai.com/api/reference/overview)。服务使用 `store=False`，但这不等同于对供应商所有数据保留行为的承诺，真实接入前请核对账号的数据设置。

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
- 本阶段不保存长期记忆，不查询真实天气，也不运行专门情绪分析；API 模式的对话会发送到 OpenAI。

## 测试与实验

```bash
uv run --frozen pytest -q
uv run --frozen python scripts/evaluate.py --limit 100
```

含 100 条合成场景及接口、隔离、重写、密钥缺失、配额、超时等回归测试。离线评测只验证 mock 链路，不衡量情感理解或幻觉率。脚本提供 direct（直接提示）、rag（简单关键词正史检索）、canon（完整正史）三个对照入口；向量检索在 M2 实现。

本地填好密钥后可执行下列小规模真实测试；会产生 API 调用及相应费用，每组最多 `limit` 次、共三组：

```bash
uv run --frozen python scripts/evaluate.py --live --limit 5
```

真实测试中的字面片段命中只是初筛，语义正确性仍需人工评审。首次交付未填写真实密钥，因此未执行付费模型测试。详见 [M1 测试记录](docs/M1_TEST_REPORT.md)。

## 项目文档

| 文档 | 内容 |
| --- | --- |
| [功能需求](docs/FEATURES.md) | 四项核心功能与验收条件 |
| [实施计划](docs/PLAN.md) | 架构、数据结构与里程碑 |
| [任务清单](TODOLIST.md) | 当前进度与后续开发 |
| [评测方案](docs/EVALUATION.md) | 幻觉、角色一致性和个性化评测 |
| [数据与隐私](docs/DATA_PRIVACY.md) | 后续持久化阶段的授权和删除设计 |
| [提示设计](prompts/DESIGN.md) | 提示分层与模板 |
| [参与贡献](CONTRIBUTING.md) | 开发与贡献约定 |

采用 [MIT License](LICENSE)。仅提交原创或已获授权的角色设定与数据；第三方 API、模型与素材遵守各自条款。

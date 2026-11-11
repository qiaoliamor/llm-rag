# 心语 · Persona RAG

[中文](README.md) · [日本語](README.ja.md)

面向女性玩家游戏的原创角色对话原型：React + TypeScript网页、FastAPI后端，支持Gemini/OpenAI/mock、确认式长期记忆、天气关怀和可纠正情绪参考。

M1–M4功能闭环已实现，M5仍在质量验证，M6未开始。亲密度30/60/90依次解锁记忆/天气/情绪资格，仍需各自授权；钱包只是演示币，没有真实支付或正式账号体系。

- [文档入口：每个模块的功能、设计、实现与测试](docs/README.md)
- [当前任务清单](TODOLIST.md) · [阶段计划](docs/PLAN.md) · [测试及历史原文](docs/TEST_HISTORY.md)
- 开发前阅读 [AGENTS.md](AGENTS.md)，贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 本地运行

需要Python 3.11+、uv、Node.js 22.12+和npm；推荐Docker Desktop运行PostgreSQL/pgvector。进入克隆目录后：

```sh
# 首次配置PostgreSQL前先启动Docker Desktop；已配置则跳过
./scripts/setup-memory-db.sh
./scripts/start.sh
```

打开 [http://127.0.0.1:8000](http://127.0.0.1:8000/)，保持终端运行，Ctrl+C停止。脚本按锁文件安装必要依赖、构建React到`app/static/`再启动FastAPI；首次安装需要网络。开发计划只在仓库维护，玩家页面没有计划页。

首次启动从`.env.example`创建本地`.env`，用编辑器填写`GEMINI_API_KEY`，不要贴进聊天或上传Git。源码默认模型为`gemini-3.5-flash-lite`，本地`GEMINI_MODEL`可覆盖；模型名不保证账号权限、免费额度或服务可用性。修改配置后重启。

- 完全离线：本地设置`CHAT_PROVIDER=mock`、`WEATHER_PROVIDER=mock`，需要时用独立SQLite路径；mock天气明确为合成，不等于真实天气。
- 可选OpenAI：`CHAT_PROVIDER=openai`并本地填写`OPENAI_API_KEY`/`OPENAI_MODEL`。
- PostgreSQL默认本机端口54329；SQLite可配置`MEMORY_DATABASE_URL=sqlite:///data/memory.sqlite3`，不称pgvector模式。切换库不会自动迁移记忆；不要删除Docker数据卷来“重置测试”。
- 8000已占用时先停止自己的旧进程，或用`uv run --frozen uvicorn app.main:app --host 127.0.0.1 --port 8001`。

## 页面与数据边界

首页只有角色选择/个人账户；进入沈砚聊天。首页仅显示初识/渐熟/默契/知心档位，解锁时短暂提示，已解锁文字可点击查看解释。账户内可管理资料、演示币、礼物和已授权能力；基础聊天始终可用。

长期记忆需要逐条确认，支持查看/纠正/删除；按需检索，不每轮查库。当前向量为本地字符特征，不是训练语义嵌入；自动提取保守，遗漏可手动添加。身份绑定浏览器Cookie，清Cookie后没有自动找回；完整聊天只在服务内存保留，确认事实本地持久化。

允许虚构书店环境、光线、声音和普通动作，重点守住角色正史、玩家经历及工具事实。语义裁判是有限模型检查，不保证理解全部事实。天气是模型估计/预报，情绪是可纠正参考，不是实况传感器或心理诊断。供应商会收到必要聊天/地点数据，详见[隐私](docs/DATA_PRIVACY.md)。

## 命令行验证

```sh
npm ci --prefix frontend
npm run build --prefix frontend
npm test --prefix frontend -- --run
uv run --frozen pytest -q
# 如需数据库专项：只创建/删除随机临时PG库，不用真实玩家库测试
uv run --frozen python scripts/test_postgres.py
# 只做封存结构/哈希检查，零模型调用
uv run --frozen python scripts/check_sealed_evaluation.py --validate-content
```

PR #28历史基线：917通过/55跳过，独立临时PG233通过（重叠），前端60通过及构建通过；上述为历史结果；最新合并审阅929/55、前端71及构建见测试记录。新默认companion和旧audit覆盖口径、历史失败、真实合成观测及未验收项见[测试记录](docs/TEST_HISTORY.md)。真实API测试仅按AGENTS缩量复测旧失败，不在自动检查中加`--live`。

项目采用MIT许可，仅提交原创/授权素材、代码和合成测试资料；不提交`.env`、密钥、数据库、日志、真实对话/记忆、标注评分原件或运行导出。真实账号、支付、完整注销/备份擦除、多实例发布仍未实现。

日语版本：网页顶部“语言 / 言語”选择“日本語”，复用同一身份和数据库。已实现日语UI、基础对话语言和中日语义记忆流程；天气意图/日期、情绪自述和其余事实核对仍待适配，语义记忆真实质量仍待独立验证。详见 [日语版设计](docs/JAPANESE_LOCALIZATION.md)。

记忆语义适配：默认`MEMORY_UNDERSTANDING_MODE=semantic`，中文/日本語共用结构化按需计划、原文候选、日期关系与证据选择。已授权轮次会额外向当前模型发送必要短期文本；只有需要时才读记忆库。手动新增/修正也解析日期，失败保留原文/未知日期；逐条确认、身份/删除保护不变。`legacy`只作明示回放。详见[M2](docs/M2_MEMORY.md)，模型准确率/延迟/费用尚未真实验收。

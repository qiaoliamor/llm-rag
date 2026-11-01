# React + TypeScript 前端迁移与测试记录

历史测试日期：2026-10-31（Asia/Tokyo）。阶段：M2前置迁移，提交 `9141d46`。后端基线 `21c487e`；本次后端 Python 代码、角色卡、模型适配器及 API 请求/响应未修改。项目声明版本仍为 `0.1.0`，没有创建新 Release 或 Git tag。

当前状态补记（2026-11-01）：下文14项前端、143项后端为React迁移时的历史结果。后续M2 `7bb28ca` 已完成记忆界面，默认模型统一为Gemini 3.5 Flash-Lite；当前计数与接口见 [M2记录](M2_TEST_REPORT.md) 和 [架构](ARCHITECTURE.md)。

## 1. 迁移范围与兼容性

原生 DOM 操作改为 React 组件和受控状态，沿用原有 CSS、配色、旧书店插画、布局、角色文案、气泡和移动断点。单页面暂不引入路由库、全局状态库或额外服务端框架。

| 原功能 | 迁移后实现 |
| --- | --- |
| 会话初始化与刷新恢复 | App 挂载调用 `GET /v1/session`，使用后端历史和 Cookie |
| 发送与上下文 | `POST /v1/chat` 仍只发送 message；历史继续由后端管理 |
| CSRF | 写请求携带原 `X-CSRF-Token`，浏览器发送同源 Cookie |
| 快捷话题 | MessageList 填入受控输入框并聚焦 |
| Enter / Shift+Enter / 输入法 | Composer 处理发送、换行和 composition/229 按键 |
| 等待与重复发送 | React 状态加同步 ref 锁；发送中禁用输入和清空，避免草稿竞争 |
| 失败恢复 | 还原之前的消息列表及本轮草稿，显示错误 |
| 清空确认 | 原生 dialog 通过 React ref 控制；取消保留历史，成功后清空 |
| 文本安全 | 消息作为 React 文本节点展示，不解释成 HTML |
| 模型状态 | 保留 Gemini/OpenAI/mock 标签与所选模型、缺密钥提示 |

“密钥已配置”仍不代表已经通过模型健康或额度检查。匿名会话、最近 12 轮内存历史、角色检查局限等后端边界不因迁移改变。

## 2. 源码与构建

- `frontend/src/App.tsx`：应用状态与对话编排。
- `frontend/src/components/`：Sidebar、MessageList、Composer、ResetDialog。
- `frontend/src/api.ts` / `types.ts`：类型化接口与同源请求。
- `frontend/src/style.css`：保留原有样式。
- `frontend/vite.config.ts`：React 构建与 Vitest 配置。
- `frontend/scripts/publish.mjs`：把构建资源发布到已有后端静态目录，index 最后替换；保留旧哈希资源以免已打开页面立即失效。

本次锁定的主要工具版本：React/React DOM 19.3.1、TypeScript 7.0.2、Vite 8.3.5、Vitest 5.0.5；完整版本见 `frontend/package-lock.json`。Node.js 要求 22.12+。

构建链路：

```text
React / TS / CSS 源码
  → tsc --noEmit 严格类型检查
  → Vite 构建到 frontend/dist
  → 发布到 app/static
  → 原 FastAPI 的 / 和 /static/ 提供页面
```

日常仍执行 `./scripts/start.sh`。脚本先检查 uv、Node/npm，在依赖缺失或锁文件更新时执行 npm ci，每次启动构建前端，再启动原 Uvicorn 服务。首次安装需要网络，构建失败就退出，不静默继续使用旧页面。

独立前端命令：

```bash
npm ci --prefix frontend
npm run typecheck --prefix frontend
npm run test --prefix frontend
npm run build --prefix frontend
```

构建后刷新已有后端网页即可。直接运行 uvicorn 或 pytest 前需先完成 build；新克隆没有构建产物。`frontend/dist/`、`node_modules/`、`app/static/` 的生成内容不提交，后者仅跟踪空目录占位文件；原来的手写静态入口已移除，避免两套界面逻辑并存。

## 3. 密钥与配置

Vite 使用 `envDir: false`，不读取 `.env` 文件；`publicDir: false`，不自动复制公开文件目录。前端只请求同源相对路径，没有接收 API 密钥的参数，也不导入 Python 配置。没有定义任何暴露根目录环境的构建常量。

本地根目录 `.env` 保留现有密钥和 `gemini-3.5-flash-lite` 覆盖项，仍由后端读取，未随迁移更改。密钥不得移到源码、公开目录或 `VITE_*` 变量。提交前对源码与生成 JS/CSS 检查当前密钥值和常见密钥格式；不输出秘密值。

迁移当时F01（默认模型差异）和F02（未知往事）仍在待办；后续M2已完成F01，F02仍需更强质量回归。本迁移历史不追溯修改后端行为。

## 4. 自动验证结果

| 检查 | 结果 | 覆盖范围 |
| --- | --- | --- |
| `npm run build --prefix frontend` | 通过 | TS 严格检查、生产构建、产物发布 |
| `npm run test --prefix frontend` | 14 项通过 | 11 项组件交互及 3 项 API 客户端行为 |
| `uv run --frozen pytest -q` | 143 项通过 | 原 142 项后端/供应商回归 + 1 项 React 资源与原 CSP 加载检查 |
| `sh -n scripts/start.sh` | 通过 | 启动脚本语法 |
| Markdown 链接与 Git 差异检查 | 交付前检查 | 文档一致性、生成文件忽略与提交范围 |

前端测试包括：初始化恢复、供应商状态、快捷话题、Enter 发送、Shift+Enter 换行、中文输入法、CSRF 与原接口契约、等待与重复请求保护、错误恢复、HTML 文本转义、清空确认/取消/失败、缺密钥提示、初始化失败和输入长度属性。

Vitest 使用模拟 fetch 和 jsdom；dialog 的原生方法由测试环境补齐，因此另用实际浏览器验证弹窗，不把 jsdom 当作完整浏览器替代。测试不调用真实模型。

构建观察：主 JS 约 227 kB（gzip 约 72 kB），CSS 约 7 kB（gzip 约 2.4 kB）。这比原生脚本体积更大，是引入 React 的成本；没有进行网络性能或首屏基准测试。

## 5. 浏览器与真实模型验证

在独立本地 mock 端口检查：快捷话题填入、Enter 发送、模型回复、多轮历史、刷新恢复、原生清空弹窗及恢复欢迎页。桌面风格人工检查与原页面一致；390 × 844 视口下文档宽度等于 390，无横向溢出。

在原地址 `http://127.0.0.1:8000/` 加载 React 构建，供应商显示 Gemini、模型 `gemini-3.5-flash-lite`。使用合成输入“今天工作有点累”发送一次真实请求，网页显示：

> 听起来今天消耗了不少精力，先坐下来歇会儿吧。要不要喝杯温水，或者挑一本翻起来不费劲的闲书看看？

等待状态结束，输入恢复可用；该页面浏览器 error/warn 日志为空。此次真实交互只证明迁移后的完整链路可用，未单独计时，也没有重跑此前六轮角色评测、费用或免费额度核验。测试临时 mock 服务在结束后关闭，原 8000 服务不受影响。

## 6. 后续

迁移后M2已复用同源API客户端与React组件完成记忆管理、持久化及相关接口。正式账户与天气/情绪工具仍待后续阶段；React迁移本身不作为这些功能的完成证据。

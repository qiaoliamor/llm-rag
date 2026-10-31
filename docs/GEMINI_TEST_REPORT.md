# Gemini 适配测试记录

日期：2026-10-31（Asia/Tokyo）。本次未使用真实 Gemini 密钥，也没有向 Google 发出模型请求。

## 实现

- 默认供应商改为 Gemini，默认模型 `gemini-2.5-flash-lite`，独立读取 `GEMINI_API_KEY` / `GEMINI_MODEL`。
- 复用已锁定的 OpenAI SDK，通过 Google 官方 OpenAI 兼容 Chat Completions 接口发送请求；没有新增运行依赖。
- 系统消息包含角色约束与正史，随后附加最近会话历史；完整回复继续经过原有角色事实检查和有限重写。
- 保留 OpenAI 与 mock 模式；Gemini 缺少密钥时不使用其他供应商密钥，不自动切换模型或服务。
- 网页显示当前供应商、模型和对应环境变量提示；离线评测默认仍不调用真实 API，`--live` 使用当前配置的供应商。

## 验证结果

`uv run --frozen pytest -q`：**142 项通过**，包含原有 122 项回归及新增 20 项 Gemini 测试。

新增测试使用真实 SDK 加内存 HTTP transport，验证：

- 请求仅发送到 Google 固定官方地址，使用 Gemini 密钥，包含正确模型、system/user/assistant 消息次序与输出上限。
- 多轮上下文可传递，网页会话响应不包含密钥。
- 400、401、403、404、429、500、连接失败、超时均转为可读错误，且不泄露上游原始错误或密钥；不自动重试。
- 空回复、空候选、输出截断、内容过滤及拒绝回复不写入成功对话历史。
- 角色冲突触发有限重写；缺少 Gemini 密钥时，即使存在 OpenAI 密钥也不会调用其他服务。
- `--live` 缺少当前供应商密钥时在发起请求前退出。

其他检查：JavaScript 语法通过；原有 100 条合成 mock 场景在三组评测入口各通过 100 条字面断言。浏览器在独立测试端口验证 Gemini 名称、模型、密钥提示及发送失败保留草稿。`.env` 已被 Git 忽略，只提交空白配置模板。

## 尚待真实账号验证

用户将在本地填写密钥，因此本次不包含账号权限、实际免费额度、地区可用性、真实延迟或中文角色效果验证。填好 `.env` 后重启并发送合成消息即可检查连接；小规模对照可运行 `uv run --frozen python scripts/evaluate.py --live --limit 5`，将发出最多 15 次真实请求并消耗额度。字面断言不能替代语义评审。

Google 官方价格页将该模型列入免费档，同时也列有付费价格；代码不能保证账号处于免费计费档，应在 AI Studio 确认项目的 Free Tier 状态及限额。免费档内容可能用于改进 Google 产品，测试应使用合成经历。

参考：[官方兼容接口](https://ai.google.dev/gemini-api/docs/openai)、[官方价格与数据使用](https://ai.google.dev/gemini-api/docs/pricing)。

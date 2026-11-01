# 参与贡献

开始任务或执行检查/Git操作前，先阅读 [AGENTS.md](AGENTS.md)。默认命令行验证；任务分支推送后通过PR由管理员squash and merge。

当前为 M3 天气与本地长期记忆原型阶段，欢迎围绕功能边界、检索策略、提示工程与评测场景提出 Issue 或 Pull Request。

1. 说明具体问题、预期行为与可复现的合成示例。
2. 涉及模型效果的改动同时说明模型、数据、提示版本及对照结果。
3. 新功能同步更新需求、任务清单与相关验收场景。
4. 不提交真实玩家聊天、个人信息、密钥、未授权游戏素材或角色设定。
5. 提交前检查变更内容；先运行 `npm ci --prefix frontend`、`npm run build --prefix frontend`，再运行 `npm run test --prefix frontend` 和 `uv run --frozen pytest -q`；模型效果评测另见 README。

默认使用中文说明，可附英文摘要。贡献内容按仓库 MIT 许可证提供；第三方内容需明确来源与授权。

记忆测试必须使用临时 SQLite 或 scripts/test_postgres.py 创建的随机临时库；不要把 MEMORY_DATABASE_URL 指向真实库再清空。PG专项由脚本注入 TEST_POSTGRES_URL，不在命令行写凭据。禁止提交真实记忆、数据库或真实对话导出。

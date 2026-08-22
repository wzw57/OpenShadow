# Web UI 实现状态

更新时间：2026-08-23

实现分支：`web-ui/implementation`（待 PR 合并到 `main`）

| 能力 | 状态 |
| --- | --- |
| Web UI 设计闸门 | Accepted |
| React + TypeScript + Vite 工程 | 已实现 |
| Conversation 列表/新建/详情 | 已实现 |
| Turn 提交和幂等 | 已实现 |
| Run 状态与有限 SSE | 已实现 |
| Retry | 已实现 |
| Hermes/Deterministic 状态提示 | 已实现 |
| Runtime descriptor/status API | 已实现 |
| FastAPI `/ui` 生产静态托管 | 已实现 |
| 多用户认证和 ACL | 明确不在本切片 |
| Memory/State/Task/Action 页面 | 后续切片 |

首版完成标准：浏览器可以在单用户 profile 下创建 Conversation、发送文本、看到
Hermes 或 Deterministic 的最终回复，刷新页面后消息仍可恢复，失败可以显示并重试，
且 Provider secret 不进入浏览器。

实现位置：`apps/shadow-web`。开发运行 `npm install && npm run dev`，生产运行
`npm run build` 后启动 Shadow，访问 `/ui/`。

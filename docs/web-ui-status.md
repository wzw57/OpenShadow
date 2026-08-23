# Web UI 实现状态

更新时间：2026-08-23

首版实现分支：`web-ui/implementation`；可靠性切片当前在
`runtime/reliability-design-gate`（待按该分支闸门合并）。

| 能力 | 状态 |
| --- | --- |
| Web UI 设计闸门 | Accepted |
| React + TypeScript + Vite 工程 | 已实现 |
| Conversation 列表/新建/详情 | 已实现 |
| Turn 提交和幂等 | 已实现 |
| Run 状态与有限 SSE | 已实现 |
| Retry | 已实现 |
| 通用 Runtime descriptor/status 提示 | 已实现 |
| Runtime descriptor/status API | 已实现 |
| Conversation Run 自动回查与事件诊断 | 本切片实现 |
| Ready/Runtime 手动刷新与可恢复错误 | 本切片实现 |
| FastAPI `/ui` 生产静态托管 | 已实现 |
| 多用户认证和 ACL | 明确不在本切片 |
| Memory/State/Task/Action 查询与受控操作 | 本切片实现 |

首版完成标准：浏览器可以在单用户 profile 下创建 Conversation、发送文本、看到
外部 Runtime 或 Deterministic Adapter 的最终回复，刷新页面后消息仍可恢复，失败可以
显示并重试，且 Provider secret 不进入浏览器。本切片补齐进行中 Run 的自动回查、有限
事件诊断、readiness/runtime 手动刷新，以及四个 Profile 的按需查询和受控操作面板。
Profile 写入、审批、纠正和删除仍全部通过现有 API 与 Commit 边界完成，浏览器不执行
Provider。

实现位置：`apps/shadow-web`。开发运行 `npm install && npm run dev`，生产运行
`npm run build` 后启动 Shadow，访问 `/ui/`。

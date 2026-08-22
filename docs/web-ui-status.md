# Web UI 实现状态

更新时间：2026-08-22

| 能力 | 状态 |
| --- | --- |
| Web UI 设计闸门 | Accepted |
| React + TypeScript + Vite 工程 | 待实现 |
| Conversation 列表/新建/详情 | 待实现 |
| Turn 提交和幂等 | 待实现 |
| Run 状态与有限 SSE | 待实现 |
| Retry | 待实现 |
| Hermes/Deterministic 状态提示 | 待实现 |
| FastAPI `/ui` 生产静态托管 | 待实现 |
| 多用户认证和 ACL | 明确不在本切片 |
| Memory/State/Task/Action 页面 | 后续切片 |

首版完成标准：浏览器可以在单用户 profile 下创建 Conversation、发送文本、看到
Hermes 或 Deterministic 的最终回复，刷新页面后消息仍可恢复，失败可以显示并重试，
且 Provider secret 不进入浏览器。

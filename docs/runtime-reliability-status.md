# Runtime Reliability 实现状态

更新时间：2026-08-23

| 能力 | 状态 |
| --- | --- |
| Durable dispatch 设计闸门 | Accepted |
| Provider 前 Attempt 持久化 | 待实现 |
| 结果/失败 CAS 收敛 | 待实现 |
| Store outage / unknown outcome | 待实现 |
| Hermes normalized SSE / Run Events | 待实现 |
| Hermes Session resume | 待实现 |
| 新数据库表 / 通用 Queue | 明确不引入 |
| Hermes Tool/Capability Bridge | 后续独立闸门 |
| Web UI | 已实现，等待稳定 Runtime 状态扩展 |

实现前必须保留现有 API 路径，不新增临时 merge、runtime job 或 tool route。
实现完成标准：重启和 Store 故障路径不伪造成功；相同 idempotency key 不重复调用
Provider；Hermes event/session reference 可恢复或诚实标记 unknown。

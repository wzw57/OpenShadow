# Runtime Reliability 实现状态

更新时间：2026-08-23

| 能力 | 状态 |
| --- | --- |
| Durable dispatch 设计闸门 | Accepted |
| Provider 前 Attempt 持久化 | 已实现：turn 初始 CommitPlan 先写入 `Run=running` / `Attempt=dispatching` |
| 结果/失败 CAS 收敛 | 已实现：Provider 成功或明确异常通过第二个 CAS CommitPlan 收敛 |
| Store outage / unknown outcome | 已实现基础语义：异常结果为 `Run=waiting` / `Attempt=outcome_unknown`；结果提交失败保留 dispatching |
| Hermes normalized SSE / Run Events | 待实现 |
| Hermes Session resume | Adapter cursor/execution reference 已有 Contract；跨重启主动 reconcile 仍待独立验证 |
| 新数据库表 / 通用 Queue | 明确不引入 |
| Hermes Tool/Capability Bridge | 后续独立闸门 |
| Web UI | 已实现，等待稳定 Runtime 状态扩展 |

实现前必须保留现有 API 路径，不新增临时 merge、runtime job 或 tool route。
当前切片已满足：重启和 Store 故障路径不伪造成功；相同 idempotency key 不重复调用
Provider；Provider 异常诚实标记 unknown。主动 Hermes session resume、事件去重和真实远程
Provider 验收仍属于后续 Reliability 收口工作。

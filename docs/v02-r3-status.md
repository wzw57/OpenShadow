# v0.2 R3 状态：ExecutionCoordinator 与 Conversation extraction

状态：**Implemented locally / active flow coordinated**

已完成：

- 新增 `shadow_application.execution.ExecutionCoordinator`，作为 Application 层统一的
  typed dispatch seam；ConversationService 通过该 seam 执行 provider。
- ConversationService 的 runtime adapter 现在是构造注入项；默认 Deterministic 实现只在
  bootstrap/tests composition 选择，不再从 `shadow_application` 导入。
- submit turn 和 retry 都构造 `ExecutionRequest`，包含 Run/Attempt/Binding refs、capability
  envelope snapshot、typed input、correlation/idempotency/deadline boundary。
- Dispatcher 内部保留受限的参数名为 `text` 的 v0.1 Adapter 兼容 shim；新 Runtime 必须实现
  typed request port。
- submit turn 与 retry 的 active path 都先提交 durable Attempt/Run 边界，再由 Coordinator
  调用 provider，最后通过 CAS finalization 提交 assistant/result 或 unknown outcome。
- 既有 202/replay、Run/Attempt 持久化、restart/event 语义未改变；旧测试显式注入
  Deterministic fixture，并记录为 compatibility migration。

定向验收：Phase 1 adapter swap/export/recovery、runtime reliability、R0/R2 测试共
`16 passed, 5 xfailed`，Ruff 通过。

## 保留到 R6 的清理项

ConversationService 仍包含一段不可达的 v0.1 retry 实现，作为迁移期间的源码参照；active
路径已经使用 Coordinator。R6 删除 parallel old path 时必须同步删除该代码和兼容 shim，不能
让两条语义重新并行运行。

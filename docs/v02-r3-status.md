# v0.2 R3 状态：ExecutionCoordinator 与 Conversation extraction

状态：**Completed / active flow coordinated and legacy path removed**

已完成：

- 新增 `shadow_application.execution.ExecutionCoordinator`，作为 Application 层统一的
  typed dispatch seam；ConversationService 通过该 seam 执行 provider。
- ConversationService 的 runtime adapter 现在是构造注入项；默认 Deterministic 实现只在
  bootstrap/tests composition 选择，不再从 `shadow_application` 导入。
- submit turn 和 retry 都构造 `ExecutionRequest`，包含 Run/Attempt/Binding refs、capability
  envelope snapshot、typed input、correlation/idempotency/deadline boundary。
- Runtime Adapter 已统一实现 typed request port；Dispatcher 不再根据参数名猜测旧的文本
  调用方式，也不保留 v0.1 text shim。
- submit turn 与 retry 的 active path 都先提交 durable Attempt/Run 边界，再由 Coordinator
  调用 provider，最后通过 CAS finalization 提交 assistant/result 或 unknown outcome。
- 既有 202/replay、Run/Attempt 持久化、restart/event 语义未改变；旧测试显式注入
  Deterministic fixture，并记录为 compatibility migration。

验收证据：Phase 1 adapter swap/export/recovery、runtime reliability、R0/R2 和全量回归均
通过；当前全量 `pytest -q` 为 `292 passed`，Ruff 通过。

## R6 清理结果

ConversationService 的不可达 v0.1 retry pipeline 已删除；retry 现在只有 Coordinator 路径，
Runtime Adapter 也只接受 typed `ExecutionRequest`。旧 friendly API 仍作为显式 facade 保留，
不再复制 durable execution 语义。

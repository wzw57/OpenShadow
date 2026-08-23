# v0.2 R3 状态：ExecutionCoordinator 与 Conversation extraction

状态：**In progress / first extraction slice delivered**

已完成：

- 新增 `shadow_application.execution.ExecutionCoordinator`，作为 Application 层统一的
  typed dispatch seam；ConversationService 通过该 seam 执行 provider。
- ConversationService 的 runtime adapter 现在是构造注入项；默认 Deterministic 实现只在
  bootstrap/tests composition 选择，不再从 `shadow_application` 导入。
- submit turn 和 retry 都构造 `ExecutionRequest`，包含 Run/Attempt/Binding refs、capability
  envelope snapshot、typed input、correlation/idempotency/deadline boundary。
- Dispatcher 内部保留受限的参数名为 `text` 的 v0.1 Adapter 兼容 shim；新 Runtime 必须实现
  typed request port。
- 既有 202/replay、Run/Attempt 持久化、restart/event 语义未改变；旧测试显式注入
  Deterministic fixture，并记录为 compatibility migration。

定向验收：Phase 1 adapter swap/export/recovery、runtime reliability、R0/R2 测试共
`16 passed, 5 xfailed`，Ruff 通过。

## 尚未完成的 R3 工作

ConversationService 仍负责构造并提交 Profile-specific 的初始 CommitPlan 和结果 CommitPlan。
下一步必须把 Admission → Requirements → Binding → Attempt → provider → Run/Attempt finalization
的 durable sequencing 收进 Coordinator，Conversation 只提供 message extraction 和 profile
result builder；在此之前不得宣称 R3 完成。

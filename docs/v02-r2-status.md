# v0.2 R2 状态：Typed ExecutionRequest 与 ExecutionDispatcher

状态：**Completed / typed Runtime boundary closed in R6**

R2 已完成 Runtime boundary 的第一步：

- Kernel 新增 `ContextItem`、`CapabilityEnvelopeSnapshot` 和 typed `ExecutionRequest`，字段
  对齐 `contracts/execution/1.0.0`，仍使用现有 stable record/version refs。
- `RuntimeAdapter.execute` 的主 port 改为接收 `ExecutionRequest`；Deterministic、Hermes、
  Codex 适配器在边界内翻译 typed input，不再保留字符串调用兼容入口。
- `ExecutionDispatcher` 统一完成 adapter descriptor 注册、target/capability 选择、
  approval/revocation/deadline 最终检查、typed provider 调用和内存幂等 replay/mismatch
  语义。Dispatcher 不写 Canonical Repository。
- 未改变 Run/Attempt schema、CommitAuthority 或现有 durable pipeline；Conversation extraction
  仍留在 R3。

验收证据：R0/R2、Adapter swap、Hermes adapter 定向测试通过；当前 R6 全量回归为
`292 passed`，Ruff 通过。
`tests/test_v02_r2_dispatch.py` 覆盖 execution schema、typed dispatch、provider 前 replay、
capability/target/approval/revocation/deadline/idempotency mismatch。

## 当前边界

R2 的 Dispatcher 不负责 durable Commit；Admission → Run/Attempt 的协调由 R3 的
ExecutionCoordinator 接管。R2 不新增数据库表或 Provider-specific 分支。

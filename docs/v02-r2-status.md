# v0.2 R2 状态：Typed ExecutionRequest 与 ExecutionDispatcher

状态：**Implemented locally / targeted regression passed**

R2 已完成 Runtime boundary 的第一步：

- Kernel 新增 `ContextItem`、`CapabilityEnvelopeSnapshot` 和 typed `ExecutionRequest`，字段
  对齐 `contracts/execution/1.0.0`，仍使用现有 stable record/version refs。
- `RuntimeAdapter.execute` 的主 port 改为接收 `ExecutionRequest`；Deterministic、Hermes、
  Codex 适配器在内部翻译 typed input，并保留字符串调用兼容入口，避免旧测试和部署脚本
  突然失效。
- `ExecutionDispatcher` 统一完成 adapter descriptor 注册、target/capability 选择、
  approval/revocation/deadline 最终检查、typed provider 调用和内存幂等 replay/mismatch
  语义。Dispatcher 不写 Canonical Repository。
- 未改变 Run/Attempt schema、CommitAuthority 或现有 durable pipeline；Conversation extraction
  仍留在 R3。

验收证据：R0/R2、Adapter swap、Hermes adapter 定向测试 `13 passed, 6 xfailed`；Ruff 通过。
`tests/test_v02_r2_dispatch.py` 覆盖 execution schema、typed dispatch、provider 前 replay、
capability/target/approval/revocation/deadline/idempotency mismatch。

## 当前边界

R2 尚未把 ConversationService 的手写 Admission → Run/Attempt 流程迁移到 Coordinator；
仍保留 `shadow_application.conversation` 作为下一阶段 R3 的迁移对象。R2 也不新增 HTTP 路由、
数据库表或 Provider-specific 分支。

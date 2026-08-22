# Runtime Reliability 设计闸门

状态：**Accepted / 允许创建实现分支**  
分支：`runtime/reliability-design-gate` → `runtime/reliability-implementation`

本切片修正现有文本 Conversation 路径的可靠性边界：Provider 调用之前必须已经
持久化 Shadow Attempt；Provider 结果、外部 execution reference 和失败语义必须能
在重启、Store 故障和网络不确定时被诚实恢复。它不引入通用 Queue、Worker Platform、
新的数据库表或 Tool/Capability Bridge。

## 1. 固定范围

### 1.1 Durable dispatch

覆盖现有：

- `POST /v1/conversations/{conversation_id}/turns`；
- `POST /v1/runs/{run_id}/retry`；
- 现有 `CommitAuthority`、Canonical record version rows 和 SQLite CAS；
- `RuntimeAdapter.execute()`、`events()` 和可选的外部 execution reference。

首个 CommitPlan 原子创建或更新：

```text
User Message
Admission
Requirements
Request
Capability Envelope
Execution Binding
Run(lifecycle=running)
Attempt(lifecycle=dispatching)
Conversation(message_refs += user, foreground_run_ref = run)
```

这个 CommitPlan 成功之后，才允许调用 Provider。结果 CommitPlan 再原子创建
Assistant Message，并 CAS 更新 Run 与 Attempt：

```text
success: Run=completed, Attempt=succeeded, result_ref=assistant_message
known failure: Run=failed, Attempt=failed/incompatible
ambiguous outcome: Run=waiting, Attempt=outcome_unknown
```

Provider 结果 Commit 失败时，不得把请求返回为成功；持久化的 `dispatching` Attempt
保留为恢复和 reconciliation 的边界。

### 1.2 Idempotency 与 CAS

- Phase 1 和 Phase 2 使用同一个 `turn:{conversation_id}` 或 `retry:{run_id}` scope；
- 相同 `Idempotency-Key` 和 request digest 重放必须在 Provider 调用之前返回已有引用，
  不得再次执行 Provider；
- 相同 key 搭配不同 digest 返回结构化 `idempotency-mismatch`；
- Run/Attempt/Conversation 的完成 Commit 必须使用 expected version CAS；
- Store unavailable 不能创建“已成功”结果，也不能删除未完成 Attempt。

### 1.3 Hermes SSE / Run Events

External Runtime Adapter 继续是独立 `shadow.agent-runtime` 边界，不导入任何 Runtime
内部对象。Hermes 只是当前参考 Adapter，不进入 Reliability Core 或 Web UI。首个
可靠性实现只做：

- 将 Hermes Chat/Run 事件解析为 Shadow normalized event：cursor、event type、
  execution reference、session reference、usage、terminal state；
- `events(execution_ref, after_cursor)` 支持 cursor 增量查询，重复读取不产生新的
  Canonical record；
- 将外部 terminal result 与 Shadow Run/Attempt 的 CAS 完成 Commit 对齐；
- 保留 opaque `execution_ref` / `session_ref`，不保存 Provider secret 或 Hermes 私有
  Memory。

Token delta 可以作为传输事件，但首版不承诺逐 token 的 Canonical 持久化，也不开放
工具调用。

### 1.4 Session resume

- Shadow Run/Attempt ID 与 Hermes Session ID 永远分离；
- 重启后优先使用持久化 `execution_ref` / `session_ref` 查询 Hermes 状态；
- Hermes 不支持可靠查询时，Attempt 必须进入 `outcome_unknown`，不能伪造完成或盲目重试；
- resume 只收敛当前 Attempt，不自动创建新的 Shadow Run；
- 不新增 Shadow Session 表。

## 2. 失败语义

| 情形 | Attempt | Run | HTTP 行为 |
| --- | --- | --- | --- |
| Provider 明确成功 | `succeeded` | `completed` | 返回 durable result |
| Provider 明确拒绝/协议错误 | `incompatible` 或 `failed` | `failed` | 结构化错误 |
| Provider 连接超时/响应不确定 | `outcome_unknown` | `waiting` | 不声称成功，不盲目重试 |
| Provider 成功但 Store 无法提交结果 | 保持 `dispatching` | 保持 `running` | `503`，等待恢复/reconciliation |
| 初始 Attempt Commit 失败 | 不创建 Attempt | 不创建 Run | `503` 或结构化 Commit 错误 |
| 同 key 不同请求 digest | 不变 | 不变 | `409` idempotency mismatch |

`waiting` / `outcome_unknown` 只能通过外部查询或明确人工证据收敛为
`completed` / `failed`，不得由 UI Retry 按钮直接盲重试。

## 3. 原子性与重启

- Admission、Run、Attempt 的初始边界一次 CommitPlan 原子提交；
- 结果和失败状态一次 CAS CommitPlan 原子提交；
- Domain Event 只在对应 Commit 成功后追加；
- 重启恢复依据 Canonical Run/Attempt，不依赖进程内缓存；
- 外部事件重复投递按 execution reference + cursor 去重；
- 不新增 SQL migration、公共临时路由或通用 outbox。

## 4. 明确不在本切片

- Hermes Tool/Capability Bridge、Action/Outbox 副作用执行；
- 多 Agent、Subagent、Delegation；
- 通用 Queue、Worker、Scheduler 或后台 Job Platform；
- Provider 私有 Memory、Prompt Cache 或 Secret Backup；
- Web UI 新页面；现有 UI 只消费稳定的 Run/Message 状态；
- 完整多用户 ACL 与 Phase 5。

## 5. 验收闸门

- [x] Provider 调用前 Attempt 已持久化的契约已冻结；
- [x] 成功、明确失败、未知结果和 Store outage 语义已冻结；
- [x] Idempotency/CAS/重启关系已冻结；
- [x] Hermes event/session 的 opaque reference 边界已冻结；
- [x] 不新增表、工具或公开临时路由；
- [ ] implementation branch 的代码、测试、迁移和真实 Hermes 验收完成。

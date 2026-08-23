# v0.2 R6 状态：旧路径清理、文档同步与发布验收

状态：**Completed locally / ready for integration**
分支：`v02/r6-release-acceptance`

## 已完成

- 删除 `ConversationService.retry_run` 中不可达的 v0.1 并行 durable pipeline；retry 只有
  `ExecutionCoordinator` 路径。
- Runtime Adapter 统一接收 typed `ExecutionRequest`；Dispatcher 和 Deterministic、Hermes、
  Codex Adapter 不再保留字符串参数猜测或 `request_text` 兼容 shim。
- R4/R5 generic Server dispatch、InputHandlerRegistry、ExtensionRegistry、records API 和
  Store capability protocols 保持 vendor-neutral；friendly routes 仅作为兼容 facade。
- 更新 R0–R5 状态、v0.2 audit、documentation-sync、OpenAPI static/runtime contract tests。
- 不新增数据库表、不改变 Canonical Envelope、CommitAuthority、CAS、Owner/Space、幂等或
  durable Request/Run/Attempt 语义。

## 验收证据

```text
pytest -q                         292 passed
ruff check ...                    passed
alembic upgrade head              passed (isolated sqlite://)
alembic downgrade base            passed (isolated sqlite://)
git diff --check                  passed
```

定向测试还覆盖 example Profile generic input/records、Extension discovery、typed Runtime
dispatch、Hermes contract adapter、restart/recovery、OpenAPI runtime/static 同步和 owner/space
隔离。仅保留 FastAPI/httpx 与 jsonschema 的上游 deprecation warnings，不影响验收结果。

## 明确边界

R6 不新增业务 Profile、Store migration、远程网络 Contract fetch、通用 Queue/Event Bus 或
真实 Provider 业务联动。`shadow_kernel.models` 中的 Conversation payload 类型仍作为旧外部
导入的兼容保留项；Application 当前使用它们只为保持既有 Canonical schema 和数据兼容，未来
若迁移到独立 Profile package，必须另建 ADR 与 migration gate。

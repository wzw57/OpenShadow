# Phase 0–1 实现状态

更新时间：2026-08-22

本文件记录 Stage 5 首个纵向切片的实际交付边界。它不改变已接受的 Stage 4
Contract；Phase 2–5 的设计仍以[分阶段实现计划](implementation-stages.md)和
[Contract 基线](contract-baseline.md)为准。

## 已实现

- Kernel 仅暴露 Repository Port、稳定 ID、Canonical Envelope、Commit Authority、
  Schema Registry、Admission 和 Adapter Binding 原语；不依赖 FastAPI、SQLAlchemy 或
  Profile 业务实现。
- SQLite Store Adapter 承担 SQLAlchemy Entity、WAL / foreign-key 配置、CAS 版本提交、
  幂等记录和 Run Event 持久化。
- Contract Registry 对 checked-in JSON Schema 做离线 `$ref` 解析、manifest digest 校验
  与 Draft 2020-12 校验。
- Phase 0 的 Commit / Expected-Version / Idempotency、Admission、Capability Binding、
  unknown target kind 和 Deterministic Adapter 验证路径。
- Phase 1 的本地 Conversation / Message API、work-bearing turn、Admission → Request →
  Run → Attempt、Result Commit、SSE Run events、幂等重放和 Store unavailable 响应。
- Phase 1 的最小 Memory Candidate → Commit 边界与 `/v1/memories` 用户命令；普通对话结果
  不会自动成为 Memory。
- Runtime base Port 的 `describe` / `execute` / `events` 形状、Deterministic Adapter 实现
  以及 SQLite 重启后的 Conversation、Run、Attempt 和 SSE event 恢复测试。
- Runtime Adapter 可替换性 Contract Test：替换 target kind 和输出实现不改变 Conversation、
  Message、Request 或 Run 的 Shadow 稳定 ID。
- Canonical Export fixture 基线：按稳定 `record_id` / `version` 顺序序列化记录，计算
  manifest / record digest，并在读取时校验篡改；它是后续 Import/restore 的输入基线，不是
  Phase 2 的跨 Store 写入编排。
- 本地开发和 CI 的 `ruff`、`pytest` 基线，测试覆盖 Contract fixtures、Repository CAS /
  replay、API loop 和 outage path。

## Phase 0–1 验收矩阵

| 能力 | 当前状态 | 主要证据 |
| --- | --- | --- |
| Kernel / Canonical Envelope / Commit | 已实现 | `test_phase0_repository.py`、`test_declared_contract_fixtures.py` |
| Expected Version / Idempotency / CAS | 已实现 | `test_atomic_create_and_expected_version_conflict`、`test_committed_batch_replays_exactly` |
| Admission → Request → Run → Attempt | 已实现 | `test_admission_is_atomic_and_degrades_explicitly`、`test_personal_shadow_loop_and_replay` |
| Adapter Binding / capability boundaries | 已实现 | `test_adapter_binding_rejects_unknown_target_and_required_capability` |
| Conversation / Message / Retry / SSE | 已实现 | `test_personal_shadow_loop_and_replay` |
| Memory Candidate → Commit | 已实现 | `test_memory_candidate_requires_commit`、Memory API tests |
| Restart recovery | 已实现 | `test_restart_recovers_canonical_conversation_and_run_events` |
| Export serialization fixture | 已实现 | `test_phase1_export.py` |
| Store unavailable / explicit degradation | 已实现 | `test_store_outage_does_not_claim_durable_success`、Admission outage test |
| Alembic migration / rollback | 已实现 | CI isolated SQLite migration step |

OpenAPI 中的 Memory correction/delete 已在 Phase 2 首个切片获准并进入独立实现分支；
Proposal decision、Portable Import/restore、Backup、Outbox 和 Erasure Job 仍是后续
Contract-only 能力。本阶段的 Export 仍仅作为 Store Adapter fixture，不提供公开 HTTP
Export API。

## 当前明确不在实现范围

- Memory Intelligence、State、Durable Task、Action、Router、Pulse；
- PostgreSQL、远程 Runtime、OpenAI Model Adapter、React Web Client；
- Portable Import / restore、Backup、Outbox、Erasure Job（Export serialization fixture 已具备）；
- 多 Endpoint、多用户 ACL、共享 Space 与设备 / 语音协议。

这些能力保留 Contract、Profile 或退出条件，但不提前建设空服务、万能接口或未来基础
设施。

## 本地验证

在仓库根目录运行：

```powershell
python -m pip install -e ".[dev]"
ruff check packages/shadow-kernel/src packages/shadow-application/src adapters/test-deterministic/src adapters/store-sqlite/src apps/shadow-server tests
pytest -q
$env:SHADOW_DATABASE_URL = "sqlite://"
alembic upgrade head
alembic downgrade base
```

启动本地服务：

```powershell
uvicorn shadow_server.app:app --reload
```

默认 SQLite 文件位于 `.shadow/shadow.db`；该文件属于运行产物，不提交到 Git。

## 下一步闸门

后续实现必须保持：所有 Canonical write 经过 Commit、所有 work-bearing input 经过
Admission、Adapter 不能直接写 Store、Store 故障不伪造持久成功。Alembic migration /
rollback、restart recovery、retry → Attempt 与 Export fixture 的 Phase 0–1 基线已具备；
Phase 2 首个 Memory 生命周期切片的状态见
[phase2-memory-lifecycle-status.md](phase2-memory-lifecycle-status.md)。Portable Import /
restore、Recall、Maintenance、SkillAsset、Integration 和 Erasure 仍须各自完成设计闸门
后才能实现。

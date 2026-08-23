# v0.2 R5 状态：Generic Records API、Extension discovery 与 Store injection

状态：**Implemented locally / generic surface delivered**

已完成：

- 新增 `GET /v1/extensions`，由共享 `ExtensionRegistry` 返回内建 Profile 和已注入 Runtime
  descriptors；RuntimeSupervisor 可把 Adapter descriptor 发布到同一 registry，生命周期
  控制与 Extension discovery 仍分离。
- 新增 `GET /v1/records/{record_id}`、`GET /v1/records`，支持 owner/space、record type、
  record state 和 limit 过滤；跨 owner 的 personal record 返回 404，避免对象存在性泄漏。
- 新增 `POST /v1/inputs`，通过 `InputHandlerRegistry` 接收 namespaced payload；内建 Proposal
  handler 与示例 Profile handler 共用同一输入边界。
- `create_app` 支持注入 `store_factory`，SQLite/Postgres 默认 factory 仍保持兼容；Kernel
  `CanonicalRepository` 已收缩为基础能力，Run events、physical erase、portable transfer
  划为可选 capability protocols。
- Server proposal/records/inputs 路由使用 registry 和 generic query；旧 friendly API 继续
  保留作为 facade。

验收证据：R0/R4/R5、Phase 1 API、Phase 3 State/Completion、Phase 4 Action、Runtime
Management 定向回归通过；全量 `pytest -q` 为 `290 passed`，Ruff、Alembic upgrade/downgrade
和 `git diff --check` 通过。`tests/test_v02_r5_generic_api.py` 覆盖 extension discovery、
generic input/record 查询、owner/space 隔离、store factory 注入以及 runtime/static OpenAPI
路径同步。

## 当前边界

本阶段没有新增数据库表；records API 仍是基于现有 Canonical version rows 的只读 facade，
没有引入独立 GenericRecord 模型。R6 仍需删除 Conversation 的不可达旧 retry 实现、清理
兼容 shim，并完成最终架构边界、文档索引和发布前验收。

# OpenShadow v0.2 架构重构审计与分阶段计划

状态：**Audit complete / design-first；尚未进入 R0 业务实现**
基线：当前 `main`（Phase 0–4、Phase 5 Core Slice 以及 production A–E 本地参考切片）
目标：把 v0.1 的“可运行参考实现”收口为真正可扩展的 v0.2，而不改变 Kernel 的
Canonical、CAS、CommitAuthority、幂等和离线 Contract digest 语义。

本文件对应 v0.2 重构请求的第一步：先记录当前实现事实、差距、兼容边界和验收顺序。
在维护者接受本计划前，不创建 ExtensionRegistry、Dispatcher 或新的通用 API。

## 1. 审计结论

当前项目的核心持久化和安全边界是可复用的，但扩展边界还没有真正落地。主要问题不是
缺少更多业务 Profile，而是“通用层仍然知道参考 Profile 的名字和流程”。因此继续添加
Profile 会放大耦合，不能满足“新增 Runtime/Profile Extension 不改 Kernel 与 generic Server
dispatch”的 v0.2 目标。

### 1.1 已有且必须保留的基线

- `CanonicalEnvelope`、stable record/version、owner/space、expected-version/CAS、
  `CommitAuthority` 和 idempotency 已由 Kernel/Store 共同实现。
- Proposal → validate → Commit 已在 State、Task、Action 等服务中形成可测试的纵向闭环。
- Run、Attempt、Checkpoint、Outbox、Action Result 等 durable record 已存在，不能在重构中
  重新发明第二套持久化模型。
- Contract 文件已签入仓库并在加载时做 SHA-256 校验；当前实现是离线可信边界，不能改成
  运行时联网拉取。
- Hermes、Codex 和 deterministic runtime 都通过运行时 Adapter 包提供；公共层已有 vendor
  neutrality 测试，必须继续保持。

### 1.2 当前实现证据与问题

| 区域 | 当前事实 | v0.2 差距 | 风险 |
| --- | --- | --- | --- |
| Kernel model | `shadow_kernel.models` 同时包含 Canonical/Commit 模型和 `ContentBlock`、`ConversationPayload`、`MessagePayload` 等 Conversation Profile 模型。 | Kernel 只应保留最小稳定原语；Profile typed payload 应由 Extension 提供。 | 新 Profile 必须改 Kernel，形成反向依赖和发布耦合。 |
| Conversation | `ConversationService` 在构造时默认导入并实例化 `DeterministicTestAdapter`，并在 `submit_turn`/retry 流程中手写 Admission、Request、Run、Attempt 和 Runtime 调用。 | 提取 `ExecutionRequest`、`ExecutionDispatcher`、`ExecutionCoordinator`；Conversation 只保留 extraction/compatibility facade。 | durable execution 语义分叉，新增 Runtime 需要改 Application。 |
| Proposal API | `apps/shadow-server/shadow_server/app.py` 声明 `StateProposalCommand \| TaskProposalCommand \| ActionProposalCommand \| ActionApprovalProposalCommand`，再用 `isinstance` 分支。Accept 也按 proposal type 分支。 | Server 应将 namespaced input 交给注册表处理器；内建 Profile 与扩展 Profile 使用同一边界。 | 每个新 Profile 都必须修改 generic server。 |
| Runtime registry | `RuntimeSupervisor` 拥有自己的 `_adapters` 注册表；`ConversationService` 又单独持有 `runtime_adapter`，选择 Runtime 时再手动 `install_runtime_adapter`。 | 统一 Extension/Adapter composition；Supervisor 只管理生命周期，Dispatcher 通过共享注册表取能力。 | UI、Supervisor、Conversation 看到的 active runtime 可能不一致。 |
| Contract registry | `ContractRegistry` 只读取一个 `contracts/manifest.json`，把所有 schema 直接放入一个 dict。 | 支持 core pack + extension pack、显式 `register_pack`、重复 schema_id 的兼容/冲突检测，并保持离线 digest 校验。 | 第三方 contract 无法独立发布；同名 schema 可能被静默覆盖。 |
| Store port | `CanonicalRepository` Protocol 强制要求 `erase_history`、`append_event`、`events` 等可选能力。 | 基础 repository + capability protocols；由 Service 在能力缺失时返回结构化 unsupported。 | 轻量 Store 适配器被迫实现不使用的历史擦除/事件接口。 |
| Server composition | `create_app` 直接导入并实例化所有内建 Service，并直接绑定 SQLite/Postgres factory。 | composition root 负责加载 Extension、Contract pack、Store factory；路由按能力拆分。 | Server 难以测试和替换；引入新 Extension 必须改入口。 |
| Public generic API | 当前有各 Profile 的 friendly endpoints，但没有统一 `GET /v1/extensions`、`GET/POST /v1/records`、`POST /v1/inputs`。 | 新增通用查询/输入边界，同时保留旧 friendly API 作为显式兼容 facade。 | 外部 Extension 无稳定 API 入口，客户端被迫知道内建路由。 |

审计扫描还确认：Kernel 没有发现反向导入 Application 的证据；vendor neutrality 测试也在
阻止 Hermes/Ollama/DeepSeek 等名称进入公共层。这些是现有安全边界，R0 必须把它们提升为
架构测试，而不是依赖人工约定。

## 2. v0.2 目标依赖图

```text
                 +---------------------------+
                 |  shadow-server (generic)  |
                 |  records / inputs / query  |
                 +-------------+-------------+
                               |
                     ExtensionRegistry
                  +------------+-------------+
                  |                          |
          ContractRegistry              Handler registries
       (core + extension packs)      (proposal/input/profile)
                  |                          |
        +---------v---------+       +--------v---------+
        |   shadow-kernel   |       |  shadow-application|
        | envelope/CAS/     |       | services +         |
        | admission/commit  |       | coordinator        |
        +---------+---------+       +--------+---------+
                  |                          |
              StoreFactory              Dispatcher/Adapter
                  |                          |
        +---------v---------+       +--------v---------+
        | Canonical Store  |       | Runtime/Profile   |
        | base + capabilities|      | Extensions       |
        +-------------------+       +------------------+
```

依赖方向固定为：`kernel ← application ← server`；Adapter/Extension 只实现 ports，不能被
Kernel 或 generic Server 按厂商/内建 Profile 反向导入。Extension 可以依赖 Kernel ports 和
Contract SDK，但不能修改 Kernel 代码来注册自己。

## 3. 分阶段改造计划

每个 R 阶段是独立分支和独立验收；完成前不得把后阶段代码偷偷带入当前阶段。

### R0 — Architecture tests 与 extension fixtures

目标：先把“可扩展”变成可失败的测试，而不是口头约定。

交付：

1. `example_profile_extension`：只通过测试 composition 注册一个 typed Profile、schema、
   proposal/input handler 和 query descriptor；不修改 Kernel 或 generic Server。
2. `example_runtime_extension`：只实现 Runtime/Execution ports，通过测试装配后可被发现和
   调用；不在公共层出现 Hermes/Codex 等 vendor 名称。
3. 架构测试：Kernel 不导入 Application/Adapters；generic Proposal dispatch 不出现
   `State/Task/Action` 分支；Contract 解析不允许网络；旧 friendly API 仍走同一服务。
4. 记录现有失败点，作为后续 R1–R6 的退出条件，而不是先放宽断言。

不做：不创建生产 ExtensionRegistry，不迁移 Conversation，不增加公开路由。

### R1 — ExtensionRegistry 与多 Contract Pack

交付：

- `ExtensionDescriptor`、版本、namespace、capabilities、contract pack 引用和 handler
  descriptor 的不可变注册模型；重复 extension id、重复 schema id、版本不兼容都拒绝。
- `ContractPack`/`ContractRegistry.register_pack`：core pack 先加载，extension pack 仅接受
  签入文件和 manifest digest；禁止 URL fetch；同 schema id 必须字节/语义兼容，否则返回
  结构化冲突。
- 只在 composition root 装配注册表；Kernel 不知道具体 Extension。
- `/v1/extensions` 的 descriptor 查询可以在 R1 提供，但不在此阶段迁移 Proposal。

兼容：保留 `ContractRegistry(root)` 作为 core-pack 兼容构造器；旧 tests 继续通过。

### R2 — ExecutionRequest 与 Dispatcher

交付：

- 将当前 ConversationService 中手写的 Request/Requirements/Binding 选择抽为稳定的
  `ExecutionRequest`、`ExecutionDispatcher` ports。
- Dispatcher 只做 capability/target/expiry/approval/revocation 最终检查并选择已注册
  Runtime；Provider 调用仍由 Adapter 完成。
- 先保留现有 Run/Attempt record schema、状态机和幂等 scope；不得新增平行 execution 表。
- deterministic、Hermes、Codex 通过相同 port 做 contract fixtures。

### R3 — ExecutionCoordinator 与 Conversation extraction

交付：

- `ExecutionCoordinator` 负责 Admission → Request → Run → Attempt → Result 的 durable
  顺序、restart/retry 和 SSE event；Conversation 只负责 message extraction、conversation
  refs 和兼容返回体。
- Provider 调用前必须已持久化 executing/attempt；unknown 保持现有 reconciliation 语义。
- 旧 `submit_turn`、retry、resume API 改为 facade，保持 202/200 replay 和 stable refs。
- 删除 `ConversationService` 对 deterministic adapter 的默认业务耦合；默认 adapter 在
  composition root 注入。

### R4 — Generic proposal/input registries 与内建 Extension 迁移

交付：

- `ProposalHandlerRegistry`、`InputHandlerRegistry` 和 namespaced typed payload adapter。
- State、Task、Action、Action Approval 迁移为内建 Extension handler；Server 的 generic
  route 只解析 envelope/namespace，然后调用注册表。
- `POST /v1/proposals`、accept、`POST /v1/inputs` 使用统一错误、幂等和 owner/space 传递。
- 旧 Profile route 保留为 thin facade，并增加“facade 与 generic path 结果一致”测试。

### R5 — Generic records API、Server 分解、Store factory/capabilities

交付：

- `GET /v1/records/{record_id}`、`GET /v1/records`：按 owner/space、record type、state、
  limit/cursor 查询；响应不泄漏未经授权的 typed payload。
- Server 拆成 generic routes、auth/context middleware、profile route modules 和 composition
  root；generic 层不 import 内建 Service 类名。
- `StoreFactory` 注入接口；SQLite/Postgres 适配器实现同一 factory contract；
  `CanonicalRepository` 拆为 base port 与 `EventStoreCapability`、`ErasureCapability`、
  `PortableTransferCapability` 等可选协议。
- 缺少能力时返回 `shadow.capability.unsupported`，不伪造成功。

### R6 — 删除并行旧路径、文档同步与发布验收

交付：

- 删除已迁移的 server `isinstance` 分支、Conversation 内重复 durable pipeline、独立
  runtime registry 和未使用的 store-specific 假接口；仅保留有明确 deprecation 注释的
  compatibility facade。
- 更新 `README.md`、`docs/architecture.md`、`docs/technical-architecture.md`、
  `docs/roadmap.md`、`docs/documentation-sync.md` 和 ADR index；所有“当前已实现”描述以
  测试/CI 证据为准。
- 运行完整旧测试、R0 架构测试、Extension fixtures、OpenAPI static/runtime sync、
  Ruff、Alembic upgrade/downgrade、git diff check。

## 4. 兼容与禁止事项

### 兼容策略

- Canonical record type、version、owner/space、CommitPlan、idempotency scope 和现有
  error code 在 R0–R6 中保持兼容；确需变化时先加 adapter，再删除旧路径。
- `shadow_kernel.models` 中现有导出先保留 re-export/deprecation shim；直到 R6 所有应用和
  tests 已迁移，才移除 Conversation Profile 定义。
- `/v1/conversations`、`/v1/states`、`/v1/tasks`、`/v1/actions` 等 friendly API 继续存在，
  但实现必须委托 generic handler，不能形成第二套语义。
- `ContractRegistry(root)`、`RuntimeAdapter` 旧调用方式在过渡期间保留适配层；新代码只依赖
  新 ports。

### 本次重构禁止事项

- 不修改 Kernel 的 Canonical/Commit 原语来适配某个 Profile 或 Runtime。
- 不在 generic Server 中添加新的 Profile `if/elif`、`isinstance` 或 vendor import。
- 不新增并行 Request/Run/Attempt/Proposal/Store 表。
- 不把 Extension discovery、Contract validation 或 Runtime execution 改为联网动态下载。
- 不把 Hermes、Codex、DeepSeek、Ollama 等厂商名写入 Kernel、generic Application、
  generic Server 或 Web UI。

## 5. 验收矩阵

| 闸门 | 必须证明 |
| --- | --- |
| R0 architecture | example Profile/Runtime 仅靠 composition 注册；Kernel 无反向依赖；generic dispatch 无内建分支；网络访问扫描为空。 |
| R1 registry | core + extension packs 离线加载；digest、namespace、重复/冲突 schema 和版本错误均结构化失败。 |
| R2 dispatcher | 所有 Runtime 经过同一 dispatcher；capability/deadline/approval/revocation 检查一致；持久 Run/Attempt 语义不变。 |
| R3 coordinator | restart/retry/SSE/idempotency 通过统一 coordinator；provider 前 durable；unknown 不盲重试。 |
| R4 handlers | State/Task/Action 的 generic proposal/input 路径与 friendly facade 结果相同；新增 example Profile 无 server 修改。 |
| R5 generic API/store | records/query/extensions/input API 有 owner/space 隔离；Store factory 可替换；可选能力缺失返回 unsupported。 |
| R6 release | 全量 pytest、Ruff、Alembic upgrade/downgrade、OpenAPI/runtime sync、vendor neutrality、documentation drift、git diff check 全部通过。 |

推荐的每阶段验收命令：

```powershell
ruff check packages/shadow-kernel/src packages/shadow-application/src adapters/test-deterministic/src adapters/store-sqlite/src apps/shadow-server migrations tests
pytest -q
$env:SHADOW_DATABASE_URL = "sqlite://"
alembic upgrade head
alembic downgrade base
git diff --check
```

## 6. 当前决策与下一步

本审计没有发现必须推翻现有 Phase 0–5 业务基线的理由；正确路径是“抽 ports、迁移 composition、
最后删除旧路径”，而不是重写所有 Service。下一步只进入 **R0：架构测试和 extension fixtures**。

R0 完成的标志是：至少一个不属于内建 Profile 的 example extension 在测试 composition 中被
注册、发现、校验和调用，同时生产代码和 generic Server 无任何针对该 example 的分支。
在 R0 通过前不实现 R1 registry 或任何新的业务 API。

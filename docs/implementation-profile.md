# OpenShadow 参考实现 Profile

- 状态：Stage 4 Proposed — D1–D8 已冻结，等待 PR 最终评审与合并
- 作用：定义 OpenShadow 第一套官方实现使用的技术组合
- 约束：本文件不是 Shadow Domain Contract；具体技术可以通过兼容实现或 Adapter 替换
- 上位文档：[完整技术架构](technical-architecture.md)
- 实现顺序：[分阶段实现计划](implementation-stages.md)
- Contract 基线：[Stage 4 Contract Baseline](contract-baseline.md)

## 1. 决策原则

完整目标架构先于参考实现。参考实现必须验证长期边界，但不得把 Framework、数据库、模型或 Runtime 私有类型带入 Domain。

以下内容长期稳定：

- Shadow Domain Semantics；
- Canonical Record 与 Stable ID；
- Port Family 与 Capability Negotiation；
- JSON Schema / OpenAPI Contract；
- Authority、Binding、Envelope 和状态转换；
- Export、Migration 和 Integrity 语义。

以下内容属于可替换实现：

- Python Web Framework；
- ORM 与数据库驱动；
- Web Client Framework；
- Runtime、模型和 Provider SDK；
- Adapter Transport；
- 数据库引擎；
- 构建、打包和部署工具。

## 2. 已接受的参考技术组合

| 领域 | 参考实现 | 长期边界 |
|---|---|---|
| Core language | Python | Domain Contract 与语言无关 |
| Domain validation | Python typed models / Pydantic implementation | Checked-in JSON Schema 是跨语言事实源 |
| Server | FastAPI | REST / OpenAPI / event-stream contract |
| Web client | React + TypeScript + Vite | Shadow Client API |
| Command / query API | REST / JSON | OpenAPI 3.1 |
| Chat / Run streaming | Server-Sent Events | Versioned Execution Event Envelope |
| Future voice transport | WebSocket | Interaction Port |
| Contract source | Checked-in JSON Schema + OpenAPI | Compatibility and Contract Tests |
| In-process Adapter | Python Port / Protocol | Adapter Contract |
| Isolated Adapter | UTF-8 NDJSON Message Envelope over stdio | Transport-neutral Adapter Envelope |
| Primary local Store | SQLite file database with WAL | Canonical Repository Capability |
| Relational access | SQLAlchemy | Repository / Unit of Work boundary |
| Schema migration | Alembic | Shadow Migration Semantics |
| Second Store profile | PostgreSQL | Same Canonical semantics |
| Reference model execution | OpenAI Model Adapter | Model Worker Port |
| Reference external runtime | Process Runtime Adapter | Agent Runtime Port |
| Test execution | Deterministic Test Adapter | Contract Test baseline |

依赖的具体版本由每次 OpenShadow Release 锁定，不在长期架构文档中冻结。升级依赖必须通过 Contract Test、Schema Migration 和回滚验证。

## 3. Repository 结构

~~~text
OpenShadow/
├─ apps/
│  ├─ shadow-server/
│  └─ shadow-web/
├─ packages/
│  ├─ shadow-kernel/
│  ├─ shadow-profiles/
│  │  ├─ conversation/
│  │  └─ memory/
│  ├─ shadow-application/
│  ├─ shadow-contracts/
│  ├─ shadow-adapter-sdk/
│  └─ shadow-testkit/
├─ adapters/
│  ├─ store-sqlite/
│  ├─ model-openai/
│  ├─ runtime-process/
│  └─ test-deterministic/
├─ migrations/
├─ docs/
└─ tests/
~~~

### 3.1 依赖方向

~~~text
shadow-web
    -> Shadow HTTP / Event API

shadow-server
    -> shadow-application
        -> shadow-kernel
        -> shadow-profiles
        -> shadow-contracts
        -> family Port interfaces

profiles
    -> kernel contracts
    -X-> concrete Adapter / infrastructure

adapters
    -> family Port interfaces
    -> external SDK / database driver

shadow-kernel
    -X-> FastAPI
    -X-> SQLAlchemy
    -X-> Pydantic transport models
    -X-> profile business payloads
    -X-> model / Runtime SDK
~~~

Kernel 可以使用 Python 标准类型和自身 Value Object。Profile Validator、API DTO、Pydantic Transport Model、ORM Entity 和外部 SDK Object 必须在边界映射。

Memory、State、Skill 等 Profile 不得通过 import 反向扩张 Kernel 类型分支。

## 4. API Profile

### 4.1 REST / JSON

REST 用于：

- 创建 Request；
- 查询 Conversation、Run、Task、Memory 和 World State；
- 提交取消、批准、纠正和删除命令；
- 管理 Adapter、Integration、Binding 和配置；
- 启动 Export、Migration 和其他 OperationJob。

API 使用 OpenAPI 3.1。写命令必须支持 idempotency key；资源更新使用显式 version 或等价条件写入。

### 4.2 Server-Sent Events

SSE 用于浏览器接收：

- message delta；
- Run state transition；
- Execution progress；
- tool / capability boundary notice；
- approval required；
- final result；
- structured failure。

SSE 断开不等于取消 Run。客户端使用 last event id 或 Run 查询恢复可见状态。高频 delta 可以是临时传输数据，最终状态仍由 Canonical Record 决定。

### 4.3 WebSocket

WebSocket 不作为普通 Chat 的默认协议。它为未来双向音频、实时设备 Endpoint 和低延迟交互保留。WebSocket 消息仍须携带 Endpoint、Owner / Space、correlation 和版本信息，并经过 Admission。

## 5. Contract Profile

### 5.1 跨语言事实源

以下 Schema 必须独立保存并纳入兼容性测试：

- Canonical Record Envelope；
- Profile Descriptor / Proposal Envelope；
- AdapterDescriptor；
- Capability Declaration；
- Execution Request / Event；
- common Message Envelope / Shadow Error；
- family-specific Result；
- Execution Binding / Capability Envelope；
- Version Negotiation；
- Export Manifest。

Python Model 和 TypeScript Type 可以由 Schema 生成或双向校验，但不能成为唯一事实源。

不建立一个覆盖所有 Port 的万能 Result union。Execution / Intelligence Family 与 Store / Secret / Interaction Family 分别维护 typed payload。

### 5.2 兼容性

Contract 使用 major / minor 兼容模型：

- minor：增加可选字段、可选 Capability、namespaced target kind 或 Profile extension；
- major：删除字段、改变语义、收紧必填条件或改变状态含义；
- 接收方忽略明确允许的未知扩展字段；
- 未识别的 required Capability 必须拒绝 Binding；
- 未识别 target kind 不能仅因名称未知而拒绝，先按 Descriptor 与 Capability 校验；
- Canonical Profile Migration、physical Store Migration 与 Adapter Contract Upgrade 分开管理；
- Profile major upgrade 必须包含语义 Migration，不能只更新 JSON Schema。

## 6. Adapter Transport Profile

### 6.1 进程内

可信、轻量官方 Adapter 可以实现 Python Family Port。进程内实现仍必须通过相同 Contract Test，不能直接访问 Canonical Repository 或绕过 Authority。

Runtime 基础 Port 只有 `describe`、`execute`、`events`。其他 Family 使用自己的最小方法集合。

### 6.2 进程外

第一种隔离 Transport 使用 UTF-8 NDJSON Message Envelope over stdio：每行一个完整 Envelope，stdout 只承载协议，stderr 只承载清洗后的日志，大对象通过 ArtifactRef 传递。

所有 Adapter 支持：

- initialize / version negotiation；
- describe；
- health；
- shutdown。

Runtime Family 基础消息：

- execute；
- events。

可选消息按 Capability Negotiation 启用：

- progress；
- usage；
- cancel；
- checkpoint；
- native resume；
- semantic handoff；
- artifact；
- reconcile。

Adapter 不得因为 Transport 存在某个方法，就声称实现该 Capability。Artifact、日志和大文件通过 ArtifactRef 传递，不嵌入 RPC Payload。

以后增加 HTTP、WebSocket、gRPC 或远程 Transport 时，复用 Message Envelope 与 Family Capability，不冻结成同一万能 RPC 接口。

## 7. Store Profile

### 7.1 SQLite

默认个人部署使用文件型 SQLite，并启用经过验证的 WAL 配置。SQLite Adapter 负责：

- Canonical Transaction；
- optimistic concurrency；
- idempotency record；
- migration metadata；
- integrity check；
- backup coordination；
- availability report。

SQLite 文件、WAL、驱动和连接配置属于 Store 实现细节，不进入 Domain Contract。

### 7.2 SQLAlchemy 与 Alembic

SQLAlchemy Entity 只能存在于 Store Adapter。Application 通过 Repository / Unit of Work Port 访问持久状态。

Alembic 执行参考实现的物理 Schema Migration；Shadow 另外保存逻辑 Schema Version、Migration Intent、结果和 Integrity Report。

### 7.3 PostgreSQL

PostgreSQL 是第二个官方 Store Profile，用于远程、自托管或更高并发部署。它必须通过与 SQLite 相同的 Durable Store Contract Tests。允许物理 Schema、索引和事务策略不同，不允许改变 Canonical Semantics。

## 8. Web Client Profile

第一客户端采用 React、TypeScript 和 Vite。

Web Client：

- 使用 OpenAPI 生成或校验的 API Client；
- 使用 SSE 接收 Chat / Run 事件；
- 保存纯 UI 状态和可重建缓存；
- 不直接读取数据库；
- 不持有唯一的 Conversation、Run、Task 或 Approval 状态；
- 断线后通过 Canonical API 恢复；
- 单用户阶段仍发送正式 Endpoint Context。

未来桌面端可以包装 Web Client，移动端和语音端可以使用相同 Shadow API 或 Interaction Port。

## 9. Reference Adapters

### 9.1 Deterministic Test Adapter

注册为测试用 namespaced target kind，用于验证：

- success / structured failure；
- timeout / retry；
- progress；
- supported cancellation；
- unsupported cancellation；
- cancellation_unknown；
- malformed typed payload；
- version incompatibility；
- capability declaration honesty。

它是 Contract Test 组件，不是面向用户的智能能力。

### 9.2 OpenAI Model Adapter

注册 `shadow.model-worker`，用于验证：

- structured input / output；
- streaming；
- usage；
- model data boundary；
- typed Proposal；
- provider failure；
- retention configuration。

OpenAI SDK Object 与 Provider Skill ID 不得进入 Kernel Contract。OpenAI Skills API 的目录或 zip、版本和 default version 可以成为 Provider Projection，但不是 Canonical SkillAsset。

### 9.3 Process Runtime Adapter

注册 `shadow.agent-runtime`，用于接入 Codex 类 Runtime、DeepSeek Harness 或未来 Agent Framework。

基础映射只要求 describe、execute 和 events。只有外部进程真实支持时才声明 cancel、checkpoint、native resume 或 semantic handoff。

具体 Runtime Session ID 只能作为 external_ref 或 Runtime Checkpoint Reference，不能代替 Shadow Run ID 或 Durable Task ID。

### 9.4 Agent Skills Fixture

参考实现提供标准 Agent Skills Bundle fixture：

- 必需 `SKILL.md`；
- 可选 `scripts/`、`references/`、`assets/`；
- bundle digest / immutable snapshot；
- Shadow SkillAsset sidecar metadata；
- Runtime Projection rebuild test；
- permission enforcement independent of `allowed-tools`。

Fixture 验证 Bundle 可以离开 Shadow 被标准客户端读取，且 Shadow 治理元数据不修改原 Bundle。

## 10. 测试与发布门槛

每次 Release 至少验证：

- Domain unit tests；
- API Schema compatibility；
- Adapter Contract Tests；
- SQLite migration up / down or documented rollback；
- PostgreSQL profile compatibility（启用后）；
- Fake / deterministic execution；
- Runtime and Model Adapter failure mapping；
- restart recovery；
- export / import integrity；
- dependency lock reproducibility；
- Web API client generation or compatibility。

## 11. 不变量

1. Python 是参考 Kernel 语言，不是 Adapter 生态的语言限制。
2. FastAPI、Pydantic 和 SQLAlchemy 不能成为 Domain / Profile Schema 的事实源。
3. React Client 不能直接写 Canonical Repository。
4. Memory、State、Skill 等 Profile 不得反向扩张 Kernel 依赖。
5. SQLite 只实现已声明 Store Capability，不被当成唯一 Store。
6. UTF-8 NDJSON stdio 是第一种隔离 Transport，不是永久唯一 Transport。
7. Adapter 只承诺已声明 Capability，不能伪造 cancel、checkpoint 或 resume。
8. namespaced target kind 不是封闭 enum。
9. OpenAI Model Adapter 是参考实现，不是 Shadow 模型依赖。
10. Codex、DeepSeek 或其他 Runtime 通过 Runtime Family Port 接入。
11. Agent Skills Bundle 保持标准格式；Provider Skill Object 只是 Projection。
12. 任何实现替换不得改变 Canonical ID、Owner、Proposal / Commit 或可移植语义。


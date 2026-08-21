# OpenShadow 参考实现 Profile

- 状态：Stage 4 Accepted
- 作用：定义 OpenShadow 第一套官方实现使用的技术组合
- 约束：本文件不是 Shadow Domain Contract；具体技术可以通过兼容实现或 Adapter 替换
- 上位文档：[完整技术架构](technical-architecture.md)
- 实现顺序：[分阶段实现计划](implementation-stages.md)

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
| Isolated Adapter | JSON-RPC-style messages over stdio | Transport-neutral Adapter Envelope |
| Primary local Store | SQLite file database with WAL | Durable Store Port |
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
│  ├─ shadow-domain/
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
        -> shadow-domain
        -> shadow-contracts
        -> Port interfaces

adapters
    -> Port interfaces
    -> external SDK / database driver

shadow-domain
    -X-> FastAPI
    -X-> SQLAlchemy
    -X-> Pydantic transport models
    -X-> model / Runtime SDK
~~~

Domain 可以使用 Python 标准类型和自身 Value Object。API DTO、Pydantic Transport Model、ORM Entity 和外部 SDK Object 必须在边界映射。

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

以下 Schema 必须以独立文件保存并纳入兼容性测试：

- Canonical Record Envelope；
- Adapter Manifest；
- Capability Declaration；
- Execution Request / Event / Result；
- Proposal / Observation；
- Shadow Error；
- Version Negotiation；
- Export Manifest。

Python Model 和 TypeScript Type 可以由 Schema 生成或与其双向校验，但不能成为唯一事实源。

### 5.2 兼容性

Contract 使用 major / minor 兼容模型：

- minor：只增加可选字段、可选 Capability 或新枚举处理规则；
- major：删除字段、改变语义、收紧必填条件或改变状态含义；
- 接收方必须忽略明确允许的未知扩展字段；
- 未识别的关键 Capability 必须拒绝 Binding，不能静默降级；
- Canonical Schema Migration 与 Adapter Contract Upgrade 分开管理。

## 6. Adapter Transport Profile

### 6.1 进程内

可信、轻量官方 Adapter 可以实现 Python Port。进程内实现仍必须通过相同 Contract Test，不能直接访问 Domain Repository 或绕过 Authority。

### 6.2 进程外

第一种隔离 Transport 使用 JSON-RPC-style Envelope over stdio，支持：

- initialize / negotiate；
- describe capabilities；
- health；
- execute；
- progress notification；
- cancel；
- checkpoint；
- resume；
- reconcile；
- shutdown。

Transport 只承载版本化消息。Artifact、日志和大文件通过 ArtifactRef 传递，不嵌入 RPC Payload。

以后增加 HTTP、WebSocket、gRPC 或远程 Transport 时，应复用相同领域消息和 Capability 语义。

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

用于确定性验证：

- success；
- structured failure；
- timeout；
- retry；
- progress；
- cancellation；
- cancellation_unknown；
- malformed output；
- version incompatibility。

它是 Contract Test 的必要组成，而不是面向用户的智能能力。

### 9.2 OpenAI Model Adapter

作为第一种 Direct Model 参考实现，用于验证：

- structured input / output；
- streaming；
- usage；
- model data boundary；
- tool or capability proposal；
- provider failure；
- retention configuration。

OpenAI SDK Object 不得泄漏进 Shadow Contract。更换 Provider 时不改变 Run、Binding 或 Result 的稳定语义。

### 9.3 Process Runtime Adapter

用于接入 Codex 类 Runtime、DeepSeek Harness 或未来其他 Agent Framework。它负责把外部进程的 session、progress、checkpoint、result 和 cancellation 映射为 Agent Runtime Port。

具体 Runtime 的 Session ID 只能作为 external_ref 或 Runtime Checkpoint Reference，不能代替 Shadow Run ID 或 Durable Task ID。

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

1. Python 是参考 Core 语言，不是 Adapter 生态的语言限制。
2. FastAPI 不能成为 Domain 或 Canonical Schema 的事实源。
3. Pydantic Model 不能取代 checked-in JSON Schema。
4. React Client 不能直接写 Store。
5. SQLAlchemy Entity 不能越过 Store Adapter。
6. SQLite 是默认 Store Profile，不是唯一允许的 Durable Store。
7. JSON-RPC-style stdio 是第一种隔离 Transport，不是永久唯一 Transport。
8. OpenAI Model Adapter 是参考实现，不是 Shadow 的模型依赖。
9. Codex、DeepSeek 或其他 Runtime 只能通过 Agent Runtime Port 接入。
10. 任何实现选择的替换都不得改变用户 Canonical Asset 的身份和语义。

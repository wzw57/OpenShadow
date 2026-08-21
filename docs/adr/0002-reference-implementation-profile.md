# ADR-0002: 第一套参考实现 Profile

- Status: Accepted
- Constrained by: [ADR-0003](0003-tiny-core-and-typed-profiles.md)、[ADR-0004](0004-agent-skills-compatibility.md)
- Date: 2026-08-21
- Owners: OpenShadow maintainers

## Context

完整技术架构已经冻结，但开始 Phase 0–1 开发仍需要选择 Core 语言、Server、Web Client、Contract 事实源、Adapter Transport、Primary Store 和参考 Execution Adapter。

这些选择需要支持快速开发和 AI 生态接入，同时不能成为长期 Domain 依赖。

## Decision

第一套官方参考实现采用：

- Python 作为 Core 实现语言；
- FastAPI 作为 Server Framework；
- React + TypeScript + Vite 作为 Web Client；
- REST / JSON 与 OpenAPI 3.1 作为 Command / Query API；
- SSE 作为 Chat / Run 单向流式协议；
- WebSocket 仅为未来双向音频和实时 Endpoint 保留；
- checked-in JSON Schema 与 OpenAPI 作为跨语言 Contract 事实源；
- Python Family Port / Protocol 作为可信进程内 Adapter 接口；
- JSON-RPC-style Message Envelope over stdio 作为第一种隔离 Adapter Transport；
- SQLite 文件数据库与 WAL 作为默认 Canonical Repository 实现；
- SQLAlchemy 作为关系持久化实现；
- Alembic 作为参考物理 Schema Migration 工具；
- PostgreSQL 作为第二官方 Store Profile；
- Deterministic Test Adapter、OpenAI Model Adapter 和 Process Runtime Adapter 作为首批参考执行实现。

具体依赖版本由每次 Release 锁定，不在长期 ADR 中冻结。

## Rationale

- Python 有利于接入快速演进的 AI、Memory 和数据生态；
- FastAPI 能提供类型化 API、OpenAPI、SSE 和 WebSocket 外层能力；
- React + TypeScript + Vite 提供独立、多端可演进的 Web Client；
- 独立 JSON Schema 防止 Python 或 TypeScript 成为 Adapter 生态限制；
- stdio Transport 便于隔离多语言 Runtime，且不要求首版运行网络服务；
- SQLite 降低个人本地部署成本；
- PostgreSQL Profile 验证 Durable Store Contract 不依赖 SQLite；
- 三种参考 Adapter 分别验证确定性测试、`shadow.model-worker` 和 `shadow.agent-runtime`；
- Adapter 只实现实际声明的 Capability；
- Agent Skills Bundle fixture 验证标准 Skill 可移植性。

## Alternatives considered

### TypeScript Core

优点是前后端共享语言，并可能直接使用部分 Runtime SDK。未采用，因为 Shadow 更需要广泛 AI 与数据生态；TypeScript Runtime 仍可通过进程 Adapter 接入。

### Go Core

优点是单二进制和资源效率。未采用，因为首期集成成本更高，且当前没有性能证据要求使用 Go。

### Pydantic Model 作为唯一 Contract

拒绝。会把跨语言 Adapter 绑定到 Python 实现细节。

### WebSocket 承载所有流式交互

拒绝。普通 Chat / Run 主要是 Server-to-Client 流，SSE 更简单；双向实时音频再使用 WebSocket。

### PostgreSQL 作为唯一默认 Store

拒绝。个人本地运行需要低运维默认值，但 PostgreSQL 保留为官方 Profile。

### Core 直接依赖具体 Runtime SDK

拒绝。Codex、DeepSeek 或未来 Runtime 必须留在 Agent Runtime Adapter 内。

## Consequences

正面结果：

- 可以直接搭建 Phase 0–1 项目；
- 本地安装简单；
- API 与 Adapter Contract 可生成跨语言 Client；
- Runtime、模型和数据库继续可替换；
- 测试 Adapter 可以稳定验证失败和恢复语义。

代价：

- 需要维护 Python Model 与 checked-in Schema 的一致性；
- Python Server 与 TypeScript Web 需要生成或校验 Client 类型；
- stdio Transport 需要处理进程生命周期和背压；
- SQLite 与 PostgreSQL 的共同 Canonical Repository Capability 需要共享 Contract Test；
- ORM Entity、API DTO 和 Domain Object 之间需要显式映射。

## Revisit triggers

- Python 生态无法满足 Core 的可靠性或分发要求；
- stdio 无法满足已验证的吞吐、隔离或远程部署需求；
- SQLite 无法满足个人默认部署的并发和恢复要求；
- OpenAPI / JSON Schema 无法表达主要 Adapter Contract；
- Web Client 需要原生平台能力且包装方案不能满足；
- 参考 Model 或 Runtime Adapter 缺乏稳定集成面。

更换参考实现不得改变 Canonical ID、Proposal / Commit、Profile portability 或 Stable ID。新增 target kind、Profile 或 Adapter Capability 不得反向增加 Kernel 依赖。

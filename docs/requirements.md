# OpenShadow Requirements & System Design Specification

**Version:** v0.3  
**Target:** Shadow v0.1 MVP  
**Status:** Implementation Baseline  
**Positioning:** Personal AI Continuity & Control Layer

> **Shadow owns the continuity.**  
> Runtime owns reasoning and execution — never durable user state.

## 1. Product definition

OpenShadow 是一个 **Local-first、Runtime-neutral** 的个人 AI 连续性与控制层，使用户拥有的 **Memory、Task、Capability、Policy 与 History / World State** 能跨模型、跨 Agent、跨设备、跨时间持续存在。

Shadow 不以“成为最聪明的 Agent”为目标，而是解决个人 AI 资产被具体 Agent / Session / Framework 锁定的问题。

### 1.1 Problems to solve

- **Personal State 被具体 Agent 锁定**：Memory、Task、Skill、Session、Policy 被不同产品分散持有。
- **Runtime 难以替换**：更换 Agent 通常意味着重新迁移上下文、任务、工具与配置。
- **多 Agent 面对的不是同一个人**：不同 Agent 维护不同版本的用户事实、偏好与项目状态。
- **长期记忆容易退化为 RAG**：大量语义相似但决策无关的历史被塞入 Context。
- **权限与副作用缺乏统一治理**：不同 Agent 分别持有 API Key、工具和动作权限。

## 2. Product boundary

判断一个功能是否属于 Shadow 的唯一标准：

> **如果一个功能必须跨 Runtime、跨模型、跨 Session、跨设备或跨年份保持一致，它应属于 Shadow；否则优先交给现有 Runtime / Provider / Engine。**

| Shadow 必须持有 | 优先复用 / 外包 |
| --- | --- |
| Identity / Policy | Agent Loop / Planning |
| Canonical Task / Semantic Checkpoint | Browser Agent |
| Raw Evidence / Canonical Memory Contract | Embedding / Vector DB / Graph Engine |
| Memory Policy / Memory Broker | Mem0 / LangMem / Graphiti |
| Event / World State | Home Assistant 设备驱动 |
| Capability Registry / Gateway / Ledger | Email / Calendar / Browser / Server Provider |
| Runtime SRI / Router / Upgrade | Hermes / DSH / Claude / Codex |
| Context Compiler | AstrBot / Hermes Gateway / IM |
| Scheduler / Pulse | STT / TTS / LLM Serving |

## 3. Core durable objects

| Object | Definition | Ownership reason |
| --- | --- | --- |
| Identity | 用户及长期身份 / 隐私基线 | 所有 Runtime 的根身份 |
| Event | 已发生事实，append-only | 支撑审计、重建、长期证据 |
| World State | 当前世界状态投影 | 让 Agent 面对“现在” |
| Task | 长期目标、进度、结果 | 不随 Runtime Session 消失 |
| Memory | 对历史形成的可追溯认知 | 属于用户，而非某个 Agent |
| Capability | 用户拥有的标准化可执行能力 | Runtime 可换，但“身体”不能丢 |
| Policy | 权限、风险、隐私、预算规则 | 跨 Runtime 统一治理 |
| Artifact | 文件、日志、报告、工具结果 | 支撑跨 Runtime 接力 |
| Runtime Binding | 当前执行引擎与临时 Session 引用 | 只绑定执行，不拥有持久状态 |

## 4. Event & World State requirements

### 4.1 Event Store

- 使用 append-only Event 表达系统事实。
- 事件至少支持：`user.message`、`email.received`、`calendar.updated`、`server.alert`、`device.state_changed`、`task.*`、`capability.*`、`runtime.*`、`memory.*`。
- 最小字段：`event_id`、`timestamp`、`source`、`actor`、`type`、`payload`、`artifact_refs`、`privacy_level`、`schema_version`。
- 修正通过新事件或显式 `supersede / correction` 表达，不允许无痕覆盖。

### 4.2 World State

World State 是 Event 的当前投影，例如当前模式、活跃任务、今日日历、Home Presence、Server Health、Active Projects。

> Event = what happened.  
> World State = what is true now.

Runtime 默认读取紧凑 World State，而不是重新扫描全部历史。

## 5. Task & Semantic Checkpoint

Task 是 Shadow 的一等公民。Runtime 只执行 Task，不能拥有 Task。

### 5.1 TaskEnvelope minimum fields

- Identity: `task_id`, `user_id`
- Goal: `goal`, `intent`, `priority`, `deadline`
- State: `status`, `current_stage`, `completed_steps`, `remaining_work`
- Knowledge: `known_facts`, `decisions`, `memory_refs`
- Artifacts: `artifact_refs`, `tool_results`
- Control: `allowed_capabilities`, `permission_profile`, `budget`
- Runtime: `runtime_binding`, `runtime_session_ref`
- Recovery: `checkpoint_ref`, `last_durable_event`

### 5.2 Semantic Checkpoint

Shadow 不迁移模型隐式思维链或 Runtime 私有内部状态，只迁移可验证的任务语义状态：

- Goal / Current Stage
- Completed Work / Known Facts
- Decisions / Evidence
- Tool Results / Artifacts
- Open Questions / Remaining Work
- Next Objective

“无损切换”定义为：**Task 语义状态、证据、Artifact 与副作用状态不丢**；不承诺 token-level / hidden reasoning state 无损。

## 6. Memory Substrate

Shadow Memory 不是“长期 RAG”。Memory 的目标是改善当前任务决策，而不是最大化召回历史。

### 6.1 Three layers

| Layer | Content | Property |
| --- | --- | --- |
| Raw Evidence | 对话、邮件、事件、任务轨迹、文件、传感历史 | 事实证据；尽量长期保存 |
| Canonical Memory | Fact / Preference / Relationship / Episode / Decision / Procedure / Project State | 可修正、可追溯、带时间有效性 |
| Derived Intelligence | Embedding / Vector Index / BM25 / Graph / Summary / Reranker features | 可重建、可替换 |

### 6.2 Write path

`Event → Raw Evidence → Memory Candidate → Memory Policy → Ignore / Buffer / Create / Merge / Supersede → Canonical Memory`

V0.1 使用：规则 + LLM 分类 + heuristic score。主要因素：

- future usefulness
- decision impact
- explicitness
- novelty
- stability
- entity importance
- confidence
- redundancy

### 6.3 Recall path

> **Retrieval is a decision, not a database query.**

先根据当前 Task / Step 生成 `MemoryNeed`，再由 Memory Broker 多路检索。优先级：

1. Direct structured lookup
2. Temporal / validity query
3. Entity / relationship lookup
4. Lexical / BM25
5. Vector semantic search

候选结果按 Task relevance、Entity match、Temporal validity、Confidence、Importance、Past usefulness、Redundancy、Provenance quality 重排，输出紧凑 `MemoryBundle`。

### 6.4 Task Working Memory

长任务启动时构造 Task Working Memory；Runtime 主要在 Working Set 内工作，仅在出现新的 MemoryNeed 时访问长期 Memory，避免每一步重复 RAG。

### 6.5 Memory feedback

记录：`retrieved / injected / referenced / decision_changed / user_corrected / task_outcome`，用于未来 Personal Memory Router 与科研实验。

## 7. Runtime SRI

SRI（Shadow Runtime Interface）是 Shadow 面向 Agent Runtime 的稳定 Contract。

### 7.1 Minimum interface

```text
execute(task_context)
resume(semantic_checkpoint)
pause(task_id)
cancel(task_id)
checkpoint(task_id)
status(task_id)
capabilities()
health()
```

### 7.2 Runtime roles

| Type | Candidate | Role |
| --- | --- | --- |
| General Runtime | Hermes | 稳定主执行器 |
| Candidate Runtime | DeepSeek Harness / DSH | 验证模块化与切换机制 |
| Specialist | Claude / Codex | Coding / Research 等专业任务 |
| Future Runtime | Any | 通过 Adapter 接入 |

### 7.3 Upgrade lifecycle

`Install Candidate → Compatibility Test → Historical Dry-run Replay → Canary → Promote → Drain Old Runtime → Retire / Rollback`

运行中任务优先 Drain；长任务可通过 Semantic Checkpoint 迁移；Runtime crash 使用 last durable checkpoint 在 fallback runtime 上恢复。

## 8. Capability & Governance

Capability 表示用户拥有的标准化“身体能力”，例如：

- `home.light.set`
- `calendar.create`
- `server.logs`
- `server.restart`
- `nas.search`

Shadow 只定义 Contract、Registry、Gateway、Policy，不重写每个动作实现。

### 8.1 Capability Registry

至少记录：`capability_id`、`version`、`schema`、`provider`、`risk_level`、`permission_requirement`、`status`。

Runtime 不直接持有长期 secrets。

### 8.2 Capability Gateway

统一执行链：

`Identity → Schema Validation → Policy → Approval → Idempotency → Provider → Result Sanitization → Audit`

### 8.3 Execution Ledger / Idempotency

每个副作用 Action 必须包含 `action_id / idempotency_key`。Runtime 在动作成功后崩溃时，新 Runtime 重复请求相同动作应返回已执行结果，而不是再次执行。

> **LLM proposes; Shadow decides; Capability executes.**

## 9. Context Compiler

Context Compiler 将 Shadow 的 Canonical Context 编译成不同 Runtime 的输入格式。

Canonical inputs:

- Task / Checkpoint
- Task Working Memory
- Relevant Personal Memory / MemoryBundle
- World State
- Policy / Capability Set
- Provenance

替换 Runtime 时，不迁移其内部 Session，而是从同一 Canonical Context 重新 hydrate。

## 10. Scheduler & Pulse

### 10.1 Scheduler

Shadow 持有长期 authoritative schedule，支持：

- one-shot
- recurring
- conditional

Runtime 自带 cron 可以存在，但不能成为长期唯一真相。

### 10.2 Pulse

Pulse 是低成本 Personal Attention Layer。

Priority path:

`L0 deterministic rules → L1 tiny local model → L2 General Runtime`

Outputs:

`Ignore / Update State / Remember Candidate / Notify / Create Task / Escalate`

目标是把大量低价值事件压缩成少量真正需要 Agent 的事件，而不是高频 heartbeat 大模型。

## 11. Interaction

V0.1 只要求：

- CLI
- Webhook
- Minimal Web Console

未来可接 AstrBot、Hermes Gateway、Telegram、Voice Satellite、Mobile App。

**验收原则：删除 Chat UI 后，Shadow 仍应能监听事件、更新状态、创建任务、调用 Runtime、执行 Capability、记录结果并通知用户。**

## 12. Data persistence baseline

V0.1 使用 PostgreSQL 作为统一 Source of Truth，pgvector 只作为派生索引。

| Logical store | Content |
| --- | --- |
| `users / identities` | 身份与基础设置 |
| `events` | append-only event log |
| `world_state` | 当前投影 |
| `tasks / task_checkpoints` | Task 与 Semantic Checkpoint |
| `artifacts` | 文件、日志、报告、工具结果引用 |
| `memories / memory_links` | Canonical Memory、时间有效性、provenance |
| `memory_feedback` | 召回、使用、修正反馈 |
| `capabilities / providers` | Capability Contract 与 Provider 注册 |
| `execution_ledger` | 副作用调用、idempotency、result、audit |
| `runtimes / runtime_bindings` | Runtime / Adapter / health / task binding |
| `policies / approvals` | 统一规则与审批记录 |

大型 Artifact / Raw Evidence 可存本地文件系统或 NAS，并在数据库保存 ref / hash / metadata。

## 13. Non-functional requirements

| Dimension | Requirement |
| --- | --- |
| Reliability | Shadow Core 重启不丢 durable Task / Event / Ledger；Runtime crash 可从 checkpoint 恢复 |
| Portability | 核心个人数据不得依赖单一 Runtime 私有结构 |
| Local-first | Personal Data 默认本地；Cloud Runtime 受 Policy 控制 |
| Auditability | 重要动作可追溯：谁提出、基于什么 Context、谁批准、执行结果 |
| Upgradeability | Runtime / Memory Engine / Provider 支持 Install→Validate→Canary→Promote→Rollback |
| Explainability | Memory 能解释“为什么记住”和“为什么这次被调取” |
| Performance | Fast deterministic path 不强制经过 Agent |
| Extensibility | 新 Runtime / Provider 原则上只新增 Adapter，不修改 Core Contract |

## 14. Security & privacy

- Cloud Runtime 默认最小权限，不直接接触长期 secrets。
- Secret 通过 Gateway / Proxy 使用。
- Capability 按风险分级：read-only / reversible / external commitment / destructive / physical safety。
- 高风险动作必须支持 approval gate。
- Raw Evidence、Memory、Artifact 按 `privacy_level` 标记。
- Context Compiler 根据 Runtime trust profile 裁剪数据。
- 支持敏感数据禁出网、Local Model 优先、Mode / Policy Bundle。

## 15. Shadow v0.1 MVP scope

### 15.1 Must build

- Event Store + Minimal World State Projection
- Canonical Task + Semantic Checkpoint
- SRI + Hermes Adapter + DSH Adapter
- Raw Evidence + Canonical Memory Contract
- Simple Memory Policy + Memory Broker + MemoryBundle
- Context Compiler
- Capability Registry + Gateway + Execution Ledger + Idempotency
- Basic Policy / Approval
- Minimal Scheduler + Pulse
- PostgreSQL + pgvector
- CLI / Webhook / Minimal Admin Console
- Docker Compose single-node deployment

### 15.2 Explicitly out of scope

- 自研 Agent Loop / Browser Agent / Coding Agent
- 完整 RAG Framework / Vector DB / Graph Database
- 自研 Home Automation / IM Platform / Voice Stack
- 复杂 Multi-Agent Framework / Plugin Marketplace
- Multi-user SaaS / Enterprise tenancy
- Kubernetes 生产集群 / 分布式微服务

## 16. Acceptance criteria

| ID | Scenario | Pass condition |
| --- | --- | --- |
| AC-01 | Runtime Continuity | Hermes 中断后 DSH 从 Semantic Checkpoint 恢复；Task / Artifact / Fact 不丢 |
| AC-02 | Cross-Runtime Memory | Runtime A 形成的 Canonical Memory 能被 Runtime B 正确调用 |
| AC-03 | Autonomous Event Handling | 无 Prompt 情况下事件可触发 Pulse → Task → Runtime → Result |
| AC-04 | Exactly-once Side Effect | Runtime crash / retry 不导致重复外部动作 |
| AC-05 | Runtime Upgrade | Candidate 经 replay/canary 切换，Memory / Task / Policy / Capability 无迁移 |
| AC-06 | Memory Utility | Task-aware Memory 相对 top-k baseline 降低无关 Context，并改善或保持成功率 |

## 17. Recommended v0.1 stack

| Layer | Choice |
| --- | --- |
| Core Backend | Python + FastAPI |
| Database | PostgreSQL |
| Vector | pgvector |
| Event Bus | In-process + PostgreSQL durable event table |
| General Runtime | Hermes + DSH |
| Memory Engine | Contract/Broker first; optional Mem0 / LangMem; Graphiti later |
| Capability | Home Assistant / PC Agent / Server Agent / Google APIs |
| LLM Serving | OpenAI-compatible API / Ollama / vLLM |
| Deployment | Docker Compose |
| Observability | Structured logs first; Prometheus/Grafana later |

## 18. Implementation guardrails

- **P1** Shadow owns the continuity.
- **P2** No runtime owns durable user state.
- **P3** Raw evidence is truth; canonical memory is interpretation; indexes are disposable.
- **P4** Retrieval is a decision, not a database query.
- **P5** Task belongs to Shadow; Runtime only executes it.
- **P6** LLM proposes; Shadow decides; Capability executes.
- **P7** Fast deterministic actions do not require an Agent.
- **P8** Logical modularity ≠ microservices.
- **P9** Every replaceable component should minimize Upgrade Absorption Cost.
- **P10** If an existing Agent / Engine can do it well and continuity does not require ownership, do not rebuild it in Shadow.

> **Success criterion:** 如果多年后 Runtime、LLM、Memory Engine 与设备生态都换了一轮，而用户的 Task、Memory、Capabilities、Policy 与 History 仍然连续存在，并能被新一代 AI 立即继承，Shadow 就成功了。

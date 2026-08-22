# OpenShadow 完整技术架构

- 状态：Stage 4 Accepted — D1–D8 已冻结并合并，进入 Phase 0–1 实现
- 适用范围：完整 Shadow 产品，不等同于某一实现 Phase
- 核心方法：冻结 Tiny Kernel、typed Profile 与 Extension Contract，再按阶段实现
- 非目标：不冻结 Runtime、模型、Memory 项目、数据库、消息队列、云平台或 Target Kind 全集
- 参考实现：[Stage 4 Implementation Profile](implementation-profile.md)
- 字段级 Contract：[Stage 4 Contract Baseline](contract-baseline.md)
- 决策记录：[ADR-0003](adr/0003-tiny-core-and-typed-profiles.md)、[ADR-0004](adr/0004-agent-skills-compatibility.md)

当前可运行参考实现已经包含 `shadow.agent-runtime` 的 Hermes Adapter：
`FastAPI → ConversationService → Hermes Adapter → Hermes API Server →
DeepSeek (deepseek-v4-flash)`。Shadow 默认仍使用 Deterministic Adapter；Hermes
工具、Session 私有状态和模型 Provider 均不进入 Shadow Canonical Store。

## 1. 架构目标

Shadow 必须允许 Runtime、模型、Memory Intelligence、Router、Runner、数据库、语音和设备能力持续升级，同时保持用户身份、资产、工作和治理记录连续。

长期稳定的是控制边界，不是 Shadow v1 对所有 AI 概念的理解。

完整架构遵循：

1. 所有承载工作的输入经过 Shadow Admission；
2. 非工作控制面请求不创建伪 Run；
3. 所有执行受 Shadow Binding 和 Capability 治理，但不都经过 Agent Runtime；
4. External Intelligence 只能 Proposal，Shadow Authority 才能 Commit；
5. Canonical Envelope 统一治理，typed Profile 保留领域语义；
6. Profile 可以升级，但必须提供 Schema 与语义 Migration；
7. Adapter 是正式边界，但公共 Descriptor 保持最小；
8. 新 namespaced target kind 不修改 Core 主流程；
9. 数据库、队列、工作流、搜索、语音和设备协议外置；
10. 逻辑边界不等于微服务；
11. 每个实现 Phase 是同一目标架构的真子集。

## 2. 架构总览

~~~mermaid
flowchart TB
    subgraph INTERACTION["Interaction Plane"]
        WEB["Web / Desktop"]
        MOBILE["Future Mobile"]
        VOICE["Voice / Audio Endpoint"]
        API["CLI / External API"]
        TRIGGER["Event / Schedule / Condition"]
    end

    subgraph ACCESS["Access & Admission"]
        GATEWAY["Gateway"]
        SUBJECT["Owner / Space / Endpoint"]
        ADMISSION["Work Admission / Idempotency"]
        DISCLOSURE["Data Boundary"]
    end

    subgraph KERNEL["Tiny Kernel"]
        ID["Identity / Ownership"]
        RECORD["Canonical Record / Lifecycle"]
        AUTH["Proposal / Validate / Commit"]
        RUN["Request / Run / Attempt"]
        CONT["Minimal Continuity"]
        BIND["Binding / Capability"]
        PORTABLE["Migration / Export / Erasure Intent"]
    end

    subgraph PROFILE["Official Typed Profiles"]
        CONV["Conversation"]
        MEMORY["Memory"]
        STATE["State"]
        TASK["Durable Task"]
        ACTION["Action"]
        ASSET["Skill / Capability / Integration"]
    end

    subgraph EXECUTION["Replaceable Intelligence & Execution"]
        AGENT["Agent Runtime"]
        MODEL["Model Worker"]
        PROGRAM["Runner"]
        WORKFLOW["Workflow Engine"]
        ROUTER["Router"]
        MEMINT["Memory Intelligence"]
        RESOLVER["State Resolver"]
        PROVIDER["Capability Provider"]
    end

    subgraph ADAPTER["Family Ports & Adapter Registry"]
        DESCRIPTOR["Minimal AdapterDescriptor"]
        RUNTIMEPORT["Runtime / Model / Runner Ports"]
        SOURCEPORT["Source / Retrieval Ports"]
        STOREPORT["Store Capability Family"]
        INTERFACEPORT["Interaction / Voice Ports"]
        INFRAPORT["Secret / Scheduler / Telemetry"]
    end

    subgraph INFRA["Replaceable Infrastructure & Sources"]
        STORE[("Database")]
        BLOB[("Blob / Artifact")]
        INDEX[("Index / Cache")]
        SECRET[("Secret Store")]
        OUTBOX["Optional Durable Outbox"]
        EXTERNAL["Knowledge / Services / Devices"]
    end

    INTERACTION --> ACCESS --> KERNEL
    KERNEL --> PROFILE
    KERNEL --> ADAPTER
    PROFILE --> EXECUTION
    ADAPTER --> EXECUTION
    ADAPTER --> INFRA
    EXECUTION --> INFRA
~~~

Plane 表示责任，不表示进程。参考部署可以把 Access、Kernel、Profile Validator、Canonical Repository 协调和可信 Adapter Host 放在一个进程；高风险或不可信执行再隔离。

## 3. Tiny Kernel

### 3.1 Identity & Ownership

负责：

- Stable ID；
- Principal / Owner / Space references；
- created_by；
- owner transfer / lifecycle intent；
- cross-record stable references。

第一版只有当前 User、默认 Personal Space 和隐式 Home Space，不实现成员、角色、邀请或共享 ACL。

### 3.2 Canonical Record & Lifecycle

共同治理 Envelope：

~~~text
record_id
record_type
schema_ref
owner_ref / space_id / created_by
data_classification
provenance
version
retention_policy_ref
record_state
created_at / committed_at
typed_payload
~~~

Kernel 不解释 typed payload，但要求 Schema 可定位、Version 可比较、Lifecycle 可审计、Erasure 可追踪。`expected_version` 属于 Mutation Input，不属于已提交 Envelope。

### 3.3 Proposal / Validate / Commit Authority

Commit Pipeline：

~~~mermaid
flowchart LR
    INPUT["Command / Typed Proposal"]
    ID["Identity / ExpectedVersion"]
    SCHEMA["Schema Validation"]
    POLICY["Authority / Deterministic Policy"]
    PROFILE["Profile Validator"]
    COMMIT["Canonical Commit"]
    VERSION["New Version"]
    EVENT["Optional Notification Event"]

    INPUT --> ID --> SCHEMA --> POLICY --> PROFILE --> COMMIT --> VERSION
    COMMIT --> EVENT
~~~

Profile Validator 不获得写权限。External Component 和 Adapter 不得直接写 Canonical Repository。

### 3.4 Work Admission

Admission 只为 work-bearing input 创建 Request / Run。以下输入属于工作：

- user command / conversation turn；
- voice intent；
- schedule / event / condition trigger；
- Semantic Pulse proposal；
- external API command；
- 恢复后需要重新执行的工作命令。

以下不是新工作：

- health / readiness；
- static asset；
- read-only control-plane query；
- existing Run event subscription；
- internal projection rebuild；
- recovery / reconciliation 内部步骤。

非工作路径仍执行身份、权限、速率和审计。

### 3.5 Run / Attempt & Minimal Continuity

一个 Accepted Request 创建且只创建一个 Root Run。Retry 追加 Attempt。

Kernel 管理：

- Run / Attempt lifecycle；
- Binding references；
- result / failure / usage summary；
- cancellation truth；
- optional Durable Task reference；
- checkpoint / artifact / trigger references；
- completion commit。

Runtime 内部 Session、Planner、Subtask、Subagent 和 Tool Loop 不进入 Kernel。

### 3.6 Binding & Capability Enforcement

ExecutionBinding 最小字段：

~~~text
binding_id
target_kind
adapter_ref
contract_version
required_capabilities
resolved_capabilities
implementation_version
capability_envelope_ref
created_at
~~~

CapabilityEnvelope 最小字段：

~~~text
allowed_capabilities
data_scope
resource_scope
budget
side_effect_level
approval_state
valid_until
revocation_state
policy_version
~~~

Core 只执行确定性 Policy primitives；复杂 Policy Engine 可以提出 evaluation，不能跳过最终检查。

### 3.7 Portability & Erasure Intent

Kernel 负责：

- Profile / Schema version registry；
- Migration Intent / result reference；
- standard export manifest；
- integrity expectation；
- Erasure Intent / component status；
- minimal Tombstone。

物理迁移、打包、备份和擦除由 Store / Adapter Capability 执行。

## 4. Typed Profile Architecture

### 4.1 Profile Descriptor

~~~text
profile_id
record_type
schema_versions
validator_ref
proposal_schemas
lifecycle_contract
migration_refs
portable_export_rules
compatibility
~~~

Profile 是可版本化的 Shadow Contract。它可以由官方包或受信任 Extension 提供，但必须通过 Contract Test，不能扩大 Authority。

### 4.2 官方 Profile

| Profile | 长期承诺 | 快速演进部分 |
|---|---|---|
| Conversation | Message identity、order refs、retention | UI rendering、prompt layout |
| Memory | identity、versions、evidence、correction、erase | extraction、retrieval、embedding、graph |
| State | state key、evidence、temporal validity、freshness | sources、fusion、prediction、ontology |
| Durable Task | stable task identity、Run refs、completion | planning、decomposition、workflow |
| Action | approval、pending-before-call、unknown / reconciliation | parameter generation、provider protocol |
| SkillAsset | standard bundle identity、revision、trust、permission | discovery、loading、execution、provider upload |
| Integration | stable connection identity、binding、secret ref | family config、protocol、health details |

Profile 大版本变化必须提供语义 Migration。仅能通过新 Schema 验证，不代表旧记录已经正确迁移。

## 5. Execution Plane

### 5.1 Extensible Target Kind

`target_kind` 是 namespaced string。首批 well-known kinds：

| target_kind | 典型实现 |
|---|---|
| `shadow.agent-runtime` | Codex 类 SDK、Agent Harness |
| `shadow.model-worker` | 单次或受限模型调用 |
| `shadow.deterministic-runner` | Function / Script / Program Runner |
| `shadow.workflow-target` | 外部 Workflow Engine |
| `shadow.capability-provider` | API、账户、设备 Provider |

它们不是封闭枚举。扩展 Target 声明 Descriptor、Capability、Request / Event / Result Schema 和兼容性即可接入。

Core 不按 target kind 名称做业务路由，只根据 Requirements、Capability、Policy、健康和显式 Binding 校验。

### 5.2 Execution Requirements

可包含：

- capabilities；
- data classes；
- tool / source requirements；
- latency / deadline；
- budget；
- reliability；
- side-effect level；
- local / remote；
- streaming / checkpoint needs。

高级任务分类和 Target 评分由 Router 产生 BindingProposal。早期实现使用用户显式选择和静态规则。

### 5.3 Runtime Base Contract

基础 Runtime Port：

~~~text
describe() -> RuntimeDescriptor
execute(ExecutionRequest) -> ExecutionReference | terminal result
events(ExecutionReference, cursor?) -> event stream
~~~

可选 Capability：

- cancel；
- progress；
- usage；
- checkpoint；
- native_resume；
- semantic_handoff；
- artifact；
- reconciliation。

没有声明的能力不得被调用，也不得用不可靠模拟返回成功。

### 5.4 Port Output Families

Execution / Intelligence Family 使用：

- Result；
- Proposal；
- Observation；
- Progress；
- Failure；
- Checkpoint Reference；
- Usage。

这只是该 Family 的输出族，不是所有 Port 的唯一响应模型。

Infrastructure Family 使用自己的 typed payload，例如：

- StoreCommitResult；
- MigrationResult；
- SecretResolveResult；
- ExportResult；
- HealthResult；
- InteractionDeliveryResult。

所有 Family 只共享：

~~~text
message_id
message_type
schema_ref
contract_version
correlation_id / causation_id
timestamp
status
typed_payload | structured_error
~~~

## 6. Adapter Control

### 6.1 Minimal AdapterDescriptor

~~~text
descriptor_id / descriptor_version
adapter_family
implementation_ref / implementation_version
supported_contracts
supported_target_kinds
capabilities
config_schema_ref
descriptor_digest
~~~

Descriptor 是不可变实现声明，不包含安装 ID、配置值、Secret、授权或实时健康。`AdapterRegistration` 记录一个安装实例及其 config / secret / host / trust refs；`HealthObservation` 带 observed_at 与 valid_until，过期后按 unknown 处理。以下通过 Family Capability 提供：

- permissions；
- secrets；
- data boundary；
- checkpoint / resume；
- migration；
- export / backup；
- outbox；
- reconciliation；
- transport details。

### 6.2 生命周期

Adapter Registry 记录：

- installed / enabled / disabled；
- compatible / incompatible；
- active bindings；
- source and pinned implementation revision；
- config reference；
- 独立 health observation reference。

升级流程：

~~~text
Discover new version
      ↓
Descriptor / Contract compatibility
      ↓
Profile or data migration when required
      ↓
Contract tests
      ↓
Canary binding
      ↓
Activate / rollback
~~~

### 6.3 Transport

Contract 不冻结 Transport。参考实现支持：

- trusted in-process Python Port；
- isolated UTF-8 NDJSON Envelope over stdio；stdout 只承载协议，stderr 只承载清洗后的日志。

未来可以增加本机 socket、container RPC 或 remote transport，但不得改变 Domain Contract。

## 7. Skill Compatibility

Shadow 原生支持 [Agent Skills Specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)。

Canonical SkillAsset：

~~~text
skill_id
owner_ref / space_id
format: agent-skills
source_ref
pinned_revision
bundle_digest
trust
permission_policy
classification
install_state
runtime_projection_refs
provider_external_refs
~~~

标准 Bundle 保留：

~~~text
SKILL.md
scripts/       optional
references/    optional
assets/        optional
~~~

规则：

1. Shadow 不向 Bundle 注入私有元数据；
2. 用户拥有的 Skill 保存 immutable snapshot 或可验证 revision；
3. Runtime Projection 是 Derived State；
4. Provider Skill ID 是 External Reference；
5. `allowed-tools` 是实验性提示，不能授予 Shadow Capability；
6. 默认优先标准位置，其他 Runtime 路径通过 Adapter 映射；
7. Provider API 可上传目录或 zip、保存 version，但 Provider 对象不成为 Canonical Skill。

## 8. Store Capability Architecture

### 8.1 Capability Split

| Capability | Contract |
|---|---|
| Canonical Repository | get、query、commit with expected version、transaction capability |
| Migration | plan / apply / verify profile and physical migrations |
| Portable Export / Import | standard manifest and canonical payloads |
| Backup / Restore | implementation-specific encrypted device backup |
| Durable Outbox | append / deliver / reconcile side-effect intents |
| Integrity | checksums、referential validation、repair report |

第一阶段只要求 Canonical Repository 与必要 Migration。Store Adapter 不需要为了接入而实现 Backup 或 Outbox。

### 8.2 Canonical、Derived 与 External

- **Canonical State**：跨组件迁移的 Shadow records；
- **Derived State**：index、embedding、graph、cache、runtime projection，可重建；
- **External Source Asset**：原始 Notion、Drive、Email、文件和设备数据，按需访问。

标准导出只承诺 Canonical State、Profile / Schema、Owner / Space、Binding、Integration 和迁移元数据，不依赖 Secret 与 Derived State。

### 8.3 Restricted Mode

Primary Canonical Repository 不可用时：

- read-only / explicit ephemeral interaction can continue；
- Canonical Commit pauses；
- real-world side effects are denied by default；
- preconfigured emergency Action must first persist to a reliable Outbox；
- recovery performs idempotent replay and reconciliation。

## 9. 关键数据流

### 9.1 Chat / Run

~~~mermaid
sequenceDiagram
    participant UI
    participant Admission
    participant Kernel
    participant Target
    participant Profile
    participant Store

    UI->>Admission: work-bearing command
    Admission->>Kernel: Accepted Request
    Kernel->>Store: commit Request + Root Run
    Kernel->>Target: execute with Binding / Envelope
    Target-->>Kernel: events / Result / Proposal
    Kernel->>Profile: validate typed changes
    Kernel->>Store: commit Run and accepted Profile records
    Kernel-->>UI: SSE events / final state
~~~

### 9.2 Memory

~~~mermaid
sequenceDiagram
    participant Source
    participant Intelligence as Memory Intelligence
    participant Kernel
    participant Profile as Memory Profile
    participant Store

    Source->>Intelligence: authorized context
    Intelligence-->>Kernel: MemoryCandidate
    Kernel->>Profile: validate candidate / transition
    Profile-->>Kernel: validation result
    Kernel->>Store: Canonical Commit
~~~

### 9.3 State

~~~mermaid
sequenceDiagram
    participant Source
    participant Resolver
    participant Kernel
    participant Profile as State Profile
    participant Store

    Source-->>Kernel: Observation / StateProposal
    Kernel->>Resolver: optional conflict resolution
    Resolver-->>Kernel: StateProposal
    Kernel->>Profile: validate key / temporal transition
    Kernel->>Store: commit accepted state version
~~~

### 9.4 External Action

~~~mermaid
sequenceDiagram
    participant Intelligence
    participant Kernel
    participant Store
    participant Provider

    Intelligence-->>Kernel: ActionProposal
    Kernel->>Kernel: schema / policy / approval
    Kernel->>Store: persist pending Action
    Kernel->>Provider: execute with idempotency key
    Provider-->>Kernel: result or unknown
    Kernel->>Store: commit outcome
    Kernel->>Provider: reconcile when unknown
~~~

## 10. Reliability and Consistency

### 10.1 Expected Version

单 Record 更新使用 ExpectedVersion。冲突返回结构化 Conflict，不静默 last-write-wins。

### 10.2 Idempotency

以下必须具备 idempotency key：

- Admission replay；
- Attempt start；
- Canonical Commit；
- Provider Action；
- Outbox delivery；
- Migration step；
- Import / Erasure step。

### 10.3 Event / Outbox / Job Boundaries

- Domain Event 是 notification，不是 Event Sourcing；
- Outbox 只保证跨边界 side effect；
- OperationJob 只用于 export、import、migration、backup、erasure；
- 普通内部通知可以同步分发；
- 第一阶段不引入通用消息队列。

### 10.4 Cancellation

cancel requested 不等于 cancelled。只有 Target acknowledgement 才提交 cancelled；无法确认时为 cancellation_unknown。没有 cancel Capability 的 Adapter 必须明确返回 unsupported。

## 11. Security and Data Boundaries

Core 稳定数据等级：

- public；
- personal；
- sensitive；
- restricted。

未知默认 sensitive。外部分类器可以提出提高等级；降低必须由用户或确定性规则确认。

每个 Model / Runtime Binding 声明：

- local / remote；
- accepted data classes；
- Memory / State / external asset access；
- retention / training；
- region / organization；
- allowed capabilities。

Secret 内容保存在 Secret Store，通过 SecretReference 使用。标准导出不包含 Secret；完整设备备份必须单独加密和授权。

## 12. Deployment Evolution

### 12.1 Reference Start

- Python Kernel；
- FastAPI；
- React + TypeScript + Vite；
- OpenAPI 3.1 / JSON Schema；
- SSE；
- SQLite WAL / SQLAlchemy / Alembic；
- trusted in-process Port；
- isolated stdio Adapter；
- Local Web。

### 12.2 Split Triggers

只有出现证据时拆分：

- untrusted code isolation；
- independent resource scheduling；
- measured throughput；
- failure-domain separation；
- remote device / multi-endpoint；
- team ownership boundary。

拆分不能改变 Stable ID、Profile Schema、Proposal / Commit 或 Binding semantics。

## 13. Contract Tests

每个 Profile 必须测试：

- valid / invalid payload；
- lifecycle transitions；
- expected-version conflict；
- export / import round trip；
- supported migration；
- erase / tombstone；
- unknown fields / forward compatibility。

每个 Adapter 必须测试：

- descriptor honesty；
- contract-version negotiation；
- declared capability；
- structured failure；
- timeout / cancellation behavior；
- no direct canonical write；
- restart / reconnect semantics where declared。

每个 Store Capability 必须独立测试，不能用“完整 Store Adapter 已通过”代替 capability-specific verification。

## 14. Stage 4 冻结决定

1. Tiny Kernel + typed Profile；
2. Proposal / Validate / Commit；
3. work-bearing Admission；
4. Run / Attempt 控制事实；
5. minimal Durable Task continuity；
6. namespaced target_kind；
7. capability-first Binding；
8. minimal AdapterDescriptor；
9. family-specific Port Result；
10. Runtime base + optional capabilities；
11. Store Capability split；
12. State Profile 不进入 Kernel 本体；
13. Agent Skills 原生兼容；
14. deterministic Policy minimum；
15. narrow Domain Event / Outbox / OperationJob；
16. modular monolith first；
17. Phase 0–5 phased delivery；
18. reference implementation remains replaceable。

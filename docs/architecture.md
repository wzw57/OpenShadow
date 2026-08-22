# OpenShadow 概要设计

- 状态：Stage 4 Core Diet 修订基线
- 目标：描述 Tiny Kernel、typed Profile 与可替换组件组成的完整 Shadow
- 非目标：不指定某个 Runtime、模型、Memory 项目、数据库、工作流引擎或部署平台

## 1. 系统定义

Shadow 是用户长期使用的完整个人 Agent。Tiny Kernel 不是“所有 Agent 功能的实现中心”，而是一个主权与连续性内核：

> Core 尽可能不理解领域内容，但必须知道对象属于谁、谁可以修改、修改是否合法、版本如何演化、工作如何继续，以及如何迁移和删除。

快速演进的智能、执行、协议和基础设施通过 Extension / Adapter 接入。Memory、State、Task、Action、Skill 等概念由官方 typed Profile 定义，可以独立升级，不成为 Kernel 的永久硬编码类型。

## 2. Core Diet 判定

每项能力必须先分类：

| 分类 | 判断标准 |
|---|---|
| KERNEL | 2030 年 AI 范式改变后仍必须由 Shadow 自己理解 |
| CONTRACT-ONLY | 需要稳定边界，但当前不必实现完整机制 |
| PROFILE / EXTENSION | 需要 Shadow 兼容，但业务语义或实现会快速变化 |
| LATER PHASE / DERIVED | 当前没有必要固化，或可以重建 |

Tiny Kernel 只保留：

~~~text
Tiny Kernel
├─ Identity & Ownership
├─ Canonical Record & Lifecycle
├─ Proposal / Validate / Commit
├─ Work Admission
├─ Run / Attempt & Minimal Continuity
├─ Extension Contract & Binding
├─ Deterministic Enforcement
└─ Portability & Erasure Intent
~~~

不进入 Tiny Kernel：

- Memory 提取、整理和检索；
- State 融合、预测、本体和查询；
- Task 规划、分解和 Workflow；
- Router 算法；
- Skill 内容格式与执行；
- 复杂 Policy 语言；
- 数据库、队列、调度、搜索；
- 语音与设备协议。

## 3. 完整逻辑架构

~~~mermaid
flowchart TB
    subgraph INTERACTION["Interaction"]
        WEB["Web / Desktop"]
        MOBILE["Future Mobile"]
        VOICE["Voice Endpoint"]
        API["CLI / External API"]
        TRIGGER["Event / Schedule / Condition"]
    end

    subgraph ACCESS["Access & Admission"]
        GATEWAY["Gateway"]
        SUBJECT["Owner / Space / Endpoint Context"]
        ADMISSION["Work Admission / Idempotency"]
        DISCLOSURE["Data Boundary"]
    end

    subgraph KERNEL["Tiny Kernel"]
        ID["Identity / Ownership"]
        RECORD["Canonical Record / Lifecycle"]
        AUTH["Proposal / Validate / Commit"]
        WORK["Request / Run / Attempt"]
        CONT["Minimal Task Continuity"]
        BIND["Extension / Binding / Capability"]
        PORTABLE["Export / Migration / Erasure Intent"]
    end

    subgraph PROFILES["Official Typed Profiles"]
        CONV["Conversation"]
        MEMORY["Memory"]
        STATE["State"]
        TASK["Durable Task"]
        ACTION["Action"]
        CAP["Skill / Capability / Integration"]
    end

    subgraph EXECUTION["Replaceable Execution & Intelligence"]
        RUNTIME["Agent Runtime"]
        MODEL["Model Worker"]
        RUNNER["Deterministic Runner"]
        FLOW["Workflow Engine"]
        ROUTER["Router"]
        MEMINT["Memory Intelligence"]
        RESOLVER["State Resolver"]
        PROVIDER["Capability Provider"]
    end

    subgraph PORTS["Family Ports"]
        ADAPTER["Minimal Adapter Registry"]
        STOREPORT["Store Capabilities"]
        SOURCE["Source / Retrieval"]
        INTERFACE["Interaction / Voice"]
        INFRA["Scheduler / Secret / Telemetry"]
    end

    subgraph INFRASTRUCTURE["Replaceable Infrastructure"]
        STORE[("Database")]
        INDEX[("Index / Cache")]
        SECRET[("Secret Store")]
        QUEUE["Optional Outbox / Queue"]
        EXTERNAL["External Sources / Services / Devices"]
    end

    INTERACTION --> ACCESS --> KERNEL
    KERNEL --> PROFILES
    KERNEL --> PORTS
    PROFILES --> EXECUTION
    PORTS --> EXECUTION
    PORTS --> INFRASTRUCTURE
    EXECUTION --> INFRASTRUCTURE
~~~

这些是责任边界，不是微服务边界。早期实现是模块化单体加少量进程外 Adapter。

### 3.1 当前可运行参考部署

当前仓库的可运行参考路径是文本 Conversation：默认使用确定性 Adapter；设置
`SHADOW_RUNTIME_KIND=hermes` 后，Shadow 通过独立 `shadow.agent-runtime`
Adapter 连接本地 Hermes API Server，再由 Hermes 使用已配置的在线模型提供者。
当前联调使用 DeepSeek `deepseek-v4-flash`，不建立 Shadow 到 DeepSeek 的直连，
也不把 Hermes 的内部 Agent Loop、Session 或 Memory 写入 Shadow Store。

```text
HTTP Client / curl
        │ REST
        ▼
FastAPI Shadow Server
        │
        ▼
ConversationService / Application Services
        ├──────────────► Admission + CommitAuthority ───► SQLite Canonical Store
        │                         ▲
        │                         │ Run / Attempt / Message / Event
        ▼                         │
Hermes Agent Runtime Adapter ─────┘
        │ HTTP (OpenAI-compatible)
        ▼
Hermes API Server
        │ Agent Loop / Session / Planner（外部拥有）
        ▼
DeepSeek API（deepseek-v4-flash）
```

首版单用户 Web UI 已实现并由 FastAPI 在 `/ui/` 提供；Hermes 联调 profile 的工具集
全部关闭。细粒度 SSE、Session resume 和经过 Shadow Capability/Action 治理的工具
桥接属于后续切片。

## 4. Canonical Record 与 Profile

统一 Envelope：

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref / space_id / created_by
├─ classification / provenance
├─ version / created_at / committed_at
├─ retention_policy_ref / record_state
└─ typed_payload
~~~

Kernel 负责：

- Stable ID；
- Owner / Space；
- Schema Reference；
- 版本与并发；
- 来源和生命周期；
- 通用删除与 Tombstone；
- Commit 原子语义。

`expected_version` 是 Mutation Input 的并发前置条件，不存入 Canonical Envelope。Profile 生命周期位于 typed payload；通用 `record_state` 仅使用 active、logically_deleted 与 erased。

Profile 负责：

- typed payload Schema；
- 合法状态转换；
- 领域不变量；
- Proposal Schema；
- 语义 Migration；
- 标准导出解释。

采用统一 Envelope 不等于把所有对象变成任意 JSON。Schema Migration 之外，跨 Profile 大版本还必须声明语义迁移与不变量变化。

## 5. Proposal / Validate / Commit

~~~mermaid
flowchart LR
    EXT["External Component"]
    PROP["Typed Proposal"]
    SCHEMA["Schema / ExpectedVersion"]
    POLICY["Authority / Deterministic Policy"]
    PROFILE["Profile Validator"]
    COMMIT["Canonical Commit"]
    RECORD["New Canonical Version"]

    EXT --> PROP --> SCHEMA --> POLICY --> PROFILE --> COMMIT --> RECORD
~~~

统一边界：

- Memory Engine → MemoryCandidate；
- Router → BindingProposal；
- Runtime → Task / CompletionProposal；
- State Resolver → StateProposal；
- Classifier → ClassificationProposal；
- Provider → Action Result / Evidence。

External Component 没有直接写 Canonical Repository 的路径。Profile Validator 也只能验证，不能给自己提交权限。

## 6. Work Admission 与连续性

所有承载工作的输入经过 Admission：

~~~text
Chat / Voice / Command / Event / Schedule / Condition
                         ↓
                     Admission
               ┌─────────┴─────────┐
          rejected             Accepted Request
     minimal record                  ↓
                                  Root Run
                                    ↓
                           Execution Attempt(s)
~~~

不承载新工作的请求不创建 Run：

- health / readiness；
- 静态资源；
- 只读控制面查询；
- 订阅已有 Run 的事件；
- 内部 recovery / reconciliation step。

这些路径仍执行身份、权限、速率和审计。

Run 是 Kernel 控制记录，Runtime Session 不能替代它。Durable Task 使用最小 Continuity Contract 保存稳定 ID、生命周期、Run / Checkpoint / Artifact / Trigger references 和 Completion Commit；规划、分解与 Workflow 外置。

## 7. 可扩展执行平面

Binding 使用 namespaced `target_kind` 与 Capability，而不是永久封闭的 execution mode enum。

首批 well-known kinds：

| target_kind | 典型用途 |
|---|---|
| `shadow.agent-runtime` | 开放式、多步骤、工具循环 |
| `shadow.model-worker` | 分类、提取、总结等受限推理 |
| `shadow.deterministic-runner` | 脚本、函数、固定算法 |
| `shadow.workflow-target` | 外部步骤、等待与补偿 |
| `shadow.capability-provider` | API、账户、设备与现实动作 |

新 Target Kind 通过 Descriptor、Schema 和 Capability 注册，不修改 Core 主流程。

Core 负责：

- Requirements；
- Binding 验证；
- Capability Envelope；
- 预算、数据与副作用检查；
- Attempt / Result / Usage 记录。

Router 负责分类、评分、动态选择和降级建议，只能提交 BindingProposal。

## 8. Runtime 与 Port 边界

Runtime 基础 Port：

~~~text
describe()
execute(execution_request)
events(execution_ref)
~~~

可选 Capability：

- cancel；
- progress；
- usage；
- checkpoint；
- native_resume；
- semantic_handoff；
- reconciliation。

Adapter 不能伪造不支持的能力。没有 cancel acknowledgement 时，Run 只能进入 `cancellation_unknown`；没有 native resume 时，可以使用 Semantic Checkpoint 创建新 Attempt，但不能声称恢复了原 Session。

Execution / Intelligence Ports 可以共享 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 和 Usage 等输出族。Store、Secret、Interaction、Export 等 Infrastructure Ports 使用各自 typed Result，只共享 Message Envelope、Correlation、Version 与结构化错误。

## 9. Memory Profile

Canonical Memory 属于用户，不属于 Memory Intelligence。

~~~mermaid
flowchart LR
    SOURCE["Conversation / Task / External Source"]
    ENGINE["Memory Intelligence"]
    CANDIDATE["MemoryCandidate"]
    AUTH["Shadow Commit Authority"]
    PROFILE["Memory Profile"]
    STORE[("Canonical Repository")]

    SOURCE --> ENGINE --> CANDIDATE --> AUTH --> PROFILE --> STORE
~~~

Memory Profile 定义稳定身份、Scope、Version、Provenance、Evidence、source_dependency、correction、supersede、delete 与 erase。

外部组件负责 Extraction、Consolidation、Deduplication、Retrieval、Reranking、Embedding、Graph 和 Summary。更换这些组件不会删除 Canonical Memory。

## 10. State Profile

State Profile 表达“Shadow 当前接受什么”，不在 Kernel 内建立领域知识图谱。

~~~text
Source / Resolver
       ↓
Observation or StateProposal
       ↓
Schema + Authority + Temporal Validation
       ↓
Accepted State Profile Record
       ↓
fresh / stale / unknown
~~~

Core 只理解通用时间有效性和 Commit。State Profile 定义 state_key、value schema、source、Evidence、observed_at、expires_at 和 freshness。

采集、融合、冲突解决、预测、异常检测、领域本体与查询外置。Accepted State 可恢复和迁移，但可以过期。删除 Integration 后，状态按 Profile 进入 source unavailable、stale 或 unknown。

## 11. Skill 与能力资产

Shadow 的 Skill Profile 原生兼容 Agent Skills Bundle，不自创内容标准。

~~~text
Standard Skill Bundle                 Shadow SkillAsset
├─ SKILL.md                            ├─ stable_id / owner / space
├─ scripts/ optional                   ├─ source / pinned revision / digest
├─ references/ optional       +        ├─ trust / permission / classification
└─ assets/ optional                    ├─ install status
                                       └─ runtime / provider projections
~~~

Shadow 不修改 Bundle 来写入治理元数据。Runtime-specific Prompt、Provider upload 和缓存是 Derived State。Provider Skill ID 是 External Reference。`allowed-tools` 不能代替 Shadow 权限判断。

Skill、Executable、Extension、Integration、MCP Connection 和 Runtime / Model / Runner Profile 可以统一呈现，但由不同 Profile 保留各自语义。

## 12. Adapter 模型

最小 AdapterDescriptor：

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

Descriptor 只描述实现，不代表安装、配置、授权或实时健康。`AdapterRegistration` 保存 adapter_id、Descriptor snapshot、普通 config ref、Secret refs、Host / Trust Binding 与兼容状态；带 TTL 的 `HealthObservation` 单独表达 healthy / degraded / unavailable / unknown。

Family-specific Capability 再声明：

- Data Boundary；
- Permission；
- Secret；
- Checkpoint / Resume；
- Migration / Export；
- Backup / Outbox；
- Reconciliation。

Shadow 不建设万能插件操作系统。Adapter SDK 只提供 Envelope、生命周期、Capability Negotiation、错误模型和 Contract Test。

## 13. Store Capability Family

Shadow 不抽象整个数据库，只定义需要跨实现成立的能力：

| Capability | 是否基础必需 |
|---|---|
| Canonical Repository | 是 |
|必要 Schema Migration | 是 |
| Portable Export / Import | 分阶段 |
| Integrity Verification | 分阶段 |
| Backup / Restore | 可选、实现相关 |
| Durable Outbox | 仅现实副作用场景 |

数据库物理 Schema、事务实现、复制、索引、备份格式和队列不属于 Shadow Domain。

Primary Repository 不可用时：

- 只读和明确标记的临时交互可以继续；
- Canonical Commit 暂停；
- 现实副作用默认禁止；
- 只有预先配置且先进入可靠 Outbox 的紧急 Action 可以继续；
- 恢复后执行幂等提交和 reconciliation。

## 14. Policy 与 Action

Core 不自建复杂 Policy Language。初期只执行确定性约束：

- data classification；
- capability；
- approval；
- budget；
- side-effect level；
- expiry；
- revocation。

复杂规则计算可以由 Policy Engine 提议，Core 做最终检查。

现实 Action 使用专门安全 Contract：

~~~text
ActionProposal
      ↓
Validate / Policy / Approval
      ↓
Persist pending Action
      ↓
Provider execution
      ↓
succeeded | failed | unknown
      ↓
reconciliation when unknown
~~~

## 15. Event、Outbox 与 OperationJob

- Domain Event 是通知 Envelope，不以 Event Sourcing 作为事实基础；
- Outbox 只用于可靠跨边界副作用，不成为通用 Queue abstraction；
- OperationJob 只用于 Export、Import、Migration、Backup 和 Erasure 长操作；
- Workflow、Memory Maintenance、普通 Schedule 不自动进入 OperationJob。

## 16. Owner、Space、删除与可移植性

每个 Canonical Record 具有 Owner 和 Space。近期只实现当前 User、默认 Personal Space 和隐式 Home Space；不实现成员、角色、邀请或共享 ACL。

标准导出包含：

- Canonical Records 与 Profile Schema refs；
- Owner / Space；
- Integration / Binding metadata；
- Migration 与 Integrity metadata；
- 不含 Secret 内容和可重建 Derived State。

完整设备备份可以在独立授权和加密后包含 Secret、Checkpoint 和部分派生状态，但不作为跨实现兼容基础。

用户拥有最终物理删除权。Tombstone 只能保留防止错误复活所需且不含原始敏感内容的最小信息。

## 17. 部署原则

逻辑边界不等于进程边界。

参考演进：

1. 模块化单体 + SQLite + 进程内 Adapter；
2. 高风险 Runtime / Runner 使用 stdio 隔离；
3. PostgreSQL、远程 Store 或独立 Worker 按真实需求接入；
4. 多设备和语音端点通过同一 API / Profile 继续使用；
5. 只有隔离、吞吐、故障域或团队边界出现证据时拆服务。

## 18. 架构不变量

1. 所有承载工作的输入经过 Admission；
2. 一个 Accepted Request 创建且只创建一个 Root Run；
3. Control-plane Query 和事件订阅不创建伪 Run；
4. External Component 只能 Proposal，Shadow 才能 Commit；
5. Canonical Envelope 统一治理，Profile 保留类型语义；
6. 新 target_kind 不修改 Core 主流程；
7. Runtime 不拥有 Run 或 Durable Task；
8. Memory Intelligence 不拥有 Canonical Memory；
9. State Resolver 不拥有 Accepted State；
10. Skill Bundle 保持标准格式；
11. Adapter 只承诺已声明 Capability；
12. Store Capability 不伪装成完整数据库抽象；
13. Complex Policy 可以外置，最终确定性检查留在 Core；
14. Domain Event 不是事实源；
15. 删除 Derived State 不丢失 Canonical Asset；
16.组件替换必须经过兼容性、迁移或重建；
17.健康、TTL、取消和恢复不依赖 LLM；
18.用户拥有纠正、删除、导出和迁移权。

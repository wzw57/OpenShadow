# OpenShadow 概要设计

- 状态：已确认边界的概要设计
- 目标：描述完整 Shadow、最小 Core 与可替换组件之间的关系
- 非目标：不选择具体 Runtime、模型、Memory 项目、数据库或部署平台

## 1. 系统定义

Shadow 是用户使用的完整 Agent：

~~~text
Shadow
    = Minimal Core
    + Replaceable Components
    + Official or Third-party Adapters
    + User Interfaces
~~~

Runtime 是 Shadow 的组成部分，不是位于 Shadow 之外的另一个 Agent。用户的所有请求都先由 Shadow 准入和记录，再由 Shadow 选择并绑定合适的 Execution Target。开放式任务可以交给 Agent Runtime；单次推理、固定程序和外部动作不必绕经 Agent Runtime。

Shadow Core 不以自行实现更多功能为目标。它只保留无法外包而不破坏用户资产、任务连续性、当前状态、权威边界和升级能力的部分。

## 2. 最小 Core

### 2.1 Core 职责

最小 Core 包含：

1. **Domain Contracts**  
   定义 Run、Task、Checkpoint、Memory、Observation、World State、Executable Asset、Owner、Space、Routing Rule、Capability Envelope、Retention、Erasure、Skill、Extension、Integration、Capability、Action 等长期语义。

2. **Authority & State Transition**  
   校验 Proposal，执行 Owner / Space、数据分级、Retention、Erasure 和 Capability Envelope 等权限边界，提交 Canonical Memory、World State、Task 和 Action 等权威状态。

3. **Task Continuity**  
   管理 Request Admission、Run、Durable Task、Checkpoint、Execution Binding 和 Handoff。

4. **Execution Dispatch**  
   根据已确认的 Binding 将执行交给 Agent Runtime、Model Worker、Deterministic Runner 或 Capability Provider，并统一记录 Status 与 Result。高级路由策略不属于 Core。

5. **Asset & Capability Catalog**  
   管理用户长期资产、Owner / Space、外部资产引用、Executable Asset、Routing Rule、Skill、Extension、Integration 和 Capability Binding。

6. **Extension Control Plane**  
   管理 Adapter Contract、Manifest、版本、权限、健康和兼容性。

7. **Portability & Upgrade**  
   管理 Stable ID、Schema Version、Export、Import、Migration 和 Integrity Verification。

### 2.2 裸核结构

~~~mermaid
flowchart TB
    REQUEST["Chat / CLI / API / Voice / Event / Schedule"]

    subgraph CORE["Shadow Minimal Core"]
        direction TB
        INGRESS["Request Admission & Run<br/>统一入口、最小 Run 记录"]
        CONTRACTS["Domain Contracts<br/>Stable IDs / Versioned Records"]

        subgraph CONTROL["Authority, Continuity and Dispatch"]
            direction LR
            TASK["Task Continuity<br/>Task / Checkpoint / Handoff"]
            EXEC["Execution Dispatch<br/>Requirements / Binding / Status / Result"]
            STATE["State Authority<br/>Validate Proposal / Commit"]
            POLICY["Policy Enforcement<br/>Approval / Action Ledger"]
        end

        subgraph CONTEXT["Durable User Context"]
            direction LR
            WORLD["World State<br/>Observation / Freshness / Current Belief"]
            ASSETS["Asset Catalog<br/>Memory / Skill / Executable / Artifact"]
            REGISTRY["Extension / Integration / Capability Registry"]
        end

        PORTABILITY["Portability & Upgrade<br/>Export / Import / Migration / Verification"]

        subgraph PORTS["Versioned Ports"]
            direction LR
            STORE_PORT{{"Durable Store"}}
            RUNTIME_PORT{{"Agent Runtime"}}
            MODEL_PORT{{"Model Worker"}}
            RUNNER_PORT{{"Deterministic Runner"}}
            ROUTING_PORT{{"Routing"}}
            MEMORY_PORT{{"Memory Intelligence"}}
            SOURCE_PORT{{"Asset / State Source"}}
            PROVIDER_PORT{{"Capability Provider"}}
            INTERACTION_PORT{{"Interaction"}}
            INFRA_PORT{{"Infrastructure"}}
        end
    end

    REQUEST --> INGRESS --> TASK --> EXEC
    CONTRACTS --> TASK
    CONTRACTS --> EXEC
    CONTRACTS --> STATE
    CONTRACTS --> WORLD
    STATE --> POLICY
    WORLD --> EXEC
    ASSETS --> EXEC
    REGISTRY --> EXEC

    EXEC --> RUNTIME_PORT
    EXEC --> MODEL_PORT
    EXEC --> RUNNER_PORT
    EXEC --> ROUTING_PORT
    ASSETS --> MEMORY_PORT
    WORLD --> SOURCE_PORT
    ASSETS --> SOURCE_PORT
    POLICY --> PROVIDER_PORT
    INGRESS --> INTERACTION_PORT
    TASK --> INFRA_PORT
    STATE --> STORE_PORT
    PORTABILITY --> STORE_PORT
~~~

裸核只有稳定 Contract、状态提交边界和 Port。没有绑定 Durable Store 时，Shadow 不承诺持久状态；没有任何 Execution Target 时，Shadow 可以接收和记录请求，但不能完成对应执行。

## 3. 完整可插拔架构

~~~mermaid
flowchart TB
    subgraph ENTRY["Shadow 交互与触发入口"]
        direction LR
        CHAT["Chat / Web / Desktop"]
        CLI["CLI / API"]
        VOICE["Voice / Device Endpoint"]
        EVENTS["Events / Schedule"]
    end

    subgraph CORE["Shadow Minimal Core"]
        direction TB
        ADMISSION["Request Admission & Minimal Run"]
        CONTINUITY["Task Continuity<br/>Checkpoint / Handoff"]
        DISPATCH["Execution Dispatch<br/>Requirements / Binding / Status / Result"]
        AUTHORITY["Authority & State Transition<br/>Policy / Approval / Ledger"]
        WORLD["World State<br/>Observation / Freshness / Current Belief"]
        CATALOG["Asset & Capability Catalog<br/>Memory / Skill / Executable / Integration"]
        REGISTRY["Adapter Registry<br/>Version / Permission / Compatibility"]
        PORTABLE["Portability & Upgrade<br/>Migration / Export / Verification"]

        subgraph PORTS["Stable Contract Ports"]
            direction LR
            P_STORE{{"Durable Store"}}
            P_RUNTIME{{"Agent Runtime"}}
            P_MODEL{{"Model Worker"}}
            P_RUNNER{{"Deterministic Runner"}}
            P_ROUTING{{"Routing"}}
            P_MEMORY{{"Memory Intelligence"}}
            P_SOURCE{{"Asset / State Source"}}
            P_PROVIDER{{"Capability Provider"}}
            P_INTERACTION{{"Interaction"}}
            P_INFRA{{"Infrastructure"}}
        end
    end

    subgraph ADAPTERS["Replaceable Adapter Layer"]
        direction LR
        A_STORE["Store Adapter"]
        A_RUNTIME["Runtime Adapter"]
        A_MODEL["Model Adapter"]
        A_RUNNER["Runner Adapter"]
        A_ROUTING["Routing Adapter"]
        A_MEMORY["Memory Adapter"]
        A_SOURCE["Source Connector"]
        A_PROVIDER["Provider / MCP Adapter"]
        A_INTERACTION["Shell / Voice Adapter"]
        A_INFRA["Scheduler / Search / Secret / Observe Adapter"]
    end

    subgraph IMPLEMENTATIONS["Replaceable Implementations"]
        direction LR
        DB[("Database Engine")]
        RUNTIME["Agent Runtime<br/>Planner / Subagent / Tool Loop"]
        MODELS["Models / Small Workers<br/>Classify / Extract / Summarize"]
        RUNNERS["Script Runners<br/>Functions / Programs / Sandboxes"]
        ROUTER["Routing Intelligence<br/>Rules / Policy / Evaluation"]
        MEMORY["Memory Intelligence<br/>Extract / Consolidate / Retrieve"]
        SOURCES["External Sources<br/>Notes / Calendar / Weather / Devices"]
        PROVIDERS["External Services<br/>Accounts / Devices / Tools"]
        UX["User Experience<br/>Chat / Voice / Apps"]
        INFRA["Infrastructure<br/>Scheduler / Index / Secret / Telemetry"]
    end

    CHAT --> ADMISSION
    CLI --> ADMISSION
    VOICE --> ADMISSION
    EVENTS --> ADMISSION

    ADMISSION --> CONTINUITY --> DISPATCH
    WORLD --> DISPATCH
    CATALOG --> DISPATCH
    REGISTRY --> CATALOG
    DISPATCH --> AUTHORITY
    PORTABLE --> CATALOG

    AUTHORITY --> P_STORE
    DISPATCH --> P_RUNTIME
    DISPATCH --> P_MODEL
    DISPATCH --> P_RUNNER
    DISPATCH --> P_ROUTING
    CATALOG --> P_MEMORY
    WORLD --> P_SOURCE
    CATALOG --> P_SOURCE
    AUTHORITY --> P_PROVIDER
    ADMISSION --> P_INTERACTION
    CONTINUITY --> P_INFRA

    P_STORE <--> A_STORE <--> DB
    P_RUNTIME <--> A_RUNTIME <--> RUNTIME
    P_MODEL <--> A_MODEL <--> MODELS
    P_RUNNER <--> A_RUNNER <--> RUNNERS
    P_ROUTING <--> A_ROUTING <--> ROUTER
    P_MEMORY <--> A_MEMORY <--> MEMORY
    P_SOURCE <--> A_SOURCE <--> SOURCES
    P_PROVIDER <--> A_PROVIDER <--> PROVIDERS
    P_INTERACTION <--> A_INTERACTION <--> UX
    P_INFRA <--> A_INFRA <--> INFRA
~~~

外部实现不能绕过 Port 直接修改 Shadow 权威状态。Adapter 可以由 OpenShadow 官方提供，也可以由第三方提供，但必须遵守相同 Contract。

## 4. Admission、Request、Run、Attempt 与 Task

所有输入先经过 Shadow Admission。被拒绝的输入只产生最小 Admission Record；被接受的 Request 是不可变准入记录，并创建一个 Root Run。

~~~mermaid
flowchart TB
    INPUT["Incoming Input"]
    ADMISSION["Admission"]
    REJECT["Admission Record<br/>rejected / invalid / replay"]
    REQUEST["Accepted Request<br/>immutable"]
    RUN["Root Run"]
    ATTEMPT1["Execution Attempt 1"]
    ATTEMPT2["Execution Attempt 2"]
    TARGETS["Runtime / Model / Runner / Provider"]
    RESULT["Result / Proposal"]
    TASK["Durable Task"]

    INPUT --> ADMISSION
    ADMISSION -->|"rejected"| REJECT
    ADMISSION -->|"accepted"| REQUEST --> RUN
    RUN --> ATTEMPT1
    ATTEMPT1 -->|"retry"| ATTEMPT2
    ATTEMPT1 --> TARGETS
    ATTEMPT2 --> TARGETS
    TARGETS --> RESULT
    RESULT -->|"Task Proposal validated by Core"| TASK
~~~

重试在同一 Run 下创建新的 Execution Attempt，不能覆盖原 Attempt，也不创建重复 Root Run。

Run 的最小状态包含 created、queued、running、waiting、paused、cancelling、cancelled、cancellation_unknown、completed 和 failed。用户请求取消只是进入 cancelling；只有 Target 确认停止后才能提交 cancelled，无法确认时提交 cancellation_unknown。

最小记录用于身份、时间、状态、Binding、费用、结果摘要和审计引用。完整 Prompt、输出和工具过程按 Retention Policy 与 Data Classification 保存；Runtime 私有推理不进入 Canonical State。

Durable Task 只表示需要跨 Session、Execution Target、重启、等待条件或长期时间存在的工作。用户可以直接创建；Runtime、Semantic Pulse 和规则只能提交 Task Proposal。一个 Durable Task 可以产生多个 Run。Run 成功不自动代表 Task 完成，Core 根据 Completion Proposal、完成条件、外部结果和 reconciliation 提交最终状态。

Runtime 内部 Subtask、Planner 和 Agent Loop 保持私有。

## 5. Execution Plane

### 5.1 Core 与路由边界

Core 定义最小执行语义：

- Execution Request；
- Requirements：能力、延迟、成本、隐私、可靠性和工具需求；
- Binding：本次实际绑定的 Target 与版本；
- Target Descriptor：能力声明、限制、健康和权限；
- Status、Result、Failure 和 Retry 语义。

Core 负责准入、显式规则、Binding 校验、预算与权限执行、记录和结果提交。模型评分、任务分类、动态策略、A/B 测试和多模型优化由可替换 Routing Component 提供。Router 只能提出 Binding Proposal，Core 决定是否接受。

### 5.2 Execution Target

| Target | 适用场景 | 不负责 |
|---|---|---|
| Agent Runtime | 开放式、多步骤、需要规划或工具循环 | Shadow 权威状态 |
| Model Worker | 分类、提取、总结、改写等单次受限推理 | Durable Task 编排 |
| Deterministic Runner | 已登记脚本、函数、固定程序 | 语义规划和权限决策 |
| Capability Provider | 外部 API、账户、家电和其他现实动作 | Shadow Action Authority |

一个 Run 可以依次使用多个 Target，但每次 Binding 都必须可追踪。基础版本可以只使用用户显式选择和静态规则，不要求先实现智能路由。

### 5.3 Executable Asset

脚本和固定程序作为用户长期能力资产登记，至少包含：

- Stable ID、source reference、version 和 checksum；
- input / output contract；
- runtime requirements 和 dependency reference；
- requested permissions；
- provenance、trust 和 compatibility metadata。

Shadow 管理其身份、授权、Binding 和执行记录；依赖解析、语言运行时、资源限制、隔离与实际执行由可替换 Runner 负责。

### 5.4 Capability Envelope 与跨边界调用

Capability Envelope 是 Policy Authority 对一次 Run 或 Durable Task 的授权结果，不是新的权限引擎。它至少包含 Target Binding、允许的 Capability、数据和资源范围、副作用等级、预算、有效期、撤销状态和 Policy Version。

普通 Run 使用短期 Envelope；Durable Task 可以使用可撤销、可过期的长期 Envelope。任务恢复时必须重新验证有效期、策略、组件身份和版本兼容性。

Runtime 可以在 Envelope 内管理自己的 Planner、Subtask、模型和脚本调用。Shadow 不保存 Runtime 私有推理，但跨 Adapter、预算或副作用边界的调用必须产生最小 Usage Record 或 Action Record。越界时由预设策略批准、拒绝或降级；没有匹配策略时询问用户。

Router 无法安全决定 Target 时同样询问用户。用户可以仅批准当前 Binding，也可以保存为可迁移的 Routing Rule。

## 6. Task Continuity

Shadow Core 持有：

- Durable Task identity；
- lifecycle state；
- Execution Binding；
- Runtime Checkpoint Reference；
- Semantic Checkpoint；
- Artifact Reference；
- waiting / trigger reference；
- completion commit。

Agent Runtime 持有 planning、subtask、subagent、workflow、tool loop 和 runtime-native session state。Runtime 可以提出 progress、failure 和 completion，但 Durable Task 的最终状态由 Shadow 提交。

非 Runtime Target 不需要伪造 Runtime Checkpoint；其恢复语义由 Execution Contract 和幂等性信息决定。

## 7. Memory 架构

### 7.1 逻辑所有权

Canonical Memory 属于 Shadow，Memory Intelligence 不拥有用户记忆。

~~~text
Shadow owns Canonical Memory semantics.
Memory component provides intelligence.
Durable Store component provides physical persistence.
~~~

### 7.2 写入流程

~~~mermaid
flowchart LR
    INPUT["Conversation / Task / External Source"]
    ENGINE["Replaceable Memory Intelligence"]
    CANDIDATE["Memory Candidate"]
    CORE["Shadow Memory Authority"]
    STORE_PORT{{"Durable Store Port"}}
    DB[("Database Engine")]

    INPUT --> ENGINE --> CANDIDATE --> CORE
    CORE -->|"validate and commit"| STORE_PORT --> DB
~~~

Shadow 自己定义 Memory Record、Stable ID、Provenance、Scope、Validity、Version、source_dependency 和状态变更语义。数据库引擎和 Memory Intelligence 都可以替换。

外部原始资产删除后，independent Memory 可以继续存在；dependent Memory 必须失效或删除；unknown 按策略等待确认。Canonical Memory 默认先逻辑删除，之后允许物理清除。纠正产生版本与 supersede 关系，但用户可以彻底擦除敏感历史。

### 7.3 派生状态与自动整理

Embedding、Index、Memory Graph、Cluster、Summary Projection、Ranking State 和 Engine Cache 属于可重建实现。

Shadow 可以按需或周期性触发 Memory 整理。Core 决定触发、授权范围和 Candidate 提交；外部组件负责 Extraction、Consolidation、Deduplication、Retrieval、Reranking 和其他智能实现。

Contract 不阻止未来组合多个 Memory Component，但当前架构不定义动态路由、并行融合或自动选择策略。

## 8. Observation 与 World State

Memory 回答“过去长期知道什么”，World State 回答“Shadow 目前认为现实是什么状态”。它们可以互相引用，但不能混为一个对象。

~~~mermaid
flowchart LR
    SOURCE["Calendar / Weather / Device / Location / User"]
    CONNECTOR["Replaceable State Source Adapter"]
    OBS["Observation Proposal<br/>value / source / observed_at / TTL"]
    AUTH["Shadow State Authority"]
    WORLD["World State Projection<br/>fresh / stale / unknown"]
    COND["Condition / Request Context"]

    SOURCE --> CONNECTOR --> OBS --> AUTH
    AUTH --> WORLD --> COND
    COND -->|"when authorized"| DISPATCH["Run / Durable Task"]
~~~

Core 只保留通用且可迁移的当前状态语义：

- subject、property、value、schema_ref 和关系；
- source、observed_at、received_at；
- TTL / expires_at；
- fresh、stale、unknown；
- owner_ref、space_id、scope、version 和 provenance；
- accepted projection、冲突候选与证据引用；
- Retention Policy、source availability 和删除状态。

Accepted World State 属于 Canonical State。Shadow 重启后必须能够恢复最后接受的状态、过期时间和当前不可信的原因。Observation 按类型保留：高频状态可以短期保存或压缩，关键变化可以长期保存。

用户明确陈述具有最高来源优先级，但不会永久冻结状态；更新、更可靠的 Observation 可以替换它。Core 处理 TTL、来源禁用、用户明确规则等确定性逻辑；复杂冲突由可替换 State Resolver 通过 Execution Plane 返回 WorldState Proposal。Resolver 不拥有特权提交路径。

删除 Integration 后，最后状态标记 source unavailable，并按 TTL 进入 stale 或 unknown；用户仍可主动删除相关状态和 Observation。

日历、天气、设备、位置等采集与协议外置；领域 Schema 由 Integration 或 Extension 声明；复杂融合、预测和领域模型也外置。外部 Source 只能提交 Observation Proposal，不能直接改写 World State。

World State 不是完整数字孪生，不要求 Shadow 实时访问所有外部系统。需要时刷新、按 TTL 失效，并明确表达 unknown，比伪造“实时”更重要。

## 9. Health Heartbeat 与 Semantic Pulse

两类“心跳”必须分开：

1. **System Health Heartbeat**  
   检查进程、Adapter、租约、超时和调度 tick。它必须确定性运行，不依赖 LLM，并支撑恢复与故障检测。

2. **Semantic Pulse**  
   可选的小模型或规则 Worker，周期性检查授权范围内的 Event、World State 和近期活动，提出 Recall、State Update、Run、Durable Task 或升级到更强 Target 的 Proposal。

Semantic Pulse 不能直接提交权威状态，不能绕过预算与权限，也不能成为系统正确运行的前提。关闭或更换它，只会降低主动智能程度，不会破坏任务恢复、状态过期或安全边界。

## 10. 外部信息资产

Shadow 不复制和管理用户全部外部资料。

Asset Catalog 只保存资产存在性、来源、引用、Integration Binding、可用状态和必要访问边界。Shadow 在 Task、Recall、World State 刷新或后台 Memory 整理需要时，通过 Connector 按需读取外部内容。

外部来源负责原始内容的存储和生命周期。由外部内容形成并提交的 Canonical Memory 或 World State 记录则进入 Shadow 的长期状态。

## 11. 能力资产与统一管理

用户长期积累的能力包括：

- Skill；
- Executable Asset；
- Extension；
- Integration；
- MCP Connection；
- Runtime / Model / Runner Profile；
- Capability Binding；
- Configuration 和 Permission Metadata。

这些对象在用户界面上可以统一呈现，但 Core 必须区分其语义。Secret 通过 Secret Reference 管理，不进入普通资产导出。

## 12. Adapter 模型

Shadow 自己维护 Port Contract、Adapter SDK、Extension Manifest、Capability Declaration、Permission Declaration、Version Negotiation、Health Contract 和 Contract Test Suite。

具体 Adapter 是可替换组件。Contract 应采用小而稳定的基础语义，并允许组件声明额外 Capability。不能为了兼容当前项目，把所有未来能力冻结进一个巨大接口。

## 13. Durable Store

Shadow 不开发数据库引擎。

Core 定义 Canonical Record、Stable ID、Schema Version、concurrency requirement、Migration、Export / Import 和 Integrity Verification。Store Adapter 将这些语义映射到具体数据库，并声明 transaction、encryption、backup、outbox、availability 和 migration 等 Capability。

任何时刻必须存在一个可用的 Primary Durable Store，Shadow 才能承诺长期状态持久化。更换数据库时，通过版本化导出、迁移和完整性验证完成切换。

Primary Store 不可用时，Shadow 进入受限模式：

- 只读和临时交互可以继续，并明确提示不承诺保存；
- 需要 Canonical Commit 的操作暂停；
- 现实副作用默认禁止；
- 明确配置的紧急 Capability 可以先写入可靠的本地持久 Outbox，再执行；
- Store 恢复后执行幂等提交、去重和 reconciliation。

Core 不实现数据库、物理备份或消息队列。

## 14. Capability 与现实动作

Agent Runtime、Model Worker、Runner 或其他组件只能提出 Action Proposal。

~~~text
Proposal
   ↓
Schema Validation
   ↓
Policy Enforcement
   ↓
Approval when required
   ↓
Provider Adapter
   ↓
External Result
   ↓
Action Ledger / Reconciliation
~~~

Core 持有 Capability 语义、Authorization Point、Action ID 和结果状态；Provider 与协议实现外置。

## 15. Owner、Space 与 Canonical Envelope

Owner 是资产的长期控制主体，可以是 User 或 Space。Space 是归属、上下文与未来共享的稳定边界。created_by 与 owner_ref 分开记录。

第一版创建正式的 Personal Space 和隐式 Home Space Record，但不实现成员、角色、邀请和共享。个人 Memory 可以归 User；公共房间和家庭设备状态归 Home Space。

所有 Canonical Record 使用共同的治理信封，但保留各自业务 Schema：

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref / space_id / created_by
├─ data_classification
├─ provenance / version
├─ retention_policy / lifecycle_state
└─ typed payload
~~~

## 16. 数据分级、Model Binding 与 Secret

Core 只定义 public、personal、sensitive、restricted 四级稳定语义。用户、来源和可替换分类器可以提出标签；无法判断时默认 sensitive。分类器可以提高等级，降低等级必须由用户或确定性策略确认。

每个 Model Binding 必须声明 local / remote、可处理的数据等级、是否允许 Memory、World State 和外部资产内容，以及 retention、training、地域或组织限制。Shadow 在执行前根据 Binding 和 Capability Envelope 裁剪最小上下文。

Secret 是用户长期能力资产，但凭据与普通 Canonical Asset 分离。Integration 保存 Secret Reference。标准导出不包含 Secret 内容；完整备份只有在独立授权和加密后才能包含。

“本地优先”约束的是用户控制、可迁移和可验证，而不是固定物理位置。Durable Store 可以本地或远程绑定，默认配置优先提供本地实现。

## 17. Retention、Erasure、导出与备份

Core 管理 Retention Policy、Logical Delete、Restore、Physical Erasure Intent、Tombstone 和组件清除状态。Adapter 负责清除 Memory Engine、Index、Cache、Backup 和其他派生副本。

无法确认清除的组件必须显示 pending 或 unreachable，不能谎报完成。Tombstone 只保留防止错误复活所需的最小元数据，不包含被删除的敏感内容。

Shadow 提供两种不同产物：

1. **标准可移植导出**：Canonical Assets、Owner / Space、Integration、Binding、Schema 和迁移元数据；不包含 Secret 内容和可重建状态；
2. **完整设备备份**：可以包含加密 Secret、Checkpoint 和部分派生状态，但必须独立加密和授权，且不能作为跨实现兼容性的基础。

## 18. 运行与部署

逻辑边界不等于进程边界。

早期实现优先采用模块化单体和少量外部组件。Adapter 可以运行在进程内或进程外，只要不绕过 Contract 和权限边界。

具体数据库、Runtime、Model、Router、Runner、Memory Intelligence、State Resolver、Scheduler、Search、Secret Store、Voice 和部署平台不在当前架构中冻结。

## 19. 架构不变量

1. 所有请求由 Shadow 准入，并至少产生最小 Run 记录；
2. 所有执行由 Shadow 绑定和治理，但并非所有执行都经过 Agent Runtime；
3. Runtime 不拥有 Durable Task；
4. Memory Intelligence 不拥有 Canonical Memory；
5. 数据库引擎不定义 Shadow Domain Semantics；
6. 外部信息源不由 Shadow 负责长期存储；
7. 外部 Observation 不能绕过 Shadow 直接修改 World State；
8. External Component 不能直接提交 Shadow 权威状态；
9. 删除派生组件不丢失 Canonical Asset；
10. Skill、Executable Asset、Extension 和 Integration 是用户长期能力资产；
11. 系统健康、超时和恢复不依赖 Semantic Pulse 或任何 LLM；
12. 每个 Canonical Asset 都具有显式 Owner 和 Space；
13. 家庭公共状态可以归 Home Space，而不被固定到某个用户；
14. 外部分类器不能自行降低数据保护等级；
15. Model Binding 不能接收超出声明边界的上下文；
16. 逻辑删除和审计不能取消用户最终物理删除权；
17. Store 故障时，未记录的现实副作用不能继续执行；
18. 标准可移植导出不依赖 Secret、派生状态或具体组件私有格式；
19. 组件替换必须经过兼容性、迁移或重建流程。

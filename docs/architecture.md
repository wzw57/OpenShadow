# OpenShadow 概要设计

- 状态：已确认边界的概要设计
- 目标：描述完整 Shadow、最小 Core 与可替换组件之间的关系
- 非目标：不选择具体 Runtime、Memory 项目、数据库或部署平台

## 1. 系统定义

Shadow 是用户使用的完整 Agent：

~~~text
Shadow
    = Minimal Core
    + Replaceable Components
    + Official or Third-party Adapters
    + User Interfaces
~~~

Runtime 是 Shadow 的组成部分，不是位于 Shadow 之外的另一个 Agent。用户的所有请求都先由 Shadow 准入，再由 Shadow 绑定 Runtime 和其他能力。

Shadow Core 不以自行实现更多功能为目标。它只保留无法外包而不破坏用户资产、任务连续性、权威状态和升级能力的部分。

## 2. 最小 Core

### 2.1 Core 职责

最小 Core 包含：

1. **Domain Contracts**  
   定义 Run、Task、Checkpoint、Memory、Skill、Extension、Integration、Capability、Action 等长期语义。

2. **Authority & State Transition**  
   校验 Proposal，执行权限边界，提交权威状态。

3. **Task Continuity**  
   管理 Request Admission、Run、Durable Task、Checkpoint、Runtime Binding 和 Handoff。

4. **Asset & Capability Catalog**  
   管理用户长期资产、外部资产引用、Skill、Extension、Integration 和 Capability Binding。

5. **Extension Control Plane**  
   管理 Adapter Contract、Manifest、版本、权限、健康和兼容性。

6. **Portability & Upgrade**  
   管理 Stable ID、Schema Version、Export、Import、Migration 和 Integrity Verification。

### 2.2 裸核结构

~~~mermaid
flowchart TB
    REQUEST["Chat / CLI / API / Voice / Event / Schedule"]

    subgraph CORE["Shadow Minimal Core"]
        direction TB

        INGRESS["Request Admission & Run<br/>统一入口、最小 Run 记录"]

        CONTRACTS["Domain Contracts<br/>Stable IDs / Versioned Records"]

        subgraph AUTHORITY["Authority and Continuity"]
            direction LR
            TASK["Task Continuity<br/>Task / Checkpoint / Handoff"]
            STATE["State Transition<br/>Validate / Commit"]
            POLICY["Policy Enforcement Point<br/>Approval / Action Ledger"]
        end

        subgraph CATALOGS["User Asset Control Plane"]
            direction LR
            ASSETS["Asset Catalog<br/>Memory / Skill / Artifact"]
            EXTENSIONS["Extension & Integration Registry"]
            CAPABILITIES["Capability & Provider Binding"]
        end

        PORTABILITY["Portability & Upgrade<br/>Export / Import / Migration / Verification"]

        subgraph PORTS["Versioned Ports"]
            direction LR
            STORE_PORT{{"Durable Store"}}
            RUNTIME_PORT{{"Runtime"}}
            MEMORY_PORT{{"Memory Intelligence"}}
            SOURCE_PORT{{"Source Connector"}}
            PROVIDER_PORT{{"Capability Provider"}}
            INTERACTION_PORT{{"Interaction"}}
            INFRA_PORT{{"Infrastructure"}}
        end
    end

    REQUEST --> INGRESS
    INGRESS --> TASK
    TASK --> STATE
    STATE --> POLICY

    CONTRACTS --> TASK
    CONTRACTS --> STATE
    CONTRACTS --> ASSETS

    ASSETS --> STATE
    EXTENSIONS --> CAPABILITIES
    CAPABILITIES --> POLICY

    STATE --> STORE_PORT
    TASK --> RUNTIME_PORT
    ASSETS --> MEMORY_PORT
    ASSETS --> SOURCE_PORT
    POLICY --> PROVIDER_PORT
    INGRESS --> INTERACTION_PORT

    PORTABILITY --> STORE_PORT
    EXTENSIONS --> PORTS
~~~

裸核只有 Contract 和 Port。没有绑定 Durable Store 时，Shadow 不承诺持久状态；没有绑定 Runtime 时，Shadow 不能执行智能任务。

## 3. 完整可插拔架构

~~~mermaid
flowchart TB
    subgraph ENTRY["Shadow 交互入口"]
        direction LR
        CHAT["Chat / Web / Desktop"]
        CLI["CLI / API"]
        VOICE["Voice / Device Endpoint"]
        EVENTS["Events / Schedule"]
    end

    subgraph CORE["Shadow Minimal Core"]
        direction TB
        ADMISSION["Request Admission & Run"]
        CONTINUITY["Task Continuity<br/>Checkpoint / Handoff"]
        AUTHORITY["Authority & State Transition<br/>Policy / Approval / Ledger"]
        CATALOG["Asset & Capability Catalog<br/>Memory / Skill / Extension / Integration"]
        REGISTRY["Adapter Registry<br/>Version / Permission / Compatibility"]
        PORTABLE["Portability & Upgrade<br/>Migration / Export / Verification"]

        subgraph PORTS["Stable Contract Ports"]
            direction LR
            P_STORE{{"Durable Store"}}
            P_RUNTIME{{"Runtime"}}
            P_MEMORY{{"Memory Intelligence"}}
            P_SOURCE{{"Asset Source"}}
            P_PROVIDER{{"Capability Provider"}}
            P_INTERACTION{{"Interaction"}}
            P_INFRA{{"Infrastructure"}}
        end
    end

    subgraph ADAPTERS["Replaceable Adapter Layer"]
        direction LR
        A_STORE["Store Adapter"]
        A_RUNTIME["Runtime Adapter"]
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
        MEMORY["Memory Intelligence<br/>Extract / Consolidate / Retrieve"]
        SOURCES["External Information<br/>Notes / Drive / Email / Files"]
        PROVIDERS["External Services<br/>Accounts / Devices / Tools"]
        UX["User Experience<br/>Chat / Voice / Apps"]
        INFRA["Infrastructure<br/>Scheduler / Index / Secret / Telemetry"]
    end

    CHAT --> ADMISSION
    CLI --> ADMISSION
    VOICE --> ADMISSION
    EVENTS --> ADMISSION

    ADMISSION --> CONTINUITY
    CONTINUITY --> AUTHORITY
    CATALOG --> AUTHORITY
    REGISTRY --> CATALOG
    PORTABLE --> CATALOG

    AUTHORITY --> P_STORE
    CONTINUITY --> P_RUNTIME
    CATALOG --> P_MEMORY
    CATALOG --> P_SOURCE
    AUTHORITY --> P_PROVIDER
    ADMISSION --> P_INTERACTION
    CONTINUITY --> P_INFRA

    P_STORE <--> A_STORE
    P_RUNTIME <--> A_RUNTIME
    P_MEMORY <--> A_MEMORY
    P_SOURCE <--> A_SOURCE
    P_PROVIDER <--> A_PROVIDER
    P_INTERACTION <--> A_INTERACTION
    P_INFRA <--> A_INFRA

    A_STORE <--> DB
    A_RUNTIME <--> RUNTIME
    A_MEMORY <--> MEMORY
    A_SOURCE <--> SOURCES
    A_PROVIDER <--> PROVIDERS
    A_INTERACTION <--> UX
    A_INFRA <--> INFRA
~~~

外部实现不能绕过 Port 直接修改 Shadow 权威状态。Adapter 可以由 OpenShadow 官方提供，也可以由第三方提供，但必须遵守相同 Contract。

## 4. Request、Run 与 Task

所有请求经过 Shadow，但持久化程度不同。

~~~text
Incoming Request
      ↓
Shadow creates minimal Run
      ↓
Runtime executes
      ↓
Result may remain ephemeral
      ├─ produce Canonical Memory
      ├─ produce Artifact
      ├─ produce governed Action
      └─ promote to Durable Task
~~~

最小 Run 记录用于身份、绑定、状态和审计。完整 Prompt、输出和工具过程是否长期保存，由用户策略决定。

Durable Task 只表示需要跨 Session、Runtime、等待条件或长期时间存在的工作。Runtime 内部 Subtask、Planner 和 Agent Loop 保持私有。

## 5. Task Continuity

Shadow Core 持有：

- Durable Task identity；
- lifecycle state；
- Runtime Binding；
- Runtime Checkpoint Reference；
- Semantic Checkpoint；
- Artifact Reference；
- waiting / trigger reference；
- completion commit。

Runtime 持有：

- planning；
- subtask；
- subagent；
- workflow；
- tool loop；
- runtime-native session state。

Runtime 可以提出 progress、failure 和 completion，但 Durable Task 的最终状态由 Shadow 提交。

## 6. Memory 架构

### 6.1 逻辑所有权

Canonical Memory 属于 Shadow，Memory Intelligence 不拥有用户记忆。

~~~text
Shadow owns Canonical Memory semantics.
Memory component provides intelligence.
Durable Store component provides physical persistence.
~~~

### 6.2 写入流程

~~~mermaid
flowchart LR
    INPUT["Conversation / Task / External Source"]
    ENGINE["Replaceable Memory Intelligence"]
    CANDIDATE["Memory Candidate"]
    CORE["Shadow Memory Authority"]
    STORE_PORT{{"Durable Store Port"}}
    DB[("Database Engine")]

    INPUT --> ENGINE
    ENGINE --> CANDIDATE
    CANDIDATE --> CORE
    CORE -->|"validate and commit"| STORE_PORT
    STORE_PORT --> DB
~~~

Shadow 自己定义 Memory Record、Stable ID、Provenance、Scope、Validity、Version 和状态变更语义。数据库引擎和 Memory Intelligence 都可以替换。

### 6.3 派生状态

以下状态属于可重建实现：

- Embedding；
- Vector / Full-text Index；
- Memory Graph；
- Cluster；
- Summary Projection；
- Ranking State；
- Engine-specific Cache。

外部 Memory Component 可以使用自己的 Store，但它不能成为 Canonical Memory 无法迁移的唯一事实源。

### 6.4 自动整理

Shadow 可以按需或周期性触发 Memory 整理。Core 决定触发、授权范围和 Candidate 提交；外部组件负责 Extraction、Consolidation、Deduplication、Retrieval、Reranking 和其他智能实现。

Contract 不阻止未来组合多个 Memory Component，但当前架构不定义动态路由、并行融合或自动选择策略。

## 7. 外部信息资产

Shadow 不复制和管理用户全部外部资料。

Asset Catalog 只保存资产存在性、来源、引用、Integration Binding、可用状态和必要访问边界。

~~~text
Task / Recall / Background Consolidation
                  ↓
         Shadow authorizes access
                  ↓
            Source Connector
                  ↓
       External content read on demand
                  ↓
       Runtime or Memory Intelligence
~~~

外部来源负责原始内容的存储和生命周期。由外部内容形成并提交的 Canonical Memory 则进入 Shadow 的长期状态。

## 8. 能力资产与统一管理

用户长期积累的能力包括：

- Skill；
- Extension；
- Integration；
- MCP Connection；
- Runtime Profile；
- Capability Binding；
- Configuration 和 Permission Metadata。

这些对象在用户界面上可以统一呈现，但 Core 必须区分其语义：

~~~text
Skill
    可复用的方法与经验

Extension
    提供实现代码的软件包

Integration
    一个已经配置的外部连接

Capability
    稳定的动作或查询语义

Provider Binding
    Capability 当前使用的实现
~~~

Secret 通过 Secret Reference 管理，不进入普通资产导出。

## 9. Adapter 模型

Shadow 自己维护：

- Port Contract；
- Adapter SDK；
- Extension Manifest；
- Capability Declaration；
- Permission Declaration；
- Version Negotiation；
- Health Contract；
- Contract Test Suite。

具体 Adapter 是可替换组件。

Contract 应采用小而稳定的基础语义，并允许组件声明额外 Capability。不能为了兼容当前项目，把所有未来能力冻结进一个巨大接口。

## 10. Durable Store

Shadow 不开发数据库引擎。

Core 定义：

- Canonical Record；
- Stable ID；
- Schema Version；
- concurrency requirement；
- Migration；
- Export / Import；
- Integrity Verification。

Store Adapter 将这些语义映射到具体数据库。

任何时刻必须存在一个可用的 Primary Durable Store，Shadow 才能承诺长期状态持久化。更换数据库时，通过版本化导出、迁移和完整性验证完成切换。

## 11. Capability 与现实动作

Runtime 或其他组件只能提出 Action Proposal。

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

## 12. 运行与部署

逻辑边界不等于进程边界。

早期实现优先采用模块化单体和少量外部组件。Adapter 可以运行在进程内或进程外，只要不绕过 Contract 和权限边界。

具体数据库、Runtime、Memory Intelligence、Scheduler、Search、Secret Store、Voice 和部署平台不在当前架构中冻结。

## 13. 架构不变量

1. 所有请求由 Shadow 准入；
2. 每次执行至少产生最小 Run 记录；
3. Runtime 不拥有 Durable Task；
4. Memory Intelligence 不拥有 Canonical Memory；
5. 数据库引擎不定义 Shadow Domain Semantics；
6. 外部信息源不由 Shadow 负责长期存储；
7. External Component 不能直接提交 Shadow 权威状态；
8. 删除派生组件不丢失 Canonical Asset；
9. Skill、Extension 和 Integration 是用户长期能力资产；
10. 组件替换必须经过兼容性、迁移或重建流程。

# OpenShadow 完整技术架构

- 状态：Stage 4 目标架构基线
- 适用范围：完整 Shadow 产品，不等同于第一阶段实现范围
- 核心方法：先冻结长期稳定边界，再按阶段实现
- 非目标：不指定某个 Runtime、模型、Memory 项目、数据库、消息队列或云平台

## 1. 架构目标

Shadow 是一个可长期持续使用、可替换智能实现、可迁移用户资产的个人 AI。它必须允许 Runtime、模型、Memory Intelligence、数据库、Runner、Router、语音和设备能力持续升级，同时保持用户身份、对话、任务、记忆、现实状态、能力资产和治理记录连续存在。

完整架构遵循以下约束：

1. 所有输入、触发和任务都经过 Shadow Admission。
2. 并非所有执行都经过 Agent Runtime。
3. Shadow 拥有长期语义、权威提交、任务连续性和用户控制。
4. 外部组件拥有快速演进的智能算法、协议实现和具体执行。
5. Canonical State 不依赖任何一个外部组件的私有格式。
6. Adapter 是 Shadow 的正式架构边界，不是临时兼容代码。
7. 逻辑架构与部署拓扑分离；完整模块不等于必须拆成微服务。
8. 第一阶段实现必须是完整目标架构的真子集，不能建立未来需要推翻的旁路。

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
        GATEWAY["Shadow Gateway"]
        SUBJECT["Owner / Space / Endpoint Context"]
        ADMISSION["Admission & Idempotency"]
        DATA_POLICY["Data Boundary & Policy"]
    end

    subgraph CORE["Shadow Core — Authority and Continuity"]
        CONV["Conversation"]
        ORCH["Run / Task Orchestrator"]
        DISPATCH["Execution Dispatch"]
        CONTEXT["Context Authority"]
        MEMORY["Memory Authority"]
        WORLD["World State Authority"]
        ACTION["Action Authority"]
        REGISTRY["Asset / Integration / Adapter Registry"]
        PORTABLE["Migration / Export / Erasure"]
    end

    subgraph EXECUTION["Execution Plane"]
        AGENT["Agent Runtime Host"]
        MODEL["Model Worker Host"]
        PROGRAM["Runner Host"]
        WORKFLOW["Workflow Target"]
        PROVIDER["Capability Provider Host"]
        ROUTER["Optional Routing Intelligence"]
        PULSE["Optional Semantic Pulse"]
    end

    subgraph ADAPTERS["Adapter Control Plane"]
        MANIFEST["Manifest & Capability Declaration"]
        BINDING["Versioned Binding"]
        HOST["Adapter Host"]
        HEALTH["Health / Compatibility"]
        SECRETREF["Secret Reference"]
    end

    subgraph STATE["Canonical State Plane"]
        RECORDS["Canonical Records"]
        EVENTS["Domain Event Envelope"]
        OUTBOX["Optional Durable Outbox"]
        AUDIT["Action / Decision Ledger"]
    end

    subgraph INFRA["Replaceable Infrastructure"]
        STORE[("Primary Durable Store")]
        BLOB[("Blob / Artifact Store")]
        SECRET[("Secret Store")]
        QUEUE["Optional Queue"]
        INDEX["Rebuildable Index / Cache"]
        TELEMETRY["Telemetry Backend"]
    end

    subgraph EXTERNAL["External Implementations and Sources"]
        RUNTIMES["Agent Frameworks"]
        MODELS["Model Providers"]
        MEMORY_ENGINE["Memory Intelligence"]
        KNOWLEDGE["External Knowledge Sources"]
        SERVICES["External Services / MCP"]
        DEVICES["Home / Personal Devices"]
    end

    INTERACTION --> ACCESS
    ACCESS --> CORE
    CORE --> EXECUTION
    CORE --> STATE
    EXECUTION --> ADAPTERS
    ADAPTERS --> EXTERNAL
    STATE --> INFRA
    CORE --> ADAPTERS
~~~

图中的 Plane 表示责任边界，而不是进程边界。默认参考部署可以将 Access、Core、Canonical State 协调逻辑和部分 Adapter Host 放在同一进程中；高风险、资源密集或不可信执行再独立运行。

## 3. 四个稳定平面

### 3.1 Interaction Plane

负责把 Web、桌面端、未来移动端、语音端点、API、事件和定时触发转换为统一输入。

它可以负责：

- 界面状态、流式显示和设备交互；
- 本地音频采集与播放；
- Endpoint 身份和能力声明；
- 用户确认、纠正、批准和取消操作。

它不能：

- 直接修改 Canonical Memory 或 World State；
- 绕过 Admission 启动 Runtime；
- 保存唯一的任务事实；
- 直接持有现实动作权限。

Web 是第一个正式客户端，但 Shadow API 不绑定 Web 技术，因此未来多端不需要重写 Core。

### 3.2 Access & Admission Plane

负责将任何输入绑定到明确的主体、空间和策略上下文，并建立一次可追踪执行的起点。

主要责任：

- 解析 owner_ref、space_id、endpoint_id 和 session_ref；
- 去重、速率限制、输入大小和 Schema 校验；
- 确定 data_classification 初始值；
- 创建 Admission Record；
- 对接受的输入创建不可变 Request 和唯一 Root Run；
- 对拒绝的输入只保存最小 Admission Record；
- 生成 correlation_id、causation_id 和 trace_id。

事件、Schedule、World State Condition 和 Semantic Pulse Proposal 同样进入 Admission，不能直接创建特权执行旁路。

### 3.3 Shadow Core

Core 只保留无法外包而不破坏长期连续性的职责。

#### Conversation

管理 Conversation 与不可变 Message 的关系、顺序、归属和保留策略。UI 渲染格式、Prompt 拼接和模型 token layout 不属于该模块。

#### Run / Task Orchestrator

管理 Request、Root Run、Execution Attempt、Durable Task、Checkpoint、等待条件、取消和恢复。Runtime 内部 Planner、Subagent 和 Tool Loop 不进入 Shadow Task 模型。

#### Execution Dispatch

将统一 Execution Requirements 绑定到具体 Execution Target，并记录 Binding、Attempt、Result、Failure 和 Usage。高级分类和评分可以外置，但最终 Binding 由 Core 校验并提交。

#### Context Authority

根据 Owner、Space、数据等级、Model Binding、Capability Envelope 和当前任务裁剪允许披露的上下文。它决定“哪些数据可以被发送”，但不规定 Runtime 如何组织 Prompt。

#### Memory Authority

管理 Canonical Memory 的身份、版本、来源、Scope、状态、纠正、合并、删除和提交。Memory Intelligence 只能提出 Candidate 或 Recall Result。

#### World State Authority

接收 Observation Proposal，执行确定性来源规则、TTL 和状态转换，提交 Accepted Projection。复杂冲突融合由外部 Resolver 提议。

#### Action Authority

管理 Action Proposal、Policy、Approval、Capability Envelope、Action、幂等键、结果和 reconciliation。任何具有现实副作用的执行必须经过此边界。

#### Asset / Integration / Adapter Registry

统一管理 Skill、Executable Asset、Extension、Integration、MCP Connection、Runtime Profile、Model Profile、Provider Binding、Adapter Manifest、版本、配置、Secret Reference 和健康状态。

#### Migration / Export / Erasure

管理 Schema Version、Migration Intent、标准导出、完整备份元数据、完整性验证和 Erasure Request。具体物理迁移、备份和删除由 Store 或 Adapter 执行。

### 3.4 Execution Plane

Execution Plane 负责完成工作，不拥有 Shadow 的权威状态。完整架构支持五类 Execution Mode：

| Execution Mode | 适用情况 | 典型实现 |
|---|---|---|
| agent_runtime | 开放式、多步骤、需要工具循环 | Codex 类 SDK、Agent Harness |
| direct_model | 分类、提取、总结、判断 | 单次模型调用 |
| deterministic_program | 脚本、函数、固定算法 | Runner / Sandbox |
| workflow | 明确步骤、等待和补偿流程 | 外部 Workflow Engine |
| capability_provider | 外部账户、设备和现实动作 | API、MCP、设备 Provider |

Workflow 是完整架构允许的 Target，但 Shadow 不自研通用 Workflow Engine。一个 Workflow 的长期身份和结果可以与 Run / Durable Task 关联，其私有节点状态仍属于外部实现。

## 4. 统一执行模型

所有被接受的输入首先创建 Root Run，随后才选择执行方式。

~~~mermaid
flowchart LR
    INPUT["Chat / Voice / API / Event / Schedule"]
    ADM["Admission"]
    REQ["Immutable Request"]
    RUN["Root Run"]
    REQUIRE["Execution Requirements"]
    ROUTE["Static Rule or Route Proposal"]
    BIND["Validated Execution Binding"]
    ATTEMPT["Execution Attempt"]
    TARGET{"Execution Mode"}
    RESULT["Result / Proposal / Failure"]
    COMMIT["Shadow Authority Commit"]

    INPUT --> ADM
    ADM -->|accepted| REQ --> RUN --> REQUIRE
    REQUIRE --> ROUTE --> BIND --> ATTEMPT --> TARGET
    TARGET -->|agent_runtime| RESULT
    TARGET -->|direct_model| RESULT
    TARGET -->|deterministic_program| RESULT
    TARGET -->|workflow| RESULT
    TARGET -->|capability_provider| RESULT
    RESULT --> COMMIT
~~~

### 4.1 Execution Requirements

稳定字段表达目标约束，而不是具体厂商参数：

- required_capabilities；
- locality；
- maximum_data_classification；
- latency_class；
- budget；
- determinism；
- side_effect_level；
- tool requirements；
- checkpoint / resume requirements；
- output schema；
- user-selected target（可选）。

### 4.2 Execution Binding

Execution Binding 是独立的 Canonical Record，记录一次经过校验的实际选择：

- binding_id；
- run_id / task_id；
- execution_mode；
- target_ref 和 adapter_ref；
- target version；
- capability envelope ref；
- model / provider profile ref；
- policy version；
- created_by；
- effective_at 和 expires_at；
- route proposal ref（可选）。

Binding 一旦被 Attempt 使用便不可覆盖。Fallback、重试或切换 Target 创建新 Binding 或新版本关系。

### 4.3 Capability Envelope

Capability Envelope 是一次执行的最小授权结果，至少包含：

- subject 和 space；
- target identity；
- 允许访问的数据等级和资产范围；
- 允许调用的 Capability；
- 副作用等级；
- 预算和资源限制；
- 有效期；
- approval references；
- policy version；
- revocation status。

Runtime 可以在 Envelope 内自由规划；跨越 Adapter、预算、数据或副作用边界必须返回 Shadow 重新授权。

### 4.4 Proposal / Result 规则

外部组件只能返回以下类型：

- Result：执行结果；
- Proposal：请求 Shadow 创建或更新 Canonical State；
- Observation：来源对现实状态的报告；
- Progress：非权威进度；
- Failure：结构化失败；
- Checkpoint Reference：外部私有状态引用；
- Usage：成本和资源记录。

所有 Proposal 必须携带 proposer、source evidence、schema version、confidence（如适用）和 idempotency information。Proposal 不等于已经提交。

## 5. Adapter Control Plane

Adapter 体系是统一的用户能力资产管理机制，而不是每种组件各自设计安装方式。

### 5.1 通用 Adapter Contract

每个 Adapter 必须提供：

- manifest；
- adapter_id、type 和 version；
- contract_versions；
- capability declarations；
- configuration schema；
- secret references；
- data boundary；
- health / readiness；
- lifecycle hooks；
- compatibility report；
- migration hooks（如需要）；
- structured errors；
- idempotency support；
- contract-test metadata。

### 5.2 Adapter 类型

完整架构定义以下 Port Family：

- Durable Store；
- Agent Runtime；
- Model Worker；
- Deterministic Runner；
- Workflow；
- Routing；
- Memory Intelligence；
- State Source / Asset Source；
- State Resolver；
- Capability Provider；
- Interaction Endpoint；
- Secret Store；
- Artifact / Blob Store；
- Search / Index；
- Scheduler / Clock；
- Telemetry。

Port Family 可以拥有可选 Capability，不应把所有功能塞进一个巨型基础接口。Core 先协商 Contract Version 与 Capability，再建立 Binding。

### 5.3 运行位置

Contract 不固定 Adapter 的部署方式。Adapter 可以：

- 与 Shadow 同进程；
- 在受控子进程中；
- 在本机独立服务中；
- 在容器或隔离环境中；
- 通过远程 API 提供。

Manifest 声明 trust_level、transport、isolation requirement 和 data locality。部署方式改变时，Domain Contract 不变。

### 5.4 替换流程

~~~mermaid
flowchart LR
    INSTALL["Install / Register"]
    VERIFY["Verify Manifest & Contract"]
    CONFIG["Configure + Secret Reference"]
    TEST["Health + Contract Test"]
    SHADOW["Create Candidate Binding"]
    MIGRATE["Migrate or Rebuild Derived State"]
    SWITCH["Atomic Binding Switch"]
    OBSERVE["Observe / Roll Back"]
    RETIRE["Retire Old Adapter"]

    INSTALL --> VERIFY --> CONFIG --> TEST --> SHADOW
    SHADOW --> MIGRATE --> SWITCH --> OBSERVE
    OBSERVE -->|healthy| RETIRE
    OBSERVE -->|failure| SWITCH
~~~

替换 Runtime、Memory Engine、模型或 Store 时，旧组件不得成为读取 Canonical State 的唯一入口。Store 替换需要导出、导入、完整性验证和 Binding 切换；派生索引优先重建。

## 6. 数据架构

### 6.1 三类数据

| 类别 | 权威归属 | 示例 | 可否重建 |
|---|---|---|---|
| Canonical State | Shadow Domain | Message、Run、Task、Memory、World State、Binding、Action | 不应依赖重建 |
| Derived State | 外部组件或基础设施 | Embedding、Index、Cache、Ranking、Materialized View | 应可重建 |
| External Source Asset | 原始来源系统 | Notion 页面、邮件、日历、设备历史 | Shadow 默认只保存引用 |

Shadow 定义 Canonical Schema 和迁移语义；Store Adapter 负责物理持久化。Canonical State 可以存放在本地或远程数据库，权威性由 Primary Store Binding 决定，而不是由物理位置决定。

### 6.2 Canonical Commit

Canonical Commit 必须满足：

- 校验 owner_ref、space_id 和 data_classification；
- 校验对象版本和合法状态转换；
- 使用幂等键避免重复提交；
- 记录 actor、causation 和 correlation；
- 同时产生最小 Domain Event Envelope；
- 不把外部组件私有状态复制进 Domain Record。

Domain Event 用于通知、派生视图、审计引用和可选 Outbox，不要求采用 Event Sourcing。当前状态仍由 Canonical Record 表达。

### 6.3 最小 Domain Event Envelope

~~~text
event_id
event_type
schema_version
occurred_at
recorded_at
subject_ref
owner_ref
space_id
correlation_id
causation_id
aggregate_ref
payload_ref | minimal_payload
data_classification
retention_policy_ref
~~~

Event Payload 必须遵循最小披露原则。高敏感原文不应为了审计被重复复制到多个事件中。

### 6.4 一致性模型

- 同一 Aggregate 内的合法状态转换要求强一致提交。
- Observation 接收与 World State Projection 更新是可恢复的两阶段流程，不强迫跨 Adapter 分布式事务。
- 外部 Action 使用幂等键、Action Ledger 和 reconciliation，不假设 exactly-once。
- 派生索引采用最终一致。
- 跨模块工作由 OperationJob 或 Durable Task 跟踪，而不是持有长数据库事务。
- Primary Store 不可用时进入 restricted mode。

## 7. 关键数据流

### 7.1 对话与执行

~~~mermaid
sequenceDiagram
    participant UI as Interaction Client
    participant A as Admission
    participant C as Conversation
    participant O as Orchestrator
    participant X as Context Authority
    participant D as Dispatcher
    participant T as Execution Target
    participant S as Canonical Store

    UI->>A: input + endpoint context
    A->>S: Admission / Request / Root Run
    A->>C: append immutable Message
    O->>X: request authorized context
    X-->>O: filtered context references
    O->>D: Execution Requirements
    D->>S: validated Binding + Attempt
    D->>T: execute with Capability Envelope
    T-->>D: Result / Proposal / Usage
    D->>S: Attempt and Run transition
    O-->>UI: streamed and final response
    O->>C: append assistant Message
~~~

流式 token 可以作为临时传输数据；最终 Message、Result 摘要和 Run 状态按策略提交。UI 断开不应自动取消 Run。

### 7.2 Memory

~~~mermaid
sequenceDiagram
    participant SCH as Scheduler / Trigger
    participant MC as Memory Coordinator
    participant MI as Memory Intelligence
    participant MA as Memory Authority
    participant DS as Durable Store
    participant IX as Derived Index

    SCH->>MC: memory maintenance trigger
    MC->>MI: authorized source references
    MI-->>MC: Memory Candidates / Recall Result
    MC->>MA: validate candidates
    MA->>DS: commit Memory + immutable MemoryVersion
    DS-->>MA: commit result
    MA-->>IX: domain event / rebuild request
~~~

Memory Intelligence 替换后，Memory 与 MemoryVersion 继续存在；Embedding、Graph 和 Ranking 可以重建。周期整理由 Shadow 调度，但整理算法不由 Core 实现。

### 7.3 World State

~~~mermaid
sequenceDiagram
    participant SRC as State Source
    participant WA as World State Authority
    participant SR as Optional Resolver
    participant DS as Durable Store
    participant TR as Trigger Evaluator

    SRC-->>WA: Observation Proposal
    WA->>DS: persist Observation by retention policy
    alt deterministic resolution
        WA->>DS: commit accepted projection
    else semantic conflict
        WA->>SR: conflict candidates
        SR-->>WA: Projection Proposal
        WA->>DS: validate and commit projection
    end
    DS-->>TR: projection changed event
    TR-->>WA: condition match proposal
~~~

Condition 命中后必须重新进入 Admission 创建 Run 或 Durable Task Proposal，不能由 World State 模块直接调用现实 Provider。

### 7.4 外部 Action

~~~mermaid
sequenceDiagram
    participant R as Runtime / User
    participant AA as Action Authority
    participant P as Policy / Approval
    participant DS as Durable Store / Outbox
    participant PR as Provider Adapter

    R-->>AA: Action Proposal
    AA->>P: validate schema, risk and permission
    P-->>AA: approved / denied / needs user
    AA->>DS: commit Action + idempotency key
    AA->>PR: execute authorized action
    PR-->>AA: success / failure / unknown
    AA->>DS: commit outcome
    opt unknown outcome
        AA->>PR: reconcile
        PR-->>AA: evidence
        AA->>DS: commit reconciled outcome
    end
~~~

高风险 Action 必须在调用 Provider 前拥有持久记录。Store 故障时默认禁止副作用；只有预配置紧急能力可以使用可靠 Outbox。

## 8. 可靠性与恢复

### 8.1 失败分类

统一错误至少区分：

- invalid_request；
- policy_denied；
- capability_unavailable；
- adapter_incompatible；
- target_failed；
- timeout；
- cancelled；
- cancellation_unknown；
- store_unavailable；
- external_outcome_unknown；
- migration_failed；
- integrity_failed。

错误必须标记 retryable、safe_to_retry、user_action_required 和 external_reference。

### 8.2 幂等与重试

- Admission 使用 client_request_id 或生成的幂等键。
- 同一 Request 只创建一个 Root Run。
- 每次重试创建新 Execution Attempt，不覆盖历史。
- Provider Action 的幂等键独立于 Run 重试。
- 无法确认取消或副作用结果时使用 unknown 状态，不伪造成功或失败。
- 重启后由租约、超时和 reconciliation 恢复，不依赖模型判断。

### 8.3 Primary Store 故障

restricted mode 允许：

- 明确标记的只读查询；
- 不承诺保存的临时交互；
- 健康检查和恢复操作。

restricted mode 禁止：

- 新 Canonical Commit；
- 普通 Durable Task 状态推进；
- 默认现实副作用；
- 声称未持久化工作已经安全完成。

## 9. 安全与信任边界

完整架构不把安全能力委托给模型。

稳定执行点包括：

- Owner / Space 边界；
- public、personal、sensitive、restricted 数据等级；
- Adapter trust level；
- Model / Provider Data Boundary；
- Secret Reference；
- Capability Envelope；
- Approval；
- Retention 和 Erasure；
- Audit / Action Ledger。

未知数据默认 sensitive。外部分类器可以建议提高保护等级，不能自行降低。Secret 内容不进入普通 Canonical Record、日志或标准导出。

第三方 Adapter 默认是不可信执行边界。它只能获得当前 Binding 和 Envelope 允许的最小数据、Secret Reference 解析结果和 Capability。

## 10. 部署演进

### 10.1 参考部署原则

完整逻辑架构不要求微服务。推荐演进路径：

1. 模块化单体：Core、API、调度协调和本地 Adapter Host 同进程；
2. 隔离 Worker：Runtime、Runner、Memory Engine 或语音组件使用子进程；
3. 本机多服务：资源密集组件独立运行；
4. 多设备 Endpoint：Web、语音和设备节点通过稳定 API 接入；
5. 可选远程基础设施：远程 Store、模型和 Provider；
6. 只有出现明确可靠性或规模证据后，才引入队列、集群和服务拆分。

模块依赖方向保持不变：

~~~text
Interaction
    -> Application / Admission
        -> Domain Core
            -> Port Contracts
                <- Adapters
                    <- External Implementations
~~~

Domain Core 不能依赖具体 SDK、ORM Model、Web Framework、数据库驱动或 Provider Client。

### 10.2 模块拆分触发条件

只有满足以下证据之一才拆进程或服务：

- 不可信代码需要安全隔离；
- Runtime 或模型任务需要独立资源调度；
- 组件故障会拖垮 Core；
- 组件需要独立升级节奏；
- 多设备部署需要网络边界；
- 可靠吞吐量超过单进程能力。

“未来可能需要”不是拆分理由。

## 11. 完整性规则

后续实现和评审必须满足：

1. 不建立绕过 Admission 的执行入口。
2. 不建立绕过 Authority 的 Canonical State 写入入口。
3. 不允许 UI、Runtime、Memory Engine、Resolver 或 Provider 成为唯一事实源。
4. 不把某个外部 SDK 的对象直接作为 Canonical Schema。
5. 不因第一阶段未实现某模块而删除其稳定扩展点。
6. 不因完整架构包含某模块而提前实现没有用例支撑的内部复杂度。
7. 新 Adapter 通过 Capability Negotiation 扩展，不随意扩大基础接口。
8. 所有 Canonical Asset 从第一版携带 owner_ref、space_id、schema_version 和生命周期信息。
9. 所有现实副作用具有 Action ID、幂等信息和可见结果。
10. 所有派生状态都能说明如何从 Canonical State 或外部来源重建。

## 12. 已冻结的 Stage 4 架构决定

1. 完整逻辑架构由 Interaction、Access、Core、Execution、Adapter、Canonical State 和 Infrastructure 边界组成。
2. 完整逻辑模块不强制微服务，默认以模块化单体起步。
3. Web 是第一客户端，但 Core 通过稳定 API 支持未来多端和语音端点。
4. 所有触发统一进入 Admission；被接受的输入创建唯一 Root Run。
5. Execution Mode 统一支持 Agent Runtime、Direct Model、Deterministic Program、Workflow 和 Capability Provider。
6. Execution Binding 与 Capability Envelope 是独立、版本化的 Canonical Record。
7. Shadow Core 管理权威状态；外部组件只返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage。
8. Adapter 采用统一 Manifest、Capability Negotiation、Version、Health、Data Boundary 和 Contract Test 机制。
9. Adapter Contract 不固定同进程、子进程、本机服务、容器或远程 API。
10. Canonical State、Derived State 和 External Source Asset 明确分离。
11. Domain Event 使用最小信封，但不要求 Event Sourcing。
12. Store 内聚合状态转换强一致；跨 Adapter 流程使用幂等、状态机和 reconciliation。
13. System Health、Lease、Timeout、TTL 和恢复路径保持确定性，不依赖模型。
14. 完整目标架构先冻结，功能按阶段实现；任何阶段都不得创建与目标架构冲突的旁路。

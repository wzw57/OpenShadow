# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 是一个可以长期存在、持续升级的个人 AI。**

OpenShadow 是一个本地优先、实现无关的个人 AI 资产与能力平台。用户始终在使用同一个 Shadow；Agent Runtime、模型、Memory Intelligence、Runner、Router、数据库、Provider、语音和其他能力都是 Shadow 内部可替换的组成部分。

Shadow 的目标不是重新实现所有 AI 基础设施，而是用尽可能小且稳定的 Core，将外部优秀项目组合成一个能够长期积累和复用用户资产、理解当前现实状态的完整 Agent。

## 产品组成

~~~text
Shadow
├─ Shadow Core
│  ├─ Domain Contracts
│  ├─ Authority & State Transition
│  ├─ Task Continuity
│  ├─ World State
│  ├─ Execution Dispatch
│  ├─ Extension / Integration Registry
│  └─ Portability & Upgrade
│
├─ Replaceable Components
│  ├─ Agent Runtime / Model Workers
│  ├─ Deterministic Runners / Routers
│  ├─ Memory Intelligence / Durable Store
│  ├─ Search / Index / Skill System
│  ├─ Asset and State Source Connectors
│  ├─ Capability Providers
│  └─ Voice / User Interfaces
│
└─ User-owned Assets
   ├─ Tasks / Runs / Checkpoints
   ├─ Canonical Memories / World State
   ├─ Owner / Personal Space / Home Space
   ├─ Skills / Executable Assets
   ├─ Extensions / Integrations
   ├─ Asset Catalog / Artifacts
   └─ Policies / Action History
~~~

Shadow 是完整产品；Shadow Core 只是其中必须长期稳定的最小内核。

## 核心原则

> **所有请求都经过 Shadow，但不必都经过 Agent Runtime。**

每个被 Shadow 接受的 Request 形成一个 Root Run；准入失败只形成最小 Admission Record。Shadow 根据明确的 Execution Binding，将工作交给 Agent Runtime、单次 Model Worker、Deterministic Runner 或 Capability Provider。完整输入、输出和工具过程是否长期保存，由用户策略和产生的长期价值决定。需要跨 Session、执行目标或时间继续存在的工作才成为 Durable Task。

> **Shadow owns assets, continuity, current state and authority.**

属于用户的长期资产、任务连续性、当前状态和最终提交权不能被某个 Runtime、Memory Engine、模型、数据库私有格式或 Provider 独占。

> **Replaceable components own intelligence and execution.**

推理、规划、路由、Memory 提取与整理、检索、脚本运行、语音、设备协议和具体外部执行优先复用可替换组件。

> **Adapter 是稳定架构的一部分。**

Shadow 自己定义 Port Contract、Adapter SDK、Extension Manifest、权限、版本协商和 Contract Test；具体 Adapter 与外部实现可以持续替换。

## World State 与现实同步

Shadow 维护一个最小 World State，用来表达“当前认为现实是什么状态”，而不是建立完整数字孪生。

~~~text
Calendar / Weather / Device / Location / User
                     ↓
          Replaceable Source Adapter
                     ↓
       Observation Proposal + timestamp + TTL
                     ↓
          Shadow validates and commits
                     ↓
      World State: fresh / stale / unknown
~~~

外部系统负责采集和保存领域数据；Shadow 只保存通用的状态投影、来源、时间、有效期和关系。Source Adapter 不能直接改写权威状态。Shadow 不要求实时读取所有外部系统，而是在需要时刷新，并诚实表达 stale 或 unknown。

World State 与 Memory 不同：Memory 是长期历史知识，World State 是带时效性的当前判断；Event 表示发生过什么，Task 表示未来承诺。

Accepted World State 属于可迁移的 Canonical State。Shadow 保存当前投影、冲突候选、证据和过期原因；Observation 按类型保留。用户明确陈述优先，但更新、更可靠的 Observation 可以替换它。复杂融合由外部 State Resolver 返回 Proposal。

## 灵活执行平面

Shadow 支持四类可替换 Execution Target：

| Target | 用途 |
|---|---|
| Agent Runtime | 开放式、多步骤、需要规划或工具循环 |
| Model Worker | 分类、提取、总结等一次受限推理 |
| Deterministic Runner | 脚本、函数和固定程序 |
| Capability Provider | 外部 API、账户、设备和现实动作 |

Core 负责准入、权限、预算、Binding、状态与结果记录。高级任务分类、多模型评分和动态选择由外部 Routing Component 提议；Core 只校验并接受或拒绝。早期版本可以使用用户显式选择和静态规则。

脚本作为 Executable Asset 长期登记其身份、版本、输入输出、依赖、权限、来源和校验信息；实际语言运行时、依赖解析、隔离和执行由 Runner 提供。

Runtime 在 Shadow 签发的 Capability Envelope 内拥有执行自由；越过数据、能力、资源、副作用、预算或有效期边界时必须重新授权。Shadow 不保存 Runtime 私有推理，但记录跨 Adapter、预算和副作用边界的最小 Usage / Action Record。

## Heartbeat 与 Semantic Pulse

系统健康心跳必须是确定性的：进程检查、Adapter 健康、租约、超时和调度 tick 不依赖任何模型。

可以额外接入一个很小的模型作为 Semantic Pulse，周期性观察授权范围内的 Event、World State 和近期活动，提出 Recall、状态更新、Run、Durable Task 或升级到更强模型的建议。但它只能提出 Proposal，不能直接提交权威状态，也不能成为 Shadow 正确运行的前提。

## Memory 边界

用户在长期使用中形成的 Canonical Memory 属于 Shadow，必须在更换 Memory Intelligence 后继续存在。

~~~text
Conversation / Task / External Source
                 ↓
       Replaceable Memory Intelligence
                 ↓
          Memory Candidate
                 ↓
       Shadow validates and commits
                 ↓
      Primary Durable Store Adapter
                 ↓
       Replaceable Database Engine
~~~

Shadow Core 持有 Memory 的稳定身份、来源、Scope、版本和提交语义；外部组件负责 Extraction、Consolidation、Retrieval、Reranking、Embedding、Graph 和其他快速演进的智能能力。

数据库引擎也不是 Shadow 自研能力。Shadow 定义 Durable Store Port、Canonical Record、迁移和导出语义，具体数据库通过 Adapter 接入。

## 外部信息与能力资产

Shadow 不负责复制和长期保存用户所有外部资料。对于 Notion、Obsidian、Drive、Email、文件系统等来源，Asset Catalog 默认只记录资产存在性、位置、Integration、可用性和来源关系；需要时才通过 Connector 读取。

用户长期积累的不只是数据，还包括能力：

~~~text
Capability Assets
├─ Skills / Executable Assets
├─ Extensions / Integrations
├─ MCP connections
├─ Provider bindings
├─ Runtime / Model / Runner profiles
└─ Configuration / permission metadata
~~~

这些资产应具有稳定身份、版本、来源、配置、权限、兼容性和迁移信息，使用户切换模型、Runtime 或设备后仍能复用已有能力。

## 长期治理、本地优先与故障边界

每个 Canonical Asset 从第一版起具有显式 Owner 和 Space。Owner 可以是 User 或 Space；个人资产归 User，公共房间和家庭设备状态可以归 Home Space。近期只实现默认 Personal Space 和隐式 Home Space，不开发成员、角色和共享功能。

Core 执行 public、personal、sensitive、restricted 四级数据约束；无法判断时默认 sensitive。Model Binding 必须声明允许的数据等级、Memory / World State / 外部资产边界，以及 retention、training 和地域限制。外部分类器可以提高保护等级，不能自行降低。

用户删除 Canonical Memory 时默认先逻辑删除，之后可以物理清除；纠正默认保留版本关系，但敏感历史允许彻底擦除。统一 Erasure Request 追踪各 Adapter 的删除状态，无法确认时显示 pending 或 unreachable。

“本地优先”表示用户控制、可迁移和可验证，不把物理位置写死。标准导出不包含 Secret 和可重建状态；完整设备备份可以在独立授权和加密后包含 Secret、Checkpoint 和部分派生状态。

Primary Durable Store 不可用时，Shadow 允许明确标记的只读和临时交互，但暂停 Canonical Commit，默认禁止现实副作用。只有预先配置的紧急能力可以先写入可靠的本地持久 Outbox，再执行并在恢复后 reconciliation。

## 当前边界

OpenShadow 不自研数据库、通用 Agent Loop、基础模型、智能路由算法、Memory Intelligence、向量数据库、知识图谱、脚本运行时与沙箱、语音引擎、浏览器 Agent、Coding Agent、设备协议栈或领域数字孪生。

OpenShadow 必须自行定义和实现：

- Shadow Domain Contracts；
- 权威状态提交边界；
- Task / Run 连续性；
- 最小 World State、Observation、Owner 与 Space 语义；
- Data Classification、Retention 与 Erasure 语义；
- Capability Envelope；
- Execution Dispatch 与 Binding；
- Adapter SDK 与 Extension Registry；
- Integration / Capability Binding；
- 权限执行点；
- 可移植数据格式；
- 兼容性、迁移和完整性验证；
- 用户控制 API。

近期实现以单用户场景为主，但核心 Contract 不封死未来多用户和多设备可能性。

## 文档

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [Core / External 责任矩阵](docs/responsibility-matrix.md)
- [关键用例](docs/use-cases/README.md)
- [领域模型](docs/domain-model.md)
- [状态机基线](docs/state-machines.md)
- [完整技术架构](docs/technical-architecture.md)
- [分阶段实现计划](docs/implementation-stages.md)
- [开发路线](docs/roadmap.md)
- [架构决策记录](docs/adr/README.md)

## 当前状态

**Stage 3 领域模型已经收紧，Stage 4 正在形成完整技术架构与分阶段实现基线。**

Stage 4 不把 MVP 当作架构边界。完整目标架构已经定义 Interaction、Access、Core、Execution、Adapter、Canonical State 与 Infrastructure 平面，以及统一执行模型、关键数据流和部署演进；实现按照 Phase 0–5 逐步交付，每个阶段都是同一目标架构的真子集。

# OpenShadow 需求基线

- 状态：需求收紧 / Core 与 External 边界设计前
- 目标：描述已经确认的产品行为和长期约束
- 非目标：本文件不选择具体 Runtime、Memory 项目、数据库或其他实现

## 1. 产品定义

OpenShadow 是一个本地优先、Runtime 无关的个人 AI 资产与能力平台。

用户面对的是统一的 Shadow Agent。Runtime、Memory Intelligence、数据库、搜索、Skill System、Provider、语音和交互界面都是 Shadow 的组成部分，但不必属于 Shadow Core。

Shadow 需要让用户在长期使用中持续积累和复用：

- Tasks、Runs 与 Checkpoints；
- Canonical Memories 与 Evidence References；
- Skills；
- Extensions、Integrations 和 MCP Connections；
- Asset Catalog；
- Artifacts；
- Policies、Approvals 和 Action History。

模型、Runtime 和外部组件可以不断升级，上述用户资产不能因此丢失。

## 2. 术语

### 2.1 Shadow

用户使用的完整 Agent 产品，包括 Core 和全部可替换组件。

### 2.2 Shadow Core

Shadow 中必须长期稳定的最小部分，负责 Domain Contract、权威状态、任务连续性、扩展管理和可移植性。

### 2.3 Runtime

Shadow 内部负责推理、规划、Subtask、Subagent、Tool Loop 和具体执行的可替换组件。

### 2.4 External Component

通过 Adapter 接入 Shadow 的数据库、Memory Intelligence、Search、Provider、Model、Voice、Storage 或其他实现。

“External”表示实现边界，不表示它在 Shadow 产品之外或用户需要单独使用。

### 2.5 Canonical Asset

由 Shadow 持有稳定身份、语义、来源、Scope、版本和生命周期的用户长期资产。

### 2.6 Derived State

可以由 Canonical Asset 重建的索引、Embedding、Graph、Summary、Projection、Cache 或 Runtime-specific State。

### 2.7 Observation

外部来源对现实状态的一次带来源和时间信息的报告。Observation 是 Proposal，不等于 Shadow 已接受的当前状态。

### 2.8 World State

Shadow 当前认为与判断和行动相关的现实状态投影。World State 具有来源、时效和过期语义，不试图复制整个外部世界。

### 2.9 Execution Target

能够执行 Shadow Run 的可替换目标，包括 Agent Runtime、Model Worker、Deterministic Runner 和 Capability Provider。

### 2.10 Executable Asset

可以被 Shadow 长期登记、版本化和授权执行的脚本、函数或固定程序。

## 3. 已确认的设计原则

### R-001 所有请求经过 Shadow

Chat、CLI、API、Voice、Event 和 Schedule 产生的请求统一由 Shadow 准入、绑定和调度。

每个请求至少保存最小 Run 记录。完整内容是否长期保留，由用户策略和是否产生 Memory、Artifact、Action 或 Durable Task 决定。

### R-002 Shadow 统一长期身份

用户切换 Runtime、模型、设备或交互入口时，仍然是在使用同一个 Shadow。

### R-003 用户资产独立于组件

任何 Runtime、Memory Engine、数据库私有格式或 Provider 都不能成为用户长期资产不可迁移的唯一所有者。

### R-004 智能与权威分离

外部组件可以提供推理、提取、整理、检索、验证和执行，但权威状态只能通过 Shadow 的 Contract 和提交边界改变。

### R-005 实现优先复用

数据库、Agent Runtime、Memory Intelligence、Search、Graph、Voice、Model 和 Provider 优先采用可插拔外部实现。

### R-006 小而稳定的 Core

Core 只保留不能外包而不破坏资产所有权、连续性、权威或升级能力的语义与控制。

### R-007 Adapter 是一等能力

Shadow 必须提供稳定 Port、Adapter SDK、Manifest、权限、版本协商、健康检查和 Contract Test。

### R-008 长期可升级

Shadow 需要支持数据版本、兼容性检查、迁移、导出、导入、备份元数据和完整性验证。

### R-009 单用户优先

近期只开发单用户场景。核心 Contract 不依赖不可移除的全局单用户假设，但暂不开发完整多用户功能。

### R-010 所有执行经过 Shadow，但不都经过 Agent Runtime

Shadow 根据任务特征将 Run 绑定到 Agent Runtime、Model Worker、Deterministic Runner 或 Capability Provider。固定脚本和单次模型推理不需要启动 Agent Loop。

### R-011 健康心跳必须确定性

进程健康、Lease、Timeout 和 Scheduler Tick 不依赖模型。小模型可以作为可替换的 Semantic Pulse 提出状态、Recall、Run 或 Task Proposal，但不能成为系统正确运行的必要条件。

## 4. 功能需求

### 4.1 Request 与 Run

Shadow 必须：

- 接收用户请求、外部 Event 和 Schedule Trigger；
- 为每次执行创建稳定 Run 标识；
- 记录最小 Run 元数据；
- 根据配置绑定 Runtime 和所需组件；
- 支持取消、失败和完成；
- 将有长期价值的结果晋升为 Memory、Artifact、Action 或 Durable Task。

最小 Run 记录用于连续性和审计，不要求永久保存完整对话、Prompt、模型输出和工具过程。

### 4.2 Durable Task

需要跨 Session、Runtime、等待条件或长期时间存在的工作必须表示为 Durable Task。

Shadow 必须支持：

- 创建、启动、暂停、等待、恢复、取消、失败和完成；
- Deadline、Retry 和长期 Waiting；
- Runtime Binding；
- Runtime Checkpoint Reference；
- Semantic Checkpoint；
- Artifact Reference；
- Event 或 Schedule 触发恢复；
- Runtime 崩溃后的恢复；
- Runtime 切换后的继续执行；
- Shadow 对最终 Task 状态的提交。

Runtime 内部 Planner、Subtask、Subagent 和 Workflow 不要求同步为 Shadow Task。

### 4.3 Runtime 接入

Shadow 必须通过 Runtime Port：

- 启动 Run；
- 提供授权上下文；
- 查询状态和健康；
- 接收进度和结果；
- 请求 Checkpoint；
- 暂停或取消；
- 恢复 Runtime-native State；
- 接收 Completion 和 Action Proposal；
- 描述 Runtime 能力与兼容性。

Runtime 实现可以替换；Runtime Session 不能成为 Durable Task 的唯一事实源。

### 4.4 Checkpoint 与 Handoff

Shadow 必须区分：

- Runtime Checkpoint：用于同一 Runtime 的高保真恢复，可以是 opaque reference；
- Semantic Checkpoint：用于跨 Runtime、跨版本或长期恢复。

Semantic Checkpoint 需要保存继续工作所需的可验证语义，不保存隐藏思维过程或模型内部状态。

### 4.5 Asset Catalog

Shadow 必须掌握用户有哪些外部信息资产，但默认不复制和长期保存外部原始内容。

Asset Catalog 需要保存：

- 稳定 Asset ID；
- 类型和来源；
- 外部引用；
- Integration Binding；
- 可用状态；
- 基本版本或更新时间信息；
- Scope 和访问边界；
- 与 Shadow Memory、Task 或 Artifact 的来源关系。

外部资料的原始存储、备份、版本历史和生命周期仍由来源系统负责。

### 4.6 外部信息访问

Shadow 必须通过 Source Connector 按需访问外部资料。

访问可以由以下情况触发：

- 当前 Task 明确需要；
- Runtime 发出受授权的 Recall 或 Resource Request；
- 用户明确请求；
- 后台 Memory 整理任务。

Shadow 不要求实时同步全部外部知识库。

### 4.7 Canonical Memory

长期使用中形成的用户 Memory 属于 Shadow。

Canonical Memory 必须具有：

- 稳定身份；
- 内容或 Claim；
- 来源；
- Scope；
- 有效性和状态；
- 版本；
- Create、Update、Merge、Supersede 和 Delete 语义；
- 用户查看、修正和删除能力。

更换 Memory Intelligence 后，Canonical Memory 必须继续存在。

### 4.8 Memory Intelligence

Memory 的 Extraction、Consolidation、Retrieval、Reranking、Embedding、Graph、Summary 和其他智能能力通过可替换组件提供。

Shadow 必须：

- 触发按需或周期性 Memory 整理；
- 决定哪些数据可以交给 Memory Component；
- 接收 Memory Candidate；
- 通过权威提交边界更新 Canonical Memory；
- 在 Recall 结果进入 Runtime 前执行 Scope 和权限控制；
- 允许删除并重建派生 Memory State。

当前需求只要求 Adapter Contract 不阻止未来组合多个 Memory Component，不要求现在实现动态组合、路由或结果融合。

### 4.9 Durable Store

Shadow 必须通过 Durable Store Port 保存 Canonical State。

Shadow 自己定义：

- Canonical Record；
- Stable ID；
- Schema Version；
- Migration Semantics；
- Export / Import；
- Integrity Verification。

具体数据库引擎、事务实现、查询执行、复制和物理备份由可替换存储实现负责。

在没有可用 Durable Store 时，Shadow 不承诺持久状态继续存在。

### 4.10 Skill

Shadow 必须将 Skill 作为用户长期能力资产管理，包括：

- Canonical Source 或稳定来源引用；
- 版本；
- Provenance；
- Trust；
- Scope；
- Compatibility；
- Runtime Projection 记录；
- Import、Export 和 Migration 信息。

Skill 的 Discovery、Activation、Composition 和 Execution 可以由 Runtime 或可替换 Skill Component 负责。

### 4.11 Extension、Integration 与 Capability

Shadow 必须区分：

- Extension：提供实现代码的软件包；
- Integration：已配置的外部连接；
- Skill：可复用的方法和经验；
- Capability：稳定的动作或查询语义；
- Provider Binding：Capability 当前由哪个实现提供。

Extension 和 Integration 是用户长期能力资产。Shadow 必须保存其稳定身份、类型、版本、来源、配置、权限、兼容性、健康状态和 Secret Reference。

Secret 内容不进入普通资产导出。

### 4.12 Capability 与外部动作

涉及长期凭证、私密数据、外部账户、费用、持续承诺或现实副作用的动作必须进入 Shadow 的治理路径。

Shadow 必须提供：

- Capability Contract；
- Schema Validation；
- Policy Enforcement Point；
- Approval 状态；
- Action ID 和 Idempotency 信息；
- Provider Binding；
- Action Ledger；
- Success、Failure 和 Unknown Outcome；
- Reconciliation 语义。

具体 Provider 和协议实现通过 Adapter 接入。

### 4.13 Event、Observation 与 World State

Shadow 必须区分：

- Event：已经发生的重要事实；
- Observation：外部来源对当前状态的报告；
- World State：Shadow 当前接受的、与判断和行动相关的状态投影；
- Memory：从历史中形成的长期认知；
- Task：Shadow 承诺完成的工作。

Observation 必须携带来源、观察时间和必要的时效信息。外部组件只能提交 Observation Proposal，不能直接修改 World State。

World State 必须支持：

- Subject / Property / Value；
- Source；
- Observed Time 和 Valid Time；
- TTL / Expiration；
- Fresh、Stale、Unknown 等状态；
- Scope；
- Version；
- 与 Event、Task 和 Capability 的关系。

Shadow 只保存影响判断和行动的最小状态。Calendar、Weather、设备、位置和其他领域状态通过 State Source Adapter 接入，外部系统仍然负责其完整领域数据。

World State 可以触发 Condition、Run 或 Durable Task。复杂状态融合、预测和异常检测由可替换组件提供。

### 4.14 Execution Dispatch

所有执行由 Shadow 准入和记录，但不要求全部经过 Agent Runtime。

Shadow 必须支持以下 Execution Target：

- Agent Runtime：开放式、多步骤、需要规划的任务；
- Model Worker：单次推理、分类、提取、摘要或判断；
- Deterministic Runner：脚本、函数、固定程序和数据处理；
- Capability Provider：外部 API、设备、账户和现实动作。

Core 必须定义：

- Execution Request；
- Execution Requirements；
- Execution Binding；
- Execution Target Descriptor；
- Execution Status；
- Execution Result。

Execution Requirements 应能表达所需 Capability、隐私、本地性、预算、延迟、风险和确定性等约束。Core 负责最终 Binding、权限和 Run 状态；具体路由评分、成本预测、模型选择、Fallback 和多模型比较由可替换 Routing Component 提供。

早期实现可以使用显式配置或静态规则，不要求智能路由。

### 4.15 Model Worker 与 Routing

Shadow 必须允许不经过 Agent Loop 的直接 Model Worker。

Model Worker 通过 Model Port 接收受约束的输入并返回结构化或文本结果。模型 Provider、模型选择和推理实现可以替换。

Routing Component 只能返回 Route Proposal。Shadow 必须根据可用性、权限、预算和任务要求校验后提交 Execution Binding。

### 4.16 Executable Asset 与 Runner

需要长期复用的脚本、函数或固定程序可以登记为 Executable Asset。

Executable Asset 需要具有：

- Stable ID；
- Source 或 Source Reference；
- Version；
- Input / Output Contract；
- Runtime Requirements；
- Permission；
- Provenance；
- Trust；
- Checksum。

Shadow 管理其身份、版本、授权、Schedule / Event Binding 和执行记录。具体语言运行时、Sandbox、资源限制、依赖安装和进程隔离由可替换 Runner 提供。

### 4.17 Health Heartbeat 与 Semantic Pulse

Shadow 的 Health Check、Lease、Timeout、Queue State 和 Scheduler Tick 必须使用确定性机制。

Shadow 可以接入可替换 Semantic Pulse，通过小模型或其他低成本智能对 Event 和 World State 进行轻量分析，并提出：

- State Update Proposal；
- Recall Proposal；
- Run Proposal；
- Durable Task Proposal；
- stronger Execution Target Proposal。

Semantic Pulse 不能直接提交 World State、Task 或高风险 Action，也不能成为 Core 持续运行的必要依赖。

### 4.18 Context

Shadow 必须在调用 Runtime 前建立授权上下文边界，可能包括：

- Request / Run；
- Durable Task；
- Semantic Checkpoint；
- Relevant Memory；
- Skill Reference；
- Artifact Reference；
- State Projection；
- Policy；
- Allowed Capability。

Runtime-specific Prompt、Token Layout 和 Context Rendering 不属于稳定 Core Contract。

### 4.19 用户控制

用户必须能够：

- 查看 Run 和 Durable Task；
- 查看、修正和删除 Canonical Memory；
- 查看 Skill、Extension 和 Integration；
- 查看 Approval 和外部 Action；
- 暂停或取消工作；
- 禁用组件或撤销权限；
- 导出 Shadow 长期资产；
- 查看迁移和完整性验证结果。

### 4.20 交互便利性与未来接口

Shadow 产品需要允许通过 Chat、CLI、API 和未来的 Voice / Device Endpoint 使用。

Wake Word、STT、TTS、音频流和设备协议由可替换组件提供。近期不要求开发家庭多用户、分布式麦克风或完整语音系统，但 Core Contract 不应阻止这些接口接入。

## 5. 非功能需求

### NFR-001 长期持久性

用户长期资产应能跨 Runtime、Memory Intelligence 和其他组件升级继续使用，设计目标面向多年持续演进。

### NFR-002 可替换性

删除任何智能组件后，Canonical Asset 不得因此丢失。可重建状态允许重新生成。

### NFR-003 可移植性

Shadow 长期资产必须具有版本化、可验证、可导出的表示。

### NFR-004 本地优先

用户长期资产默认保存在用户控制的 Durable Store 中。外部云能力只能获得完成当前请求所需的数据和权限。

### NFR-005 可恢复性

Core 重启后，应能从 Durable Store 恢复已提交的长期状态。

### NFR-006 可审计性

重要状态变化和现实动作应能追踪到 Request、Task、Component、Policy、Authorization 和 Result。

### NFR-007 使用便利性

组件可替换性不能要求普通用户直接操作每个底层项目。Shadow 应提供统一入口、统一配置和统一用户控制。

### NFR-008 实现克制

不因未来可能需要某项能力而提前实现复杂路由、多组件融合、微服务、集群或完整多用户系统。

### NFR-009 状态时效性

World State 必须显式表达时效和未知状态。过期 Observation 不得被静默当作当前事实。

### NFR-010 确定性基础运行

系统健康、调度 Tick、Lease 和 Timeout 不依赖任何模型或语义智能组件。

## 6. 明确不自研的基础能力

OpenShadow 不自行开发：

- 数据库引擎；
- 通用 Agent Loop 和 Runtime Planner；
- 基础模型；
- 通用 Memory Intelligence；
- Vector Database 或 Graph Database；
- 通用 Search Engine；
- 通用 Skill Resolver；
- Browser Agent 或 Coding Agent；
- STT、TTS、Wake Word 和音频引擎；
- 家电协议栈；
- 通用 Workflow Engine；
- 通用多模型路由和模型评分系统；
- Script Runtime、Sandbox 和依赖管理器；
- 领域专用 World State 同步或 Digital Twin；
- Secret Store；
- 日志、指标或 Trace 后端。

Shadow 可以提供这些外部实现所需的 Adapter 和官方集成。

## 7. 顶层验收原则

- 所有请求由 Shadow 准入并产生最小 Run 记录；
- Runtime 更换后，Durable Task 和用户资产继续存在；
- Memory Intelligence 更换后，Canonical Memory 继续存在；
- Durable Store 可以通过导出、迁移和验证替换；
- 删除派生索引后，可以从 Canonical State 重建；
- 外部资料按需访问，不要求 Shadow 复制全部内容；
- Skill、Extension、Integration 和 MCP Connection 可以作为用户能力资产持续管理；
- 外部 Action 经过统一治理并具有可恢复记录；
- World State 能表达来源、时效、过期和未知状态；
- 简单任务可以直接绑定 Model Worker 或 Deterministic Runner，不启动 Agent Runtime；
- Semantic Pulse 删除后，系统健康和确定性调度仍然正常；
- 用户能够查看、修正、删除和导出自己的长期资产。

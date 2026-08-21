# OpenShadow 需求基线

- 状态：需求基线 / Stage 4 Core Diet 已确认
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

Shadow 中必须长期稳定的 Tiny Kernel。它负责 Identity / Ownership、Canonical Envelope 与生命周期、Proposal / Validate / Commit、工作准入与最小连续性、Extension Contract / Binding，以及 Portability / Erasure Intent。

Memory、World State、Skill、Task 等业务概念通过官方 typed Profile 表达。Profile 属于 Shadow 产品与兼容性承诺，但不要求 Tiny Core 为每一种类型建立永久硬编码模块。

### 2.3 Runtime

Shadow 内部负责推理、规划、Subtask、Subagent、Tool Loop 和具体执行的可替换组件。

### 2.4 External Component

通过 Adapter 接入 Shadow 的 Runtime、Model、Runner、Router、Memory Intelligence、State Resolver、Store、Search、Provider、Voice 或其他实现。

“External”表示实现边界，不表示它在 Shadow 产品之外。Execution / Intelligence Adapter 通过类型化 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage 交互；Store、Secret、Interaction 等基础设施 Port 使用各自的 family-specific Result。所有 Port 共享版本化 Message Envelope、Correlation、结构化错误和 Capability Negotiation，但不强行共享一个万能 Payload。

External Component 不能直接提交 Canonical State。

### 2.5 Canonical Record、Canonical Asset 与 Profile

Canonical Record 是带 Stable ID、Owner / Space、Schema Reference、Version、Provenance、Lifecycle 和 typed payload 的可迁移记录。

Canonical Asset 是用户长期拥有或控制的 Canonical Record。不是所有控制面记录都属于用户资产，例如 AdmissionRecord 和 ExecutionAttempt 是 Shadow 连续性事实。

Profile 为一类 Canonical Record 定义类型化 Schema、合法状态转换、迁移与导出语义。Memory、State、Task、Action、Skill 和 Integration 可以使用官方 Profile 演进，而不被写死成 Tiny Core 的永久模块。

### 2.6 Derived State

可以由 Canonical Asset 重建的索引、Embedding、Graph、Summary、Projection、Cache 或 Runtime-specific State。

### 2.7 Observation

外部来源对现实状态的一次带来源、时间和证据的信息。Observation 是 State Profile 接受的一类 typed Proposal / Evidence Record，不等于 Shadow 已接受的当前状态，也不是 Tiny Core 的通用实体要求。

### 2.8 World State

Shadow 当前认为与判断和行动相关的现实状态投影。它由官方 State Profile 定义 state key、source、observed_at、expires_at、fresh / stale / unknown、Evidence 与迁移规则。

Tiny Core 只提供 Canonical Envelope、通用时间有效性、Proposal / Commit 和权限机制；来源采集、冲突融合、预测、领域本体与查询全部外置。

### 2.9 Execution Target

能够处理 Shadow Run 的可替换目标。Binding 使用可扩展、带命名空间的 `target_kind` 和 Capability Declaration，不使用永久封闭枚举。

首批 well-known kinds 为 `shadow.agent-runtime`、`shadow.model-worker`、`shadow.deterministic-runner`、`shadow.workflow-target` 和 `shadow.capability-provider`。新增 Target Kind 不应要求修改 Core 主流程。

### 2.10 Executable Asset 与 SkillAsset

Executable Asset 是可被 Shadow 长期登记、版本化和授权执行的脚本、函数或固定程序。

SkillAsset 是对标准 Skill Bundle 的治理包装，不是 Shadow 自创的 Skill 内容格式。默认兼容 Agent Skills 的 `SKILL.md`、`scripts/`、`references/`、`assets/`；Shadow 只保存稳定身份、来源、固定 revision、digest、trust、权限、安装状态和 Runtime Projection。

### 2.11 Owner 与 Space

Owner 是 Canonical Asset 的长期控制主体，可以是 User 或 Space。Space 是资产归属、上下文和未来共享的稳定边界；近期只实现默认 Personal Space 和隐式 Home Space，不实现成员、角色或邀请。

### 2.12 Capability Envelope

Shadow 为一次 Run 或 Durable Task 签发的受限授权，描述 Target、能力、数据、资源、副作用、预算、有效期和撤销状态。

### 2.13 Data Classification

Shadow 用于执行数据边界的少量稳定敏感度等级：public、personal、sensitive、restricted。标签可以由用户、来源或可替换分类器提出，最终约束由 Core 执行。

### 2.14 Proposal 与 Canonical Commit

外部智能、Runtime、Router、Resolver 和 Provider 只能提交类型化 Proposal 或执行结果。Shadow 依据 Schema、Expected Version、Authority、Policy 和当前状态接受或拒绝，并由 Commit 产生新的 Canonical Version。

Proposal 未被接受前不是 Canonical State；被拒绝或过期 Proposal 是否保留由 Retention / Audit Policy 决定。

## 3. 已确认的设计原则

### R-001 所有承载工作的输入经过 Shadow

Chat、CLI、API Command、Voice、Event、Schedule、Condition 和 Semantic Pulse Proposal 等承载工作的输入统一经过 Shadow Admission、Binding 和治理。

每个被接受的工作 Request 创建一个 Root Run；准入失败只保存最小 Admission Record。健康检查、静态资源、只读控制面查询、已有 Run 的事件订阅和内部恢复步骤不创建新 Run，但仍受身份、权限和审计约束。

### R-002 Shadow 统一长期身份

用户切换 Runtime、模型、设备或交互入口时，仍然是在使用同一个 Shadow。

### R-003 用户资产独立于组件

任何 Runtime、Memory Engine、数据库私有格式或 Provider 都不能成为用户长期资产不可迁移的唯一所有者。

### R-004 智能与权威分离

外部组件提供推理、提取、整理、检索、融合和执行，只能产生类型化 Proposal 或 Result。任何长期状态变化都必须经过 Shadow 的 Schema、Authority、Policy 与 Expected Version 校验，再由 Canonical Commit 生效。

### R-005 实现优先复用

数据库、Agent Runtime、Memory Intelligence、Search、Graph、Voice、Model 和 Provider 优先采用可插拔外部实现。

### R-006 小而稳定的 Core

Core 只保留如果外包就会破坏资产所有权、主权、连续性或可迁移性的控制语义。一个概念只有在未来 AI 范式完全变化后仍必然需要时，才进入 Tiny Core。

领域语义优先进入 typed Profile，智能算法和具体执行进入 Extension，未验证能力进入后续 Phase，而不是预建空模块。

### R-007 Adapter 是一等能力

Shadow 提供最小 AdapterDescriptor、按 Family 划分的 Port、Capability Negotiation、版本协商、健康检查和 Contract Test。

通用 Descriptor 只包含 adapter_id、family、contract_versions、capabilities、config_schema_ref、implementation_ref 和 health。权限、Secret、Checkpoint、Migration、Data Boundary 与 Reconciliation 通过 Family-specific Capability 声明，不形成万能 Manifest。

### R-008 长期可升级

Shadow 需要支持数据版本、兼容性检查、迁移、导出、导入、备份元数据和完整性验证。

### R-009 单用户优先

近期只开发单用户场景。核心 Contract 不依赖不可移除的全局单用户假设，但暂不开发完整多用户功能。

### R-010 所有执行经过 Shadow，但不都经过 Agent Runtime

Shadow 按 Capability 和 Binding 把 Run 交给适当的 `target_kind`。Agent Runtime、Model Worker、Deterministic Runner、Workflow Target 和 Capability Provider 是首批 well-known kinds，不是封闭全集。

Core 不根据名称硬编码执行逻辑；固定脚本和单次模型推理不需要启动 Agent Loop。

### R-011 健康心跳必须确定性

进程健康、Lease、Timeout 和 Scheduler Tick 不依赖模型。小模型可以作为可替换的 Semantic Pulse 提出状态、Recall、Run 或 Task Proposal，但不能成为系统正确运行的必要条件。

### R-012 归属从第一版显式存在

所有 Canonical Asset 必须具有 Owner Reference 和 Space ID。Owner 可以是 User 或 Space；创建者与所有者分别记录。近期不实现多用户权限，但不能依赖“当前用户”或“无主体”的隐式假设。

### R-013 数据最小披露

Model、Runtime、Runner 和 Provider Binding 必须声明可处理的数据等级和边界。Shadow 在执行前裁剪和校验上下文；智能分类器可以提高敏感度，但不能自行降低保护等级。

### R-014 用户拥有最终删除与迁移权

逻辑删除、保留历史和审计不能取消用户的最终物理删除权。标准导出必须可迁移；完整备份必须独立加密和授权。

### R-015 Profile 与 Kernel 分离

Canonical Envelope 提供统一治理，但不能退化为无语义 JSON 容器。Memory、State、Task、Action、Skill 等 Profile 必须提供版本化 Schema、状态不变量和迁移规则，同时不进入 Tiny Core 的硬编码类型分支。

## 4. 功能需求

### 4.1 Admission、Request、Run 与 Attempt

Shadow 必须区分：

- Admission Record：准入结果的最小记录；
- Request：被接受请求的不可变准入记录；
- Root Run：一个被接受 Request 对应的一次顶层运行；
- Execution Attempt：同一 Run 下的一次具体执行尝试。

身份无法确认、格式无效、权限拒绝、来源撤销或重复重放等准入失败只创建受 Retention Policy 控制的最小 Admission Record，不创建 Run。

每个被接受的 Request 必须创建一个 Root Run。失败重试必须创建新的 Execution Attempt，不创建重复 Root Run，也不能覆盖旧 Attempt。

Run 最小状态机为：

~~~text
created → queued → running
                    ├─ waiting → running
                    ├─ paused → queued
                    ├─ completed
                    ├─ failed
                    └─ cancelling
                         ├─ cancelled
                         └─ cancellation_unknown
~~~

Shadow 必须校验状态转换。用户请求取消不等于外部执行已停止；只有获得 Target 确认后才能提交 cancelled，无法确认时提交 cancellation_unknown。

最小记录保存身份、时间、状态、Binding、费用、结果摘要和必要审计引用。完整对话、Prompt、模型输出和 Tool Trace 按 Retention Policy 与 Data Classification 保存；Runtime 私有推理不要求保存。

### 4.2 Durable Task

需要跨 Session、Execution Target、重启、等待条件或长期时间存在的工作必须表示为 Durable Task。执行耗时较长或使用 Agent Runtime 本身不构成 Durable Task。

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
- Shadow 对最终 Task 状态的提交；
- 一个 Durable Task 跨时间关联多个 Run；
- 从普通 Run 接收 Durable Task Proposal。

用户可以直接创建 Durable Task。Runtime、Semantic Pulse、规则和其他组件只能提交 Durable Task Proposal，由 Shadow 校验后创建。

Runtime 内部 Planner、Subtask、Subagent 和 Workflow 不要求同步为 Shadow Task。Run 成功不自动代表 Durable Task 完成；Runtime 提交 Completion Proposal，Shadow 根据 Task 完成条件、外部结果和 reconciliation 提交最终状态。

### 4.3 Runtime 接入

Runtime Adapter 的最小 Port 只要求：

- `describe`：声明 contract version、target kind 与 capabilities；
- `execute`：接受 Execution Request；
- `events`：产生类型化事件流或终态结果。

cancel、progress、usage、checkpoint、native resume、semantic handoff 和 reconciliation 是可选 Capability。Adapter 不能为了满足统一接口而伪造不支持的恢复或取消语义。

具体 Runtime SDK、Session、Planner、Subagent 和 Tool Loop 不进入 Canonical Schema。

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

### 4.7 Canonical Memory Profile

Shadow 必须持久化用户在长期使用中形成的 Memory，使其不随 Memory Intelligence 替换而丢失。

Memory 由官方 typed Profile 定义稳定身份、版本、Scope、Provenance、Evidence、source_dependency、纠正、supersede、删除和迁移语义。Tiny Core 不理解 Memory 内容，不实现提取、整理、召回或融合算法。

Memory Candidate 只有经过 Proposal / Validate / Commit 才成为 Canonical Memory Record。

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

### 4.9 Store Capability Family

Shadow 不开发数据库，也不使用一个 Port 抽象整套数据库产品。Store Adapter 可以分别声明：

- Canonical Repository；
- Schema Migration；
- Portable Export / Import；
- Backup / Restore；
- Durable Outbox；
- Integrity Verification。

第一阶段只强制 Canonical Repository 与必要 Migration。只有 Canonical 语义和标准可移植导出必须跨 Store 一致；事务、复制、物理备份、索引和队列属于具体实现。

### 4.10 Skill

Shadow 原生兼容 Agent Skills 规范，不自创 Skill 内容包标准。

一个可移植 Skill Bundle 保留原始 `SKILL.md` 和可选 `scripts/`、`references/`、`assets/`。Shadow 的 SkillAsset 只管理 Stable ID、Owner / Space、format、source reference、pinned revision、digest、trust、permission policy、classification、install status 与 Runtime Projection。

Shadow 元数据不得修改标准 Bundle。Provider Skill ID 只是外部引用；Runtime-specific Prompt 或上传对象是 Derived State。Shadow 独立执行权限，不能把实验性的 `allowed-tools` 视为最终 Authority。

### 4.11 Extension、Integration 与 Capability

用户应能统一管理 Extension、Integration、MCP Connection、SkillAsset、Executable Asset、Runtime / Model / Runner Profile 和 Provider Binding。

统一管理不意味着统一成一个万能聚合。Core 只保存共同身份、Owner / Space、来源、版本、启停、Binding、Secret Reference 和 Descriptor Reference；Family Profile 定义自己的配置、权限和生命周期。

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

### 4.13 Event、Observation 与 World State Profile

Event 表示发生过什么，Memory 表示值得长期保留的知识，Task 表示未来承诺，State Profile 表示当前接受的现实投影。

State Profile 必须支持 source、observed_at、expires_at、Evidence、fresh / stale / unknown、source unavailable 和版本迁移。Accepted State 是可恢复、可迁移的 Canonical Record，但可以过期。

Tiny Core 只执行 Schema、权限、Expected Version、通用时间有效性和 Commit。Source Adapter、Resolver、预测、融合、本体和领域查询外置。Domain Event 仅作为通知信封，不要求 Event Sourcing。

### 4.14 Execution Dispatch

Execution Binding 至少保存 `target_kind`、adapter reference、contract version、capabilities、policy / envelope reference 和实际版本。

Core 根据 Capability、数据等级、预算、副作用、健康与显式规则校验 Binding；Router 可以提出 Binding Proposal，但不能提交。新增 namespaced target kind 不得要求修改 Core 主流程。

### 4.15 Model Worker 与 Routing

Shadow 必须允许不经过 Agent Loop 的直接 Model Worker。

Model Worker 通过 Model Port 接收受约束的输入并返回结构化或文本结果。模型 Provider、模型选择和推理实现可以替换。

Routing Component 只能返回 Route Proposal。Shadow 必须根据可用性、权限、预算、数据等级和任务要求校验后提交 Execution Binding。

Router 无法确定安全 Binding 时必须询问用户。用户可以选择仅对当前 Run 生效，或将决定保存为可查看、修改、导出和删除的 Routing Rule。Core 不进行隐式智能降级。

每个 Model Binding 必须声明 local / remote、允许的数据等级、是否允许 Memory、World State 和外部资产内容，以及 retention、training、地域或组织限制。Shadow 必须在调用前执行最小上下文裁剪。

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

### 4.19 归属、Space 与数据治理

每个 Canonical Asset 必须具有：

- owner_ref，可指向 User 或 Space；
- space_id；
- created_by；
- data_classification；
- retention_policy；
- lifecycle state 和 version。

第一版必须存在正式 Space Record、类型和生命周期，但只创建默认 Personal Space 和隐式 Home Space，不实现成员、角色、共享和邀请。个人资产可以归 User；公共房间和家庭设备状态归 Home Space。

Core 执行 public、personal、sensitive、restricted 四级数据约束。用户、来源和外部分类器可以提出标签；分类器可以提高等级，降低等级必须由用户或确定性策略确认。无法判断时默认 sensitive。

Secret 是用户长期能力资产的一部分，但凭据与普通资产分离。标准导出只包含 Secret Reference；完整备份可以在单独授权和加密后包含 Secret。

### 4.20 保留、删除与 Erasure

Shadow 必须支持：

- 类型级 Retention Policy；
- logical delete、restore 和 scheduled physical erase；
- correction / supersede 版本关系；
- 敏感历史彻底擦除；
- 不含原始内容的最小 Tombstone；
- 统一 Erasure Request；
- Memory、Index、Cache、Backup 和其他派生组件的清除状态。

Core 管理 Erasure Intent、范围和状态；Adapter 执行具体删除。无法确认的组件必须显示 pending 或 unreachable，不能报告已完成。

### 4.21 导出与备份

Shadow 必须提供两种不同承诺：

1. 标准可移植导出：包含 Canonical Assets、Owner / Space、Integration、Binding、Schema 和迁移所需元数据，不包含 Secret 内容和可重建状态；
2. 完整设备备份：可以包含加密 Secret、Checkpoint 和部分派生状态，但必须单独加密、明确授权，且不能成为跨实现兼容性的基础。

### 4.22 用户控制

用户必须能够：

- 查看 Run 和 Durable Task；
- 查看、修正和删除 Canonical Memory 与 World State；
- 查看 Owner、Space、Data Classification 和 Retention Policy；
- 查看 Skill、Extension 和 Integration；
- 查看 Approval 和外部 Action；
- 暂停或取消工作；
- 禁用组件或撤销权限；
- 导出 Shadow 长期资产；
- 查看迁移和完整性验证结果。

### 4.23 交互便利性与未来接口

Shadow 产品需要允许通过 Chat、CLI、API 和未来的 Voice / Device Endpoint 使用。

Wake Word、STT、TTS、音频流和设备协议由可替换组件提供。近期不要求开发家庭多用户、分布式麦克风或完整语音系统，但 Core Contract 不应阻止这些接口接入。

## 5. 非功能需求

### NFR-001 长期持久性

用户长期资产应能跨 Runtime、Memory Intelligence 和其他组件升级继续使用，设计目标面向多年持续演进。

### NFR-002 可替换性

删除任何智能组件后，Canonical Asset 不得因此丢失。可重建状态允许重新生成。

### NFR-003 可移植性

Shadow 长期资产必须具有版本化、可验证、可导出的表示。标准导出不依赖具体 Store、Runtime、Model、Runner、Router 或 Memory Engine 的私有格式。

### NFR-004 本地优先

本地优先表示用户拥有控制权、可导出性、可迁移性和可验证性，而不是把物理存储位置写死。Store Binding 可以指向本地或远程实现，默认配置应优先提供本地 Store。

外部云能力只能获得完成当前请求所需、且符合 Model / Provider Binding 数据边界的数据和权限。

### NFR-005 可恢复性

Core 重启后，应能从 Durable Store 恢复已提交的长期状态。

### NFR-006 可审计性

重要状态变化和现实动作应能追踪到 Request、Task、Component、Policy、Authorization 和 Result。

### NFR-007 使用便利性

组件可替换性不能要求普通用户直接操作每个底层项目。Shadow 应提供统一入口、统一配置和统一用户控制。

### NFR-008 实现克制

一个概念先按 CORE / CONTRACT-ONLY / PROFILE-EXTENSION / LATER-PHASE 分类。没有跨组件主权或连续性证据的概念不得进入 Tiny Core；没有真实实现需要的 Contract 不预建服务、表或万能抽象。

### NFR-009 状态时效性

World State 必须显式表达时效和未知状态。过期 Observation 不得被静默当作当前事实。

### NFR-010 确定性基础运行

系统健康、调度 Tick、Lease 和 Timeout 不依赖任何模型或语义智能组件。

### NFR-011 隐私默认值

数据敏感度无法确定时默认 sensitive。外部智能组件不得自行降低数据保护等级。

### NFR-012 可删除性

用户发起物理清除后，Shadow 必须可追踪所有受管组件的删除状态；无法访问的组件必须明确报告未完成。

## 6. 明确不自研的基础能力

OpenShadow 不自研：

- 基础模型、通用 Agent Loop、Planner、Subagent 或 Workflow Engine；
- 智能 Router、Memory Intelligence、State Resolver、Search / RAG、Embedding、Graph 或领域本体；
- 数据库引擎、复制系统、物理备份、Secret Store、消息队列或通用调度平台；
- 脚本语言 Runtime、依赖解析、Sandbox 或资源隔离平台；
- Skill 内容格式；默认兼容 Agent Skills；
- STT、TTS、Wake Word、浏览器 Agent、Coding Agent、设备协议或领域数字孪生；
- 通用 Policy 语言或自建插件操作系统。

Shadow 只实现连接这些能力所需的主权、连续性、类型 Profile、Binding、Capability、迁移与用户控制边界。

## 7. 顶层验收原则

1. 替换 Runtime、Model、Memory Intelligence、State Resolver 或 Store，不改变 Canonical ID 和 Owner；
2. External Component 不能绕过 Proposal / Validate / Commit；
3. 新增 Execution Target Kind 不修改 Core 主流程；
4. 删除派生组件不会删除 Canonical Record；
5. Profile 升级具有 Schema 与语义迁移路径；
6. Skill Bundle 保持标准格式并可离开 Shadow 使用；
7. Store Adapter 只实现其声明的 Capability，不伪造备份、取消或恢复；
8. 健康、TTL、权限和恢复不依赖 LLM；
9. 用户可以查看、纠正、撤销、删除、导出和迁移长期资产；
10. Phase 0–1 是完整架构的真子集，不把短期实现固化为长期内核。


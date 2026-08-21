# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 是一个可以长期存在、持续升级的个人 AI。**

OpenShadow 是一个本地优先、实现无关的个人 AI 资产与能力平台。用户始终在使用同一个 Shadow；Agent Runtime、模型、Memory Intelligence、Router、Runner、数据库、语音、设备与其他快速演进能力都通过可替换组件接入。

Shadow 不重新实现所有 AI 基础设施。它用一个小而稳定的主权内核，组合外部优秀项目，同时保证用户长期积累的身份、资料索引、记忆、任务、能力和治理记录不会随某个组件被替换而消失。

## 产品结构

~~~text
Shadow
├─ Tiny Core
│  ├─ Identity & Ownership
│  ├─ Canonical Record & Lifecycle
│  ├─ Proposal / Validate / Commit Authority
│  ├─ Work Admission & Minimal Continuity
│  ├─ Extension Contract & Binding
│  └─ Portability & Erasure Intent
│
├─ Official Profiles
│  ├─ Conversation / Memory / State
│  ├─ Durable Task / Action
│  ├─ Skill / Capability / Integration
│  └─ Profile-specific schemas and invariants
│
├─ Replaceable Components
│  ├─ Runtime / Model / Runner / Workflow / Router
│  ├─ Memory Intelligence / Retrieval / State Resolver
│  ├─ Store / Search / Scheduler / Policy Engine
│  ├─ Source / Provider / MCP / Skill Runtime
│  └─ Web / Voice / Device Interfaces
│
└─ User-owned Assets
   ├─ Conversations / Memories / Tasks / State
   ├─ Skills / Executables / Integrations
   ├─ External Asset Catalog / Artifacts
   └─ Bindings / Policies / Action History
~~~

Shadow 是完整产品。Tiny Core 只理解长期主权和连续性所必需的控制语义；Memory、World State、Task、Skill 等由版本化 Profile 定义，不被硬编码成不可演进的内核模块。

## 核心不变量

### 所有承载工作的输入经过 Shadow

Chat、Voice、Schedule、Event、API Command 和 Semantic Pulse Proposal 等工作入口都经过 Admission。一个被接受的工作 Request 创建一个 Root Run；准入失败只形成最小 Admission Record。

健康检查、静态资源、只读控制面查询、已有 Run 的事件订阅和内部恢复步骤不创建 Root Run，但仍受身份、权限和审计约束。

### 所有执行受 Shadow 治理，但不都经过 Agent Runtime

Execution Binding 使用可扩展、带命名空间的 `target_kind`。首批 well-known kinds 是：

- `shadow.agent-runtime`；
- `shadow.model-worker`；
- `shadow.deterministic-runner`；
- `shadow.workflow-target`；
- `shadow.capability-provider`。

它们不是永久封闭枚举。Core 根据 Capability、数据边界、副作用、预算和健康状态治理执行，不为每种 Target 硬编码业务分支。

### 外部智能只能提议，Shadow 才能提交

~~~text
External Intelligence / Execution
                ↓
          Typed Proposal
                ↓
   Schema + Authority + Policy Validation
                ↓
        Canonical Commit
                ↓
  Versioned Canonical Record / Profile
~~~

Memory Engine 不能直接改 Memory，Router 不能直接改 Binding，Runtime 不能直接完成 Durable Task，State Resolver 不能直接改当前状态，Provider 不能绕过 Action Authority 产生现实副作用。

### Canonical Record 统一治理，但不退化成万能 JSON

所有长期记录共享最小治理信封：

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref / space_id / created_by
├─ classification / provenance
├─ version / lifecycle / retention
└─ typed_payload
~~~

Envelope 负责身份、归属、版本、来源和生命周期。各 Profile 继续定义必要的类型化 Schema、合法状态转换和迁移规则；仅更换 JSON Schema 不能替代语义迁移。

## Memory 与 World State

Canonical Memory 是 `memory` Profile 的用户资产，必须在更换 Memory Intelligence 后继续存在。外部组件负责提取、整理、召回、去重、Embedding、Graph 和排序；Shadow 只治理 Candidate、版本、来源、纠正、删除和提交。

World State 是官方 `state` Profile，不是 Tiny Core 内建知识图谱。Core 只提供通用身份、来源、证据、时间有效性和提交机制；State Profile 定义 state key、Observation、fresh / stale / unknown 与迁移语义；采集、融合、预测、本体和领域查询全部外置。

~~~text
Source Adapter / State Resolver
             ↓
       State Proposal
             ↓
     Shadow validates
             ↓
Versioned State Profile Record
~~~

Accepted State 可恢复和迁移，但允许过期。Shadow 不要求实时访问所有外部知识库或设备，只在需要时调用并诚实表达 stale / unknown。

## Skill 与能力资产

Shadow 不自创 Skill 内容格式。官方 Profile 原生兼容 [Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)：保留标准 `SKILL.md` 以及可选的 `scripts/`、`references/`、`assets/`。

Shadow 的 `SkillAsset` 只保存治理信息：稳定 ID、Owner / Space、来源、固定版本或 revision、digest、信任、权限策略、数据等级、安装状态和 Runtime Projection。标准 Skill Bundle 不因 Shadow 元数据而被修改；Provider Skill ID 只是外部引用。

具体 Skill 发现、加载、Prompt 投影、脚本执行和 Provider 上传由 Adapter 完成。Shadow 独立执行权限和信任边界，不能把实验性的 `allowed-tools` 当作最终授权。

外部资料也遵循同一原则：Notion、Obsidian、Drive、Email 和文件系统中的原始内容继续由外部来源持有；Shadow 的 Asset Catalog 默认只记录“存在什么、在哪里、如何访问”，需要时再读取。

## Adapter 与基础设施边界

通用 `AdapterDescriptor` 保持最小：

~~~text
adapter_id
adapter_family
contract_versions
capabilities
config_schema_ref
implementation_ref
health
~~~

权限、Secret、迁移、Checkpoint、数据边界和 Reconciliation 是按 Adapter Family 声明的可选能力，不进入一个万能 Manifest。

Runtime 基础 Port 只要求 `describe`、`execute` 和 `events`；cancel、checkpoint、native resume、semantic handoff、progress、usage 与 reconciliation 通过 Capability Negotiation 声明。Adapter 不得伪造不支持的能力。

Shadow 也不抽象整套数据库。Store Family 分成 Canonical Repository、Migration、Portable Export / Import、Backup、Outbox 和 Integrity Capability。只有 Canonical 语义和标准可移植导出需要跨 Store 一致；物理 Schema、复制、备份和队列实现属于外部基础设施。

## 治理与长期升级

- 每个 Canonical Record 从第一版具有明确 Owner 和 Space；
- 近期只实现单用户、默认 Personal Space 和隐式 Home Space；
- Core 只执行少量确定性 Policy：数据等级、Capability、Approval、Budget、副作用、有效期和撤销；
- 复杂 Policy 计算可以外置，但 Core 保留最终检查；
- 用户拥有纠正、逻辑删除、最终物理清除、导出和迁移权；
- 标准导出不依赖 Secret、缓存、索引或具体组件私有格式；
- Store 故障时暂停 Canonical Commit，默认禁止未记录现实副作用；
- Domain Event 只是通知信封，不采用强制 Event Sourcing；
- Outbox 只解决跨边界副作用可靠提交；
- OperationJob 只用于迁移、导出、备份和 Erasure 等长操作。

## 当前明确不自研

OpenShadow 不自研数据库引擎、通用 Agent Loop、基础模型、智能 Router 算法、Memory Intelligence、向量数据库、知识图谱、Workflow Engine、脚本运行时与沙箱、语音引擎、浏览器 Agent、Coding Agent、设备协议栈或领域数字孪生。

OpenShadow 自行实现的范围收紧为：

- Stable ID、Owner、Space、Version 与 Canonical Envelope；
- Proposal / Validate / Commit 主权边界；
- Admission、Run / Attempt 与最小 Task Continuity；
- 类型 Profile 注册、Schema 兼容与迁移控制；
- 最小 Adapter Registry、Binding 与 Capability 校验；
- 确定性数据、授权、预算和副作用执行点；
- 标准导出、完整性校验与 Erasure Intent；
- 用户查看、纠正、撤销、删除和导出 API。

## 文档

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [Core / External 责任矩阵](docs/responsibility-matrix.md)
- [关键用例](docs/use-cases/README.md)
- [领域模型](docs/domain-model.md)
- [状态机基线](docs/state-machines.md)
- [完整技术架构](docs/technical-architecture.md)
- [分阶段实现计划](docs/implementation-stages.md)
- [参考实现 Profile](docs/implementation-profile.md)
- [开发路线](docs/roadmap.md)
- [架构决策记录](docs/adr/README.md)

## 当前状态

Stage 0–3 已形成需求、责任、用例和领域基线。Stage 4 正在用 Tiny Kernel、typed Profile、Proposal / Commit 和 capability-first Adapter 完成架构收紧；完整目标架构仍按 Phase 0–5 分阶段实现，不以短期 MVP 限制长期边界。

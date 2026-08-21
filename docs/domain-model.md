# OpenShadow 领域模型

- 状态：Stage 3 基线 / Stage 4 Core Diet 修订
- 输入：[关键用例](use-cases/README.md)、[责任矩阵](responsibility-matrix.md)与[ADR-0003](adr/0003-tiny-core-and-typed-profiles.md)
- 目标：定义长期稳定的控制原语，以及可独立演进的类型 Profile
- 非目标：不定义数据库表、ORM、API DTO、进程边界或具体外部组件

## 1. 设计立场

Shadow 的完整产品边界很大，但 Tiny Kernel 必须很小。

本模型遵守：

1. Tiny Kernel 只理解身份、归属、版本、生命周期、Authority、工作连续性、Binding 和可移植性；
2. Memory、State、Task、Action、Skill 等领域语义由版本化 typed Profile 定义；
3. Canonical Envelope 不是无约束 JSON 容器，Profile 必须声明 Schema、不变量和迁移；
4. Proposal 与已接受状态分离；
5. External Component 不能直接提交 Canonical State；
6. Run / Attempt 是控制平面事实，不能由 Runtime 私有 Session 代替；
7. Aggregate 是实现期一致性边界，不是必须长期冻结的公共类型清单；
8. Canonical Record 之间使用 Stable ID 引用，不复制完整对象；
9. Derived State 可以删除重建；
10. 默认采用模块化单体、一个 Primary Store 与少量 Adapter；
11. 一个新概念先进入 Profile 或 Extension，只有证明跨 Profile 都必需后才进入 Kernel Contract。

## 2. 四级归属

| 等级 | 含义 | 典型内容 |
|---|---|---|
| KERNEL | Tiny Kernel 必须直接理解并执行 | Stable ID、Owner / Space、Version、Canonical Commit、Admission、Run / Attempt、Binding |
| CONTRACT-ONLY | Core 保留最小跨组件语义，不要求立即实现完整功能 | Durable Task continuity、Action safety、Export / Migration / Erasure Intent |
| PROFILE / EXTENSION | Shadow 发布标准 Profile，具体语义和智能可独立演进 | Conversation、Memory、State、Skill、Integration、Capability |
| LATER PHASE / DERIVED | 不进入当前稳定模型，按真实用例增加或重建 | Router Score、Embedding、Graph、Prompt、Runtime Planner、复杂 ACL、领域本体 |

“Profile 属于 Shadow”与“Profile 不硬编码进 Tiny Kernel”不矛盾。官方 Profile 可以提供十年兼容承诺，但通过 Schema Registry、Migration 和 Commit Policy 接入同一 Kernel。

## 3. Kernel Model

### 3.1 Canonical Envelope

所有 Canonical Record 共享：

~~~text
CanonicalEnvelope
├─ record_id
├─ record_type
├─ schema_ref
├─ owner_ref / space_id / created_by
├─ data_classification
├─ provenance
├─ version
├─ retention_policy_ref
├─ record_state
├─ created_at / committed_at
└─ typed_payload
~~~

Kernel 保证：

- Stable ID 不因 Adapter、Runtime、数据库或 Profile 实现替换而改变；
- owner_ref 与 space_id 从第一版存在；
- expected_version 属于 Mutation Input，并在 Commit 时防止静默覆盖；
- schema_ref 可以定位验证器和 Migration；
- erased 内容只留下不含原文的最小 Tombstone；
- Secret 内容不进入普通 Envelope。

Kernel 不解释 typed_payload 的领域含义。Profile Validator 负责类型不变量，Kernel 在 Commit 前调用已绑定且受信任的 Validator。

### 3.2 Canonical Commit

所有长期状态变化统一为：

~~~text
Command or Typed Proposal
          ↓
Identity / Schema / ExpectedVersion
          ↓
Authority / Deterministic Policy
          ↓
Profile Validation
          ↓
Canonical Commit
          ↓
New Version + optional Notification Event
~~~

Commit 至少记录：

- command_id / proposal_id；
- actor_ref / proposer_ref；
- target record / expected version；
- schema_ref；
- accepted / rejected reason；
- correlation_id / causation_id；
- resulting version。

Proposal 未接受前不是 Canonical State。External Component 不获得绕过 Commit 直接写 Primary Store 的权限。

### 3.3 Principal、Space 与 Schema

Kernel Canonical Records：

- Principal Reference；
- Space Record；
- Schema / Profile Descriptor；
- Adapter Descriptor；
- Execution Binding；
- Store Binding；
- Tombstone；
- Migration / Export / Erasure Intent。

第一版只创建当前 User、默认 Personal Space 和隐式 Home Space，不实现成员、角色、邀请和共享 ACL。

### 3.4 Admission、Request、Run 与 Attempt

只有承载工作的输入形成 Request：

~~~text
Work-bearing Input
      ↓
AdmissionRecord
      ├─ rejected / duplicate / denied
      └─ Accepted Request → Root Run → Execution Attempts
~~~

健康检查、静态资源、只读控制面查询、已有 Run 事件订阅和内部恢复步骤不创建 Root Run。

Request 是不可变控制记录。一个 Accepted Request 恰好创建一个 Root Run。Retry 只追加 ExecutionAttempt，不覆盖旧 Attempt，也不创建重复 Root Run。

Run 最小字段：

- run_id / request_id / optional task_ref；
- lifecycle；
- requirements；
- binding refs；
- attempt refs；
- result / failure / usage summary；
- cancellation state；
- timestamps / expected_version。

Runtime 私有 Planner、Subtask、Subagent、Tool Loop 和 Session State 不进入 Kernel Model。

### 3.5 Execution Binding 与 Capability Envelope

ExecutionBinding 是版本化控制记录，包含：

~~~text
target_kind
adapter_ref
contract_version
required_capabilities
resolved_capabilities
implementation_version
policy_ref / envelope_ref
~~~

`target_kind` 是 namespaced string，不是封闭枚举。首批 well-known kinds：

- `shadow.agent-runtime`；
- `shadow.model-worker`；
- `shadow.deterministic-runner`；
- `shadow.workflow-target`；
- `shadow.capability-provider`。

CapabilityEnvelope 是一次 Run 或 Durable Task 的确定性授权结果，最小包含允许的 Capability、数据范围、预算、副作用、有效期、撤销状态和 Policy Version。

Router 只能提交 Binding Proposal；Core 根据 Capability 和 Envelope 接受或拒绝，不根据 target kind 名称建立永久业务分支。

## 4. Profile Model

### 4.1 Profile Descriptor

每个 Profile 声明：

~~~text
profile_id
record_type
schema_versions
validator_ref
migration_refs
lifecycle_contract
proposal_schemas
portable_export_rules
compatibility
~~~

Profile Validator 可以由 Shadow 官方包、可信 Extension 或纯确定性 Schema 实现，但最终 Commit 仍由 Kernel 完成。Profile 不能给自己增加写权限。

### 4.2 Conversation Profile

Conversation / Message 是官方 Profile：

- Message 是独立、不可变 Canonical Record；
- Conversation 保存有序 Message references；
- 修正通过新 Message 或 redaction / erase 语义完成；
- 单条内容可以有独立 Retention；
- 删除 Conversation 不自动删除独立 Memory；
- Runtime Session 不属于 Conversation。

“同时最多一个前台生成 Run”属于参考 Interaction Profile 的并发规则，不进入所有 Canonical Object 的 Kernel。

### 4.3 Memory Profile

Memory Profile 定义：

- Memory stable identity；
- Canonical Envelope 的不可变版本；
- Claim / content；
- owner / space / scope；
- provenance / Evidence refs；
- validity / lifecycle；
- source_dependency：independent / dependent / review_required；
- correction / merge / supersede；
- logical delete / physical erase / anti-resurrection Tombstone。

Memory 不建立平行的 `MemoryVersion` 实体或第二套 current-version pointer。精确历史版本使用 `(record_id, version)` 引用；同一 Memory 的 correction 创建新的 Canonical Envelope Version，跨 Memory merge 在一个 Commit Batch 中创建新 Memory 并 supersede 输入记录。

MemoryCandidate 不是 Memory。Memory Intelligence 负责 extraction、consolidation、deduplication、retrieval、reranking、embedding、graph 和 summary，只能提交 Candidate / Recall Result。

更换 Memory Profile 大版本需要显式语义 Migration；仅修改 JSON Schema 不足以证明兼容。

### 4.4 State Profile

State Profile 定义“当前接受的现实状态”，而不是在 Kernel 中建立知识图谱。

最小 State Record：

~~~text
state_key
typed_value
value_schema_ref
source_refs
evidence_refs
observed_at
accepted_at
expires_at
freshness: fresh | stale | unknown
source_availability
~~~

Observation 是 State Profile 的 typed Proposal / Evidence Record，可以按类型设置 Retention。Accepted State 是 Canonical Record，可恢复和迁移，但允许过期。

Core 只理解通用时间有效性、Schema、Authority、Expected Version 和 Commit。State Profile Validator 处理 state_key 与 freshness 不变量。Source Adapter、Resolver、冲突融合、预测、异常检测、领域本体和查询外置。

可恢复流程：

~~~text
Observation committed when retention requires
    → State Proposal
    → Profile validation
    → Accepted State version
    → optional applied reference
~~~

Store 支持事务时可以优化，但 Contract 不要求跨 Adapter 分布式事务。

### 4.5 Durable Task Profile 与 Kernel Continuity Contract

Durable Task 是 CONTRACT-ONLY + 官方 Profile：

Kernel 只保证：

- stable task_id；
- owner / space；
- lifecycle version；
- related Run refs；
- checkpoint / artifact / trigger refs；
- completion commit。

Task Profile 可以定义 goal、completion criteria、waiting condition、deadline、retry 和 Semantic Checkpoint。规划、分解、Task Graph 和 Workflow Engine 外置。

Run 成功不自动完成 Task。Runtime、Semantic Pulse 和规则只能提交 Task / Completion Proposal。

### 4.6 Action Profile 与安全 Contract

Action 是后续 Phase 的官方 Profile，但以下安全语义属于 Kernel Contract：

- ActionProposal 与 Action 分离；
- Provider 调用前持久化 pending / approval decision；
- idempotency key；
- succeeded / failed / unknown；
- unknown outcome 必须 reconciliation；
- 没有可靠记录时不得执行现实副作用。

参数生成、风险解释、协议调用和 reconciliation 建议外置。

### 4.7 SkillAsset Profile

Shadow 不定义 Skill 内容格式。默认 Profile 兼容 Agent Skills：

~~~text
skill-root/
├─ SKILL.md
├─ scripts/       optional
├─ references/    optional
└─ assets/        optional
~~~

SkillAsset typed payload 只保存治理信息：

- format；
- source reference；
- pinned revision / immutable snapshot；
- digest；
- trust；
- permission policy；
- classification；
- install status；
- runtime projections；
- provider external refs。

原始 Bundle 不因 Shadow 元数据而修改。Runtime-specific Prompt、Provider upload 和缓存是 Derived State。`allowed-tools` 仍是实验性元数据，不能代替 Shadow Authority。

### 4.8 Integration 与 Capability Profile

Integration 需要稳定 ID，因为更换 Adapter 不应改变用户配置对象的身份。

共同治理字段进入 Envelope；Family Profile 定义：

- config schema；
- permissions；
- Secret References；
- bindings；
- health / availability；
- lifecycle；
- family-specific capabilities。

Skill、Executable、Extension、Integration、MCP Connection 和 Runtime / Model / Runner Profile 可以在同一 UI 管理，但不合并成一个万能聚合。

## 5. Proposal Families

公共 Proposal Envelope：

~~~text
proposal_id
proposal_type
payload_schema_ref
target_ref
expected_version
proposer_ref
evidence_refs
created_at / expires_at
correlation_id / causation_id
typed_payload
~~~

官方 Proposal 类型包括：

- BindingProposal；
- MemoryCandidate；
- StateProposal；
- DurableTaskProposal；
- CompletionProposal；
- ActionProposal；
- ClassificationProposal；
- CapabilityExpansionProposal；
- ClarificationProposal。

这不是封闭全集。新 Profile 可以注册 namespaced proposal_type 和 Schema，但不能绕过 Authority。

Execution / Intelligence Port 可以返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage 等族。Infrastructure Port 使用 StoreCommitResult、SecretResolveResult、ExportResult 等 family-specific payload；公共部分只共享 Message Envelope、版本和结构化错误。

## 6. Adapter Model

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

Descriptor 只描述实现。安装实例由 AdapterRegistration 表达；配置与 Secret 分离；实时健康由带 TTL 的 HealthObservation 表达。权限、Secret、Checkpoint、Migration、Data Boundary 与 Reconciliation 是 Family Capability，不是所有 Adapter 的必填字段。

Runtime Port 基础能力：

- describe；
- execute；
- events。

可选能力：

- cancel；
- progress；
- usage；
- checkpoint；
- native_resume；
- semantic_handoff；
- reconciliation。

Adapter 必须诚实声明，不得模拟不支持的取消、Checkpoint 或恢复。

## 7. Store Capability Model

Shadow 不使用一个接口抽象整套数据库。Store Family 划分为：

| Capability | 责任 |
|---|---|
| Canonical Repository | 版本化读写、ExpectedVersion、事务能力声明 |
| Migration | Profile / Schema 迁移执行 |
| Portable Export / Import | 标准可移植包 |
| Backup / Restore | 实现相关完整设备备份 |
| Durable Outbox | 跨边界副作用可靠提交 |
| Integrity | 校验、清单与恢复验证 |

Phase 0–1 只要求 Canonical Repository 和必要 Migration。Backup、Outbox 与复杂 OperationJob 不进入首条闭环。

## 8. Domain Event、Outbox 与 OperationJob

Domain Event 是最小通知 Envelope，不采用强制 Event Sourcing。Canonical Record 仍是事实源。

Domain Event 仅用于：

- UI event stream；
- Profile / Adapter 通知；
- 派生索引重建；
- 跨记录最终一致；
- 审计关联。

Outbox 只用于需要可靠跨边界投递的现实副作用，不抽象成通用消息平台。

OperationJob 只用于 export、import、migration、backup 和 erasure 等长操作，不成为通用 Workflow 或后台任务框架。Memory 整理和普通调度不因为“耗时”自动进入 OperationJob。

## 9. Derived State

以下均可删除重建：

- Embedding / Index / Memory Graph；
- Router Score / Evaluation Cache；
- Prompt Rendering / Runtime Projection；
- Runtime Planner / Subtask；
- UI Cache / Materialized View；
- Summary Projection；
- Provider Skill upload；
- Telemetry Backend State。

Derived State 可以有外部 ID 和重建元数据，但不能成为标准导出的兼容性基础。

## 10. 实现分层

### Phase 0–1：Kernel 与个人闭环

实现：

- Canonical Envelope、Schema Registry、ExpectedVersion；
- Principal / Personal Space；
- Admission / Request / Run / Attempt；
- static Binding、minimal Envelope；
- one Runtime or Model Adapter；
- Conversation Profile；
- Memory Profile 的最小 Candidate / Commit；
- Canonical Repository Capability；
- Local Web。

### Phase 2：Memory 与能力资产

实现：

- Memory correction / erase / maintenance Adapter；
- SkillAsset / Executable / Integration Profile；
- Agent Skills Bundle 管理；
- Asset Catalog 与按需访问；
- 基础 Portable Export。

### Phase 3：连续性与 State Profile

实现：

- Durable Task Profile；
- checkpoint / handoff；
- State Profile、Observation、TTL / freshness；
- Source Adapter 与可选 Resolver；
- Migration / Integrity Capability。

### Phase 4：Action 与主动能力

实现：

- Action Profile 与 reconciliation；
- Router / Semantic Pulse；
- Policy Engine Adapter；
- Durable Outbox；
- 跨组件 Erasure。

### Phase 5：多端与多用户演进

实现候选：

- 多 Endpoint / Voice；
- Space membership / ACL；
- Home Space 共享；
- 远程 Store 与设备协调。

每个 Phase 是同一架构的真子集，不需要预建未使用的模块、表或服务。

## 11. 首条实现闭环

~~~mermaid
flowchart LR
    WEB["Local Web"]
    CONV["Conversation Profile"]
    ADMIT["Admission / Request"]
    RUN["Run / Attempt"]
    BIND["Static Binding / Envelope"]
    TARGET["Runtime or Model Adapter"]
    RESULT["Typed Result / Proposal"]
    COMMIT["Authority Commit"]
    MEM["Memory Profile"]
    STORE[("Canonical Repository")]

    WEB --> CONV --> ADMIT --> RUN --> BIND --> TARGET
    TARGET --> RESULT --> COMMIT
    COMMIT --> CONV
    COMMIT --> MEM
    RUN --> STORE
    CONV --> STORE
    MEM --> STORE
~~~

验收重点：

- 重启后 Conversation、Run 和 Memory 可恢复；
- 更换 Target Adapter 不改变 Canonical ID；
- Memory Component 只能提交 Candidate；
- 新 target_kind 不修改 Core 主流程；
- Store 只实现已声明 Capability；
- Phase 0–1 不依赖 Router、Pulse、State、Action、多用户或消息队列。

## 12. 冻结范围

Stage 4 冻结：

1. Kernel / Contract-only / Profile / Later Phase 四级分类；
2. Canonical Envelope 与 Proposal / Commit；
3. Work-bearing Admission、Run / Attempt；
4. namespaced target_kind 与 Capability-first Binding；
5. typed Profile + Schema + semantic Migration；
6. minimal AdapterDescriptor 与 Family Port；
7. Store Capability 分拆；
8. Skill 标准兼容边界；
9. Domain Event、Outbox、OperationJob 的窄用途。

不冻结：

- Profile 内部未来所有字段；
- Target Kind 全集；
- Adapter Transport 全集；
- Memory / State / Routing 算法；
- 数据库物理 Schema；
- 部署进程数量。

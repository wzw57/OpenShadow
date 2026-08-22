# Architecture Decision Records

OpenShadow 计划长期运行，而 Runtime、Memory Intelligence、数据库、模型、Runner、Router、Provider 和交互技术会持续变化。任何改变 Tiny Kernel、typed Profile、Authority、用户资产或可替换组件边界的决定，都必须记录原因、后果和重新评估条件。

## 已接受 ADR

- [ADR-0001：完整目标架构与分阶段实现](0001-target-architecture-and-phased-delivery.md)
- [ADR-0002：第一套参考实现 Profile](0002-reference-implementation-profile.md)
- [ADR-0003：Tiny Kernel、Typed Profile 与 Capability-first Extension](0003-tiny-core-and-typed-profiles.md)
- [ADR-0004：Agent Skills 原生兼容与 Shadow SkillAsset 治理](0004-agent-skills-compatibility.md)

- [ADR-0005：Phase 2 首个切片的 Memory 生命周期边界](0005-phase2-memory-lifecycle.md)
- [ADR-0009：Phase 2 SkillAsset sidecar 注册边界](0009-phase2-skillasset-sidecar.md)
- [ADR-0010：Phase 2 Integration Profile 注册边界](0010-phase2-integration-profile.md)
- [ADR-0011：Phase 2 Portable Import / restore snapshot 边界](0011-phase2-portable-import-restore.md)
- [ADR-0012：Phase 2 Physical erase 与 Tombstone 边界](0012-phase2-physical-erase-tombstone.md)
- [ADR-0021：Hermes Agent Runtime Adapter](0021-hermes-agent-runtime-adapter.md)
- [ADR-0022：Web UI 作为 Shadow API 参考客户端](0022-web-ui-reference-client.md)

## 待接受 ADR

- [ADR-0006：Phase 2 第二切片的 Recall / Maintenance Adapter 边界](0006-phase2-recall-maintenance.md)
- [ADR-0007：Phase 2 派生 Memory Index 重建边界](0007-phase2-derived-index-rebuild.md)
- [ADR-0008：Phase 2 source-dependent Memory invalidation 边界](0008-phase2-source-dependent-invalidation.md)

## ADR 格式

文件命名：

~~~text
NNNN-short-title.md
~~~

模板：

~~~md
# ADR-NNNN: Title

- Status: Proposed | Accepted | Superseded | Deprecated
- Date: YYYY-MM-DD
- Owners: ...

## Context

什么问题迫使我们作出决定？

## Decision

决定采用什么边界或行为？

## Rationale

为什么采用？

## Alternatives considered

考虑过什么，为什么没有采用？

## Consequences

正面和负面结果是什么？

## Revisit triggers

什么证据会触发重新评估？
~~~

## 决策索引

### 产品与所有权

1. Shadow 是完整 Agent；Runtime、Model、Memory Intelligence、Store、Voice 和 Provider 是内部可替换组件。
2. 用户或 Space 从第一条 Canonical Record 起具有明确所有权。
3.近期实现单用户、默认 Personal Space 与隐式 Home Space，不实现完整 ACL。
4.本地优先表示用户控制、可迁移和可验证，不冻结物理 Store 位置。
5.外部原始资料默认只登记和按需读取，不由 Shadow 复制为长期资料库。
6.用户拥有纠正、逻辑删除、最终物理清除、导出和迁移权。

### Tiny Kernel

7. Kernel 只持有 Identity、Owner / Space、Canonical Envelope、Version / Lifecycle、Proposal / Commit、Work Admission、Run / Attempt、minimal Continuity、Binding / Capability、deterministic Policy 与 Portability Intent。
8. 一个概念先分类为 KERNEL、CONTRACT-ONLY、PROFILE / EXTENSION 或 LATER PHASE / DERIVED。
9. Memory、State、Task、Action、Skill、Integration 使用 typed Profile，不成为 Kernel 永久 enum。
10. Canonical Envelope 统一治理，但 typed payload 必须有 Profile Schema、状态不变量和语义 Migration。
11. Profile Validator 不获得 Commit 权限。
12. External Component 不能直接写 Canonical Repository。

### Admission 与执行

13. 所有承载工作的输入经过 Admission。
14. 一个 Accepted Request 创建且只创建一个 Root Run。
15. Health、静态资源、只读控制面 Query、已有 Run 订阅和内部恢复步骤不创建新 Run。
16. Retry 是同一 Run 下的新 Attempt。
17.取消区分 cancelling、cancelled 与 cancellation_unknown。
18. Run completed 不自动完成 Durable Task。
19. Runtime 私有 Session、Planner、Subtask 和 Tool Loop 不进入 Kernel Model。
20. Binding 使用 namespaced target_kind，而不是封闭 execution mode enum。
21. agent-runtime、model-worker、deterministic-runner、workflow-target、capability-provider 是 well-known kinds。
22. Router 只能提交 BindingProposal，Core 按 Capability / Policy 校验。

### Proposal、Memory 与 State

23. Proposal → Validate → Commit 是所有外部智能的统一权威边界。
24. Canonical Memory 属于用户，Memory Intelligence 只产生 Candidate / Recall。
25. Embedding、Index、Graph、Summary Projection 是 Derived State。
26. State 是官方 Profile，不是 Kernel 内置知识图谱。
27. Accepted State 是可恢复、可迁移、允许过期的 Canonical Record。
28. Observation 是 State Profile 的 typed Proposal / Evidence，不等于 accepted state。
29. State Resolver 只提交 Proposal；fusion、prediction、ontology 外置。
30. fresh、stale、unknown 是 State Profile 稳定语义。
31.系统健康、TTL、Lease、Timeout 和恢复不依赖 LLM。
32. Semantic Pulse 是可选 Proposal producer，不是正确性依赖。

### Adapter 与 Store

33. 通用 AdapterDescriptor 只包含 identity、family、contract versions、capabilities、config schema、implementation ref 和 health。
34.权限、Secret、Checkpoint、Migration、Data Boundary 和 Reconciliation 是 Family Capability。
35. Runtime 基础 Port 只要求 describe、execute、events。
36. cancel、checkpoint、native resume、handoff、usage、reconciliation 是可选 Capability。
37. Adapter 不得伪造未支持能力。
38. Execution / Intelligence 与 Infrastructure 使用 family-specific typed payload，只共享 Message Envelope、Version、Correlation 和 structured error。
39. Store 分为 Canonical Repository、Migration、Portable Export / Import、Backup、Outbox、Integrity Capability。
40. Store Adapter 不要求实现其未声明的 Capability。
41. Primary Repository 故障时暂停 Commit，默认禁止未记录现实副作用。
42. Domain Event 是通知，不要求 Event Sourcing。
43. Outbox 只用于可靠跨边界副作用。
44. OperationJob 只用于 export、import、migration、backup、erasure。

### Skill 与能力资产

45. Shadow 不自创 Skill 内容格式，原生兼容 Agent Skills Bundle。
46. `SKILL.md`、`scripts/`、`references/`、`assets/` 保持标准原样。
47. Shadow SkillAsset 使用独立 sidecar 保存 Stable ID、Owner、revision、digest、trust、permission 和 projections。
48. Provider Skill ID 和 Runtime Prompt 是 External Reference / Derived State。
49. `allowed-tools` 不直接授予 Shadow Capability。
50.高风险 Skill 权限绑定 bundle digest / pinned revision。
51. Skill、Executable、Extension、Integration、MCP 和 Runtime Profile 可以统一管理，但不合并为万能聚合。

### 数据治理与 Action

52. Core 稳定执行 public、personal、sensitive、restricted；未知默认 sensitive。
53.外部分类器可以提高保护，降低需要用户或确定性规则。
54. Model / Runtime Binding 声明可处理数据、Retention、Training、Region 和 Capability。
55.复杂 Policy Engine 外置，Core 保留 data、capability、approval、budget、side-effect、expiry、revocation 最终检查。
56. ActionProposal 与 Action 分离。
57. Provider 调用前必须持久化 pending Action。
58. unknown Action 必须 reconciliation，不能盲目 retry。
59. Secret 与普通资产分离；标准导出只含 Secret Reference。
60.标准导出与加密完整设备备份是不同承诺。

### 实现与阶段

61.逻辑边界不等于微服务；默认模块化单体。
62. Phase 0–5 是同一目标架构的真子集。
63.参考实现为 Python、FastAPI、React + TypeScript + Vite、OpenAPI / JSON Schema、SSE、SQLite WAL、SQLAlchemy、Alembic。
64.进程内使用 Python Family Port；第一种隔离 Transport 是 UTF-8 NDJSON Message Envelope over stdio。
65. PostgreSQL 是第二 Canonical Repository Profile。
66.首批参考 Adapter 为 Deterministic Test、OpenAI Model 与 Process Runtime。
67.具体 Framework / SDK 不进入 Kernel、Profile Canonical Schema 或 Stable ID。

### Phase 3 State Profile

68. State 使用独立 `shadow.profile.state`，Canonical Envelope 只负责身份、Owner/Space、版本和 Commit。
69. Observation / StateProposal 只能经过 StateService 与 CommitAuthority，Source Adapter/Resolver 不得直接 Commit。
70. State freshness 使用 `fresh`、`stale`、`unknown` 稳定语义；TTL 到期不得继续返回 fresh。
71. Phase 3 首个 State 切片不新增数据库表、Proposal 审批表或 State 专用写入路由。

### Phase 3 Continuity Completion

ADR-0014：Phase 3 Continuity 与 State Profile 完成边界。

72. Durable Task 使用 typed Profile；Run success 不自动完成 Task。
73. Checkpoint/Handoff 只保存可审计 refs/digest；无 native resume 时只能创建新 Attempt，不能伪装原 Session 恢复。
74. Schedule/Clock/Resolver 只能产生 Observation/Trigger/Proposal，State condition 必须重新进入 Admission。
75. Migration/Integrity 是窄 Store capability，复用 Portable Export/Import，不引入通用 Job、Queue 或 Outbox。

### Phase 4 Action Lifecycle

ADR-0015：Phase 4 Action 生命周期与副作用安全边界。

76. Action 使用独立 typed Profile，Proposal、Approval、Result 和 Reconciliation 复用 Canonical Commit。
77. Action Proposal/Approval 复用通用 Proposal API，不新增 Action 创建路由或 Proposal 表。
78. Provider 调用前必须持久化 executing；Provider 不能直接 Commit。
79. low-risk 自动批准、medium-risk 需要 Approval、high-risk 确定性拒绝；unknown 必须 reconciliation，不能盲目 retry。
80. 首片不实现 Outbox、Router、Semantic Pulse、跨组件 Erasure、Backup、真实 Provider 或 Secret 读取。

### Phase 4 Durable Outbox

ADR-0016：Phase 4 Durable Outbox 最小可靠副作用边界。

81. Outbox 仅服务 allowlisted reliable side effect/emergency capability，不是通用 Queue、
    Event Bus、Workflow 或后台 Job 平台。
82. Provider 调用前必须提交 Outbox Intent；Adapter 只能返回 Result，不能直接 Commit。
83. `unknown` 必须通过 evidence-backed reconciliation 收敛或保持 unknown，不能盲目 retry；
    同一 dedup key 重放不创建新的 Intent、Result 或 Reconciliation。

### Phase 4 Router / Policy

ADR-0017：Phase 4 Deterministic Policy 与 Router Proposal 边界。

84. Policy Engine 只能提出 PolicyDecision，Router 只能提出 BindingProposal；Core 保留最终
    capability、data scope、budget、side effect、approval、expiry 和 revocation 检查。
85. `target_kind` 保持 namespaced open-world；candidate rank/fallback 不是授权，未知 target
    必须通过 Descriptor/Capability/Policy 检查后才能接受。

### Phase 4 Semantic Pulse

ADR-0018：Phase 4 Semantic Pulse Proposal Producer 边界。

86. Semantic Pulse 只能产生 Trigger、Observation 或 Proposal；work-bearing Proposal 必须
    重新进入 Admission，Pulse 不能直接创建 Task、Memory、State、Action 或 Run。
87. Pulse 是可关闭、可替换的可选 producer；budget、deadline、cooldown、evidence、source
    unavailable 和 dedup 状态必须诚实表达，不承诺跨进程 exactly-once。

### Phase 4 Erasure / Backup Metadata

ADR-0019：Phase 4 跨组件 Erasure 与 Backup Metadata 边界。

88. ErasureRequest 使用 scope、逐组件状态和 evidence 表达 quiesce/erase/失败/恢复；未确认
    组件不得被显示为 completed，Tombstone 不包含敏感原文。
89. Backup 只冻结加密 Export metadata、digest、manifest、opaque key ref、retention 和
    erase schedule；不保存 Secret、Provider 私有状态或不可重建索引。

## 何时必须新增 ADR

- 把概念移入或移出 Tiny Kernel；
- 改变 Profile 的事实所有权或 Authority；
- 改变 Proposal / Commit；
- 改变 work-bearing Admission；
- 把 Target Kind 改为封闭集合；
- 改变 Adapter Capability 诚实声明原则；
- 改变 Store Capability split；
- 允许 External Component 直接 Commit；
- 改变 Skill 内容标准或 Bundle / sidecar 边界；
- 允许复杂 Policy Engine 直接签发权限；
- 改变 Action pending / unknown / reconciliation；
- 改变用户删除、导出或迁移承诺；
- 引入 Event Sourcing、通用 Workflow、Plugin OS、Policy Language 或 Job Platform；
- 引入不可重建的外部私有状态；
- 改变参考实现且影响 Stable Contract。

## 核心原则

> **External intelligence proposes; Shadow authority commits.**

> **Tiny Kernel knows ownership and evolution, not every domain meaning.**

> **Typed Profiles preserve semantics without locking them into the Kernel.**

> **Replaceable components own intelligence, execution, protocols, and infrastructure.**

> **Users retain portable data and capability assets across component generations.**

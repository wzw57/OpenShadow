# OpenShadow 开发路线

本路线描述软件工程阶段；具体功能交付顺序见[分阶段实现计划](implementation-stages.md)。

## Stage 0：需求基线（已完成）

产物：[requirements.md](requirements.md)

已经确认：

- Shadow 是完整 Agent，Runtime 是内部可替换组件；
- 所有承载工作的请求经过 Shadow；
- 所有执行受治理，但不都经过 Agent Runtime；
- 用户长期资产独立于具体组件；
- 单用户优先，保留 Owner / Space；
- Memory 与外部原始资产分离；
- State 表达当前接受的现实状态；
- 用户拥有导出、迁移和最终删除权。

## Stage 1：责任边界（已完成并修订）

产物：[responsibility-matrix.md](responsibility-matrix.md)

最初完成 Authority / Canonical State / Intelligence / Execution 分配。Stage 4 Core Diet 进一步收紧为：

- KERNEL；
- CONTRACT-ONLY；
- PROFILE / EXTENSION；
- LATER PHASE / DERIVED。

核心结论：

- Tiny Kernel 只持有身份、归属、Canonical Envelope、Proposal / Commit、Admission、Run / Attempt、Binding 与可移植 Intent；
- Memory、State、Task、Action、Skill 和 Integration 使用 typed Profile；
- External Component 不能直接 Commit；
- 复杂智能、执行、协议和基础设施外置；
- 统一 UI 不建立万能聚合。

## Stage 2：关键用例（已完成，需遵守新内核边界）

产物：[use-cases/](use-cases/README.md)

覆盖：

1. 普通请求与拒绝；
2. Web 多端连接；
3. Model Worker；
4. Executable / Runner；
5. Workflow Target；
6. Run → Durable Task；
7. Runtime failure / handoff；
8. Memory candidate / correction / delete；
9. Observation / State；
10. Governed Action / reconciliation；
11. Store restricted mode；
12. Export / backup / erasure；
13. Integration / external assets；
14. Semantic Pulse。

用例行为不变，但解释方式调整：

- Memory / State / Task / Action 是官方 Profile；
- 执行使用 namespaced target_kind；
- 基础设施 Port 使用 family-specific Result；
- 只有 work-bearing input 创建 Root Run；
- 所有 Canonical change 统一走 Proposal / Commit。

## Stage 3：领域模型与状态机（基线已修订）

产物：

- [domain-model.md](domain-model.md)
- [state-machines.md](state-machines.md)

已冻结：

- CanonicalEnvelope；
- ProposalEnvelope / Commit；
- Principal / Owner / Space；
- Admission / Request / Run / Attempt；
- ExecutionBinding / CapabilityEnvelope；
- ProfileDescriptor；
- Run cancellation truth；
- Memory / Task / State / Action 的必要 Profile 状态；
- Domain Event、Outbox、OperationJob 的窄边界。

不冻结：

- 所有 Profile 未来字段；
- Target Kind 全集；
- Memory / State / Router 算法；
- 数据库物理模型；
- 微服务拓扑。

## Stage 4：完整技术架构与 Contract（已完成）

产物：

- [technical-architecture.md](technical-architecture.md)
- [implementation-stages.md](implementation-stages.md)
- [implementation-profile.md](implementation-profile.md)
- [contract-baseline.md](contract-baseline.md)
- [`contracts/`](../contracts/) JSON Schema、OpenAPI、fixtures 与声明式 Contract Tests
- [ADR](adr/README.md)

### 已完成

- Tiny Kernel + typed Profile；
- Proposal / Validate / Commit 泛化；
- work-bearing Admission；
- namespaced target_kind；
- minimal AdapterDescriptor；
- Runtime base Port + optional capabilities；
- family-specific Port Result；
- Store Capability split；
- Agent Skills compatibility；
- deterministic Policy minimum；
- narrow Event / Outbox / OperationJob；
- 模块化单体参考部署；
- Phase 0–5 实现顺序；
- Python / FastAPI / React / SQLite 参考 Profile；
- Phase 0–1 字段级 JSON Schema；
- ProfileDescriptor / MutationInputEnvelope；
- AdapterDescriptor / Capability / Binding / CapabilityEnvelope；
- Runtime Message / Request / Event / Error；
- Canonical Repository CommitPlan / Result；
- Agent Skills fixtures 与 deterministic digest contract；
- 声明式 Contract Test cases；
- OpenAPI 3.1。

### Stage 4 完成条件

- Schema、offline references、fixtures 与 OpenAPI 的工件验证已完成；
- 全仓术语与语义一致性复核已完成；
- Stage 4 PR 已 review 并合并；
- Stage 4 ADR 与 Implementation Profile 已切换为 Accepted。

Stage 4 不再继续扩展概念清单，进入 Phase 0–1 实现。

## Stage 5：实现启动与分阶段交付

Stage 5 不是重新设计完整架构，而是按[分阶段实现计划](implementation-stages.md)交付：

1. Phase 0：Kernel Foundation；
2. Phase 1：Personal Shadow Loop；
3. Phase 2：Memory & Capability Profiles；
4. Phase 3：Continuity & State Profile；
5. Phase 4：Action & Proactivity；
6. Phase 5：Multi-endpoint & Multi-user。

首个开发目标是 Phase 0–1 纵向闭环，但代码结构服务完整目标架构，不把短期范围冻结为长期内核。

当前交付状态：Phase 0–1 的 Python reference slice 已在
`stage5/phase0-1-implementation` 分支实现并通过本地 Contract / Repository / API
测试。已覆盖 Kernel Port、SQLite Store Adapter、Commit / Admission、Binding、
Deterministic Adapter、Conversation / Message、Run / Attempt、SSE、幂等重放与 Store
不可用路径，以及最小 Memory Candidate → Commit。未获单独闸门授权的 Phase 2–5 能力继续
只维护已接受的 Contract 与退出条件，暂不实现未授权业务能力。Phase 2 首个 Memory 生命周期切片已获
ADR-0005 接受并合并到 `main`，已交付 correction、merge（Service / Contract only）和
logical delete；详见 [Phase 2 状态](phase2-memory-lifecycle-status.md)。
Phase 2 第二切片已按 ADR-0006 合并 Recall / Maintenance Adapter；派生 Index rebuild
已按 ADR-0007 获准并合并第三切片实现，详见
[第三切片状态](phase2-derived-index-status.md)。下一切片 source-dependent invalidation
已按 ADR-0008 完成设计并进入实现，详见
[第四切片状态](phase2-source-invalidation-status.md)。SkillAsset sidecar 第五切片已按
ADR-0009 接受并合并实现，详见 [第五切片状态](phase2-skillasset-status.md)；Integration、
Portable Import/restore 和 Physical erase 仍须分别完成设计接受后实现。
Integration 第六切片已完成并合并，详见 [第六切片状态](phase2-integration-status.md)。
Portable Import/restore 第七切片已按 ADR-0011 接受并合并实现，详见
[第七切片状态](phase2-portable-import-status.md)。Physical erase 第八切片已按 ADR-0012
接受并合并实现，详见 [第八切片状态](phase2-physical-erase-status.md)。
Phase 3 首个 State Profile 切片已按 ADR-0013 完成设计闸门接受并实现，详见
[Phase 3 State Profile 状态](phase3-state-profile-status.md)。Durable Task、Checkpoint/Handoff
和其他 Phase 3 能力仍未授权实现。
Phase 3 完成闸门已按 ADR-0014 接受，剩余连续性、Schedule/Clock 和 Migration/Integrity
切片正在实现，详见 [Phase 3 完成状态](phase3-completion-status.md)。

## 延后实现与重新评估

以下只有在真实用例和测量证据出现后实现：

- 多 Runtime 自动组合；
- 多 Memory Engine 融合；
- 复杂 Router / Policy Language；
- 领域 State Ontology；
- 通用 Workflow 或 Job Platform；
- 分布式 Event Bus；
- 完整家庭音频；
- 多 Space ACL；
- 跨设备同步；
- 微服务拆分。

重新评估条件：

- Profile 无法表达必要语义；
- Kernel 控制原语不足；
- Capability Negotiation 无法接入主要组件；
- 模块化单体出现可测量瓶颈；
- 用户迁移或删除承诺无法验证；
- 标准 Skill 兼容不足以表达真实需求。

## 路线验收原则

1. 不重造已有优秀基础项目；
2. External Component 可以替换；
3. Canonical Asset 不随组件消失；
4. Profile 可以升级且有语义 Migration；
5.所有权威状态通过 Shadow Commit；
6.新 target kind 不修改 Core 主流程；
7. Adapter 不伪造 Capability；
8. Store Contract 不膨胀成数据库产品；
9. Skill Bundle 保持标准；
10.用户始终拥有查看、纠正、撤销、删除、导出和迁移权。

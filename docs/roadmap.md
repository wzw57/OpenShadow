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

- Tiny Core 只持有身份、归属、Canonical Envelope、Proposal / Commit、Admission、Run / Attempt、Binding 与可移植 Intent；
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

## Stage 4：完整技术架构与 Contract（进行中）

产物：

- [technical-architecture.md](technical-architecture.md)
- [implementation-stages.md](implementation-stages.md)
- [implementation-profile.md](implementation-profile.md)
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
- Python / FastAPI / React / SQLite 参考 Profile。

### Stage 4 剩余工程化工作

1. 冻结 Phase 0–1 字段级 JSON Schema；
2. 冻结 ProfileDescriptor / ProposalEnvelope；
3. 冻结 AdapterDescriptor / Capability；
4.定义 Runtime base Port 消息；
5.定义 Canonical Repository Capability；
6.提供 Agent Skills fixture；
7.提供 Contract Test cases；
8.生成 OpenAPI；
9.完成 PR review 并合并。

完成后不再继续扩展概念清单，进入实现。

## Stage 5：实现启动与分阶段交付

Stage 5 不是重新设计完整架构，而是按[分阶段实现计划](implementation-stages.md)交付：

1. Phase 0：Kernel Foundation；
2. Phase 1：Personal Shadow Loop；
3. Phase 2：Memory & Capability Profiles；
4. Phase 3：Continuity & State Profile；
5. Phase 4：Action & Proactivity；
6. Phase 5：Multi-endpoint & Multi-user。

首个开发目标是 Phase 0–1 纵向闭环，但代码结构服务完整目标架构，不把短期范围冻结为长期内核。

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

# OpenShadow 开发路线

- 状态：Stage 3 领域模型已收紧，Stage 4 完整技术架构设计进行中
- 原则：先明确完整需求，再决定 Core 与 External 的边界，最后选择具体实现

OpenShadow 不按外部项目名称制定路线，也不因为某项能力可能有用就提前实现。每个阶段都必须产生可审阅的工程产物和退出条件。

## Stage 0：需求基线

目标：统一产品定义、术语、用户资产和顶层行为。

需要完成：

- 明确 Shadow 是完整 Agent，Agent Runtime 是内部可替换组件；
- 明确所有请求经过 Shadow，但不要求都经过 Agent Runtime；
- 明确最小 Run 与 Durable Task 的差异；
- 明确 Canonical Memory、Observation、World State 和外部信息资产的差异；
- 明确 Execution Target、Executable Asset、Skill、Extension、Integration、Capability 和 Provider Binding；
- 明确 System Health Heartbeat 与可选 Semantic Pulse 的差异；
- 明确 Owner 可以是 User 或 Space，并从第一版保存显式归属；
- 明确本地优先是控制、可迁移和可验证，而非固定物理位置；
- 明确数据分级、Model Binding、Secret、删除和 Store 故障边界；
- 明确单用户优先但不封死未来扩展；
- 删除没有经过讨论的具体组件选择和实现方案。

退出条件：

- README、Requirements 和 Architecture 使用相同术语；
- 文档不把具体数据库、Runtime、Model、Runner、Router 或 Memory 项目写成既定选择；
- 已确认需求与推测性设计明确分离。

## Stage 1：Core / External 责任矩阵（已完成）

正式产物：[Core / External 责任矩阵](responsibility-matrix.md)

对每项需求分别确定：

~~~text
Authority
    谁决定并提交最终状态

Canonical State
    哪些数据不可丢失，谁定义其语义

Intelligence
    哪个可替换组件提供算法和语义判断

Execution
    哪个组件完成具体工作
~~~

重点领域：

- Request / Run；
- Durable Task / Checkpoint；
- Execution Dispatch / Binding；
- Agent Runtime / Model Worker / Deterministic Runner；
- Routing；
- Memory；
- Observation / World State；
- Durable Store；
- Skill / Executable Asset；
- Extension / Integration；
- Capability / Provider；
- Event / Scheduler / System Health；
- Owner / Personal Space / Home Space；
- Data Classification / Model Data Boundary；
- Retention / Erasure；
- Export / Full Backup / Secret；
- Store Availability / Outbox；
- Context；
- User Interface / Voice。

退出条件：

- 每项能力都明确 Core 持有什么 Contract；
- 每项能力都明确哪些实现必须外置；
- Core 中不存在仅因“以后可能需要”而加入的机制。

完成结论：

- 13 个能力域已分别明确 Authority、Canonical State、Intelligence 和 Execution；
- 已列出 Core 必须实现与必须外置的完整清单；
- Request / Run / Attempt / Durable Task 关系和取消语义已经冻结；
- External Component 统一返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage，不持有权威提交路径；
- Stage 2 用例可以直接引用责任矩阵确定参与者。

## Stage 2：关键用例（已完成）

正式产物：[关键用例目录](use-cases/README.md)

先设计用户可观察行为，不设计数据库表。

第一批用例：

1. 普通请求经过 Shadow 并产生最小 Run；
2. 普通 Run 晋升为 Durable Task；
3. Agent Runtime 执行、失败和恢复；
4. Runtime A 到 Runtime B 接力；
5. 单次 Model Worker 完成分类或提取；
6. 已登记 Executable Asset 由 Runner 执行；
7. 静态规则或 Router Proposal 选择 Execution Target；
8. Memory Component 从交互形成 Candidate；
9. Shadow 提交 Canonical Memory；
10. 周期性 Memory 整理；
11. Source Connector 提交 Observation；
12. World State 更新、过期为 stale / unknown；
13. World State 条件触发受治理的 Run 或 Durable Task；
14. 按需访问外部信息资产；
15. 安装和配置 Integration；
16. 执行受治理的外部 Action；
17. System Health Heartbeat 检测故障且不依赖模型；
18. Semantic Pulse 提出建议但被权限或预算拒绝；
19. 更换 Agent Runtime、Memory Intelligence、Runner 或 Model；
20. 更换 Durable Store；
21. 导出和恢复 Shadow 长期资产；
22. 将个人资产和家庭公共状态分别归属 User 与 Home Space；
23. 未知敏感度默认 sensitive，分类器不能自行降低；
24. Model Binding 拒绝超出声明数据边界的上下文；
25. 删除 Memory 并追踪派生组件的 Erasure 状态；
26. 删除 Integration 后状态进入 source unavailable 和 stale / unknown；
27. Primary Store 故障时阻止未记录副作用；
28. 使用可靠 Outbox 执行预先配置的紧急能力；
29. 分别验证标准可移植导出和加密完整备份。

每个用例需要：

- Actor；
- Trigger；
- Preconditions；
- Main Flow；
- Failure Flow；
- Durable State Changes；
- External Side Effects；
- Acceptance Criteria。

退出条件：

- 正常和异常路径均可观察、可测试；
- 不依赖尚未选择的具体外部项目；
- 关闭 Router 和 Semantic Pulse 后，基础系统仍然正确运行。

草案完成结论：

- Stage 2 的 19 个用例覆盖交互准入、Web 多端、执行、连续性、Memory、World State、外部动作、Store 故障、迁移、Erasure、Integration、按需资产访问和 Semantic Pulse；Stage 4 另增 1 个 Workflow Target 用例；
- 每个用例均包含 Actor、Trigger、Preconditions、正常流程、失败流程、持久状态、外部副作用、Policy 与验收条件；
- 用例直接引用 Stage 1 责任边界，不选择具体数据库、模型、Runtime 或 Provider；
- 已审阅并合并为 Stage 2 正式基线。

## Stage 3：领域模型与状态机（基线已形成）

初始产物：

- [领域模型](domain-model.md)
- [状态机基线](state-machines.md)

根据用例冻结最小领域对象和状态机。

本阶段采用反过度设计约束：

- Phase 0–1 覆盖工程基础与个人 Shadow 对话执行闭环；
- Phase 2 实现 Canonical Memory 与能力资产；
- Phase 3 实现 Durable Task、World State 和长期连续性；
- Phase 4 实现受治理 Action、Router、Pulse、Outbox 和跨组件 Erasure；
- Phase 5 实现多端与多用户演进；
- 未来兼容对象可以 Contract-only，不要求在首次实现时创建空模块；
- 不为每个 Record 创建 Aggregate、Repository、Service 或状态机。

优先顺序：

1. Request / Run；
2. Durable Task；
3. Execution Requirements / Binding / Target Descriptor；
4. Runtime Checkpoint / Semantic Checkpoint；
5. Memory Candidate / Canonical Memory；
6. Observation / World State Projection；
7. Executable Asset；
8. Owner / Space / created_by；
9. Data Classification / Retention Policy；
10. Capability Envelope / Routing Rule；
11. Erasure Request / Tombstone；
12. Extension / Integration；
13. Capability Request / Action；
14. Migration / Standard Export / Full Backup。

退出条件：

- 对象只包含长期稳定语义；
- Runtime、Model、Runner 和 Memory Engine 私有状态不进入 Canonical Model；
- 状态转换具有明确提交者和失败语义；
- World State 明确 fresh、stale 和 unknown，而不假设实时一致；
- Aggregate 数量经过收紧，不把分析候选直接变成实现模块；
- Phase 0–1 可以在不实现 Router、Pulse、Action、World State 或多用户的情况下闭环；
- 后续 Phase 与 Contract-only 能力不阻塞首批实现，也不从完整架构中删除。

## Stage 4：完整技术架构与 Adapter Contract（进行中）

正式产物：

- [完整技术架构](technical-architecture.md)
- [分阶段实现计划](implementation-stages.md)
- [参考实现 Profile](implementation-profile.md)

本阶段不再把 MVP 当作设计边界。先定义完整 Shadow 的长期逻辑架构，再按 Phase 0–5 逐步实现。完整架构包含：

- Interaction Plane；
- Access & Admission；
- Shadow Core；
- Execution Plane；
- Adapter Control Plane；
- Canonical State Plane；
- Replaceable Infrastructure；
- External Implementations and Sources。

已冻结的顶层决定：

- 逻辑架构与部署拓扑分离，默认模块化单体起步；
- Web 是第一客户端，但 Core 使用稳定 API 支持未来多端；
- 所有触发统一进入 Admission；
- Execution Mode 包含 Agent Runtime、Direct Model、Deterministic Program、Workflow 和 Capability Provider；
- Shadow Core 持有 Authority，外部组件只返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage；
- Adapter 使用统一 Manifest、Capability Negotiation、Version、Health、Data Boundary 和 Contract Test；
- Canonical State、Derived State 和 External Source Asset 分离；
- Domain Event 使用最小信封，不强制 Event Sourcing；
- 跨 Adapter 流程通过幂等、状态机和 reconciliation 恢复；
- 完整目标架构先冻结，实现阶段不得创建冲突旁路。

参考实现已经确定 Python、FastAPI、React + TypeScript + Vite、REST / OpenAPI、SSE、JSON Schema、进程内 Python Port、进程外 JSON-RPC-style stdio Transport、SQLite WAL、SQLAlchemy、Alembic、PostgreSQL Profile，以及三类 Reference Execution Adapter。

后续在本阶段只需继续冻结：

- Port 的字段级请求、响应与错误 Schema；
- Adapter Manifest 与版本协商精确字段；
- API、Migration 和 Contract Test 的可执行验收样例。

退出条件：

- 完整逻辑模块、依赖方向、Authority 和信任边界明确；
- 每类执行都能映射到统一 Run / Binding / Attempt；
- 每类长期数据都能归类为 Canonical、Derived 或 External；
- Adapter 的共同生命周期与 Capability Negotiation 明确；
- Phase 0–5 的实施顺序不会改变 Canonical 身份和核心契约；
- 字段级 Contract 通过样例和 Fake Adapter 验证后可以直接进入编码。

## Stage 5：实现启动与分阶段交付

Stage 5 不再为每项能力建立一套新的设计阶段。全部实现按照 [分阶段实现计划](implementation-stages.md) 在同一目标架构上推进：

1. Phase 0：工程基础；
2. Phase 1：个人 Shadow 基本闭环；
3. Phase 2：Memory 与能力资产；
4. Phase 3：任务连续性与 World State；
5. Phase 4：受治理动作与主动能力；
6. Phase 5：多端与多用户演进。

首批开发从 Phase 0–1 开始：

~~~text
Web
   ↓
Admission / Conversation / Message
   ↓
Request / Root Run / Execution Attempt
   ↓
Static Execution Binding + Capability Envelope
   ↓
Deterministic Test Adapter / Real Execution Adapter
   ↓
Result / Assistant Message
   ↓
SQLite Durable Store Adapter
~~~

首批开发同时建立完整架构需要的基础身份和边界：

- stable_id、schema_version、owner_ref 和 space_id；
- checked-in JSON Schema / OpenAPI；
- Adapter Manifest 与 Capability Negotiation；
- Store Migration 和 Integrity；
- Fake Adapter 与 Contract Test；
- Domain 不依赖 FastAPI、SQLAlchemy、React 或具体 Runtime SDK。

后续 Phase 只增加实现，不替换 Phase 0–1 的 Canonical Identity、Authority、Binding 或 Adapter 边界。每个 Phase 的详细范围、非目标和退出条件以 [分阶段实现计划](implementation-stages.md) 为唯一事实源。

Stage 5 的总体退出条件：

- Phase 0–1 可以安装、启动、升级、回滚和恢复；
- 至少一个真实 Execution Adapter 与 Deterministic Test Adapter 通过相同 Contract；
- Primary Store、Runtime 和 Model 实现可以替换；
- 后续 Phase 不需要建立绕过 Admission、Authority 或 Port 的新路径；
- 用户资产可以通过标准格式导出并验证完整性。

## 延后实现与重新评估

以下内容已经保留架构边界，但在相应 Phase 前不冻结内部实现细节：

- 多 Memory Component 自动组合；
- 高级动态 Capability / Model Router；
- 常驻 Semantic Pulse 的频率和模型选择；
- 多用户成员、角色、邀请和家庭权限；
- 分布式麦克风与扬声器；
- 多节点同步；
- Plugin Marketplace；
- 微服务和高可用集群；
- 通用 Workflow Engine；
- 领域数字孪生和复杂状态预测。

## 路线验收原则

路线中的每个阶段都必须继续满足：

1. 不重造已有优秀基础项目；
2. External Component 可以替换；
3. Canonical Asset 不随组件消失；
4. 所有权威状态通过 Shadow 提交；
5. 所有执行经过 Shadow 治理，但不强制经过 Agent Runtime；
6. 基础正确性不依赖任何 LLM 心跳；
7. 所有 Canonical Asset 都有显式 Owner 和 Space；
8. 数据披露受 Model / Provider Binding 与敏感度约束；
9. 用户能够查看、纠正、物理删除和导出长期资产；
10. Store 故障时不产生无法审计的现实副作用；
11. 新机制只在真实用例证明必要后加入。

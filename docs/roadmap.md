# OpenShadow 开发路线

- 状态：Stage 1 责任矩阵完成，准备进入 Stage 2 关键用例
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
- External Component 统一通过 Proposal / Result 返回，不持有权威提交路径；
- Stage 2 用例可以直接引用责任矩阵确定参与者。

## Stage 2：关键用例（下一阶段）

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

## Stage 3：领域模型与状态机

根据用例冻结最小领域对象和状态机。

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
- World State 明确 fresh、stale 和 unknown，而不假设实时一致。

## Stage 4：Port Contract 与 Adapter SDK

定义最小、版本化的 Port：

- Durable Store Port；
- Agent Runtime Port；
- Model Worker Port；
- Deterministic Runner Port；
- Routing Port；
- Memory Intelligence Port；
- Asset / State Source Port；
- Capability Provider Port；
- Interaction Port；
- Infrastructure Port。

同时定义：

- Extension Manifest；
- Target / Capability Declaration；
- Capability Envelope；
- Model Data Boundary Declaration；
- Permission / Data Classification Declaration；
- Retention / Erasure Contract；
- Store Availability / Outbox Contract；
- Version Negotiation；
- Health Contract；
- Contract Test Suite。

退出条件：

- 可以用 Fake Adapter 完成所有核心用例；
- Contract 不依赖某个具体外部项目；
- Optional Capability 可以演进而不扩大基础接口；
- Router 只能返回 Binding Proposal，Source 只能返回 Observation Proposal。

## Stage 5：最小纵向闭环

实现第一个端到端闭环：

~~~text
Request
   ↓
Minimal Run
   ↓
Static Execution Binding
   ↓
Replaceable Agent Runtime
   ↓
Result / Memory Candidate
   ↓
Shadow Authority
   ↓
Replaceable Durable Store
~~~

同时验证：

- Core 重启恢复；
- Runtime 删除后 Canonical State 仍存在；
- Memory Component 删除后 Canonical Memory 仍存在；
- 用户可以查看和导出长期资产；
- 所有 Canonical Asset 都有显式 owner_ref 和 space_id；
- 默认 Personal Space 与 Home Space 可以恢复。

退出条件：

- 闭环中至少包含一个真实 Runtime Adapter；
- Durable Store 和 Memory Intelligence 都通过 Port 接入；
- 没有外部组件直接写 Shadow 权威状态。

## Stage 6：Execution Plane 与 Task Continuity

实现：

- Execution Requirements / Binding；
- Model Worker 直接执行；
- Executable Asset 与 Runner 执行；
- 静态路由规则；
- Durable Task lifecycle；
- Runtime Checkpoint Reference；
- Semantic Checkpoint；
- Capability Envelope；
- Runtime 跨边界 Usage / Action Record；
- deterministic health / lease / timeout；
- pause / resume / cancel；
- failure recovery；
- cross-runtime handoff。

退出条件：

- 分类或脚本任务不需要启动 Agent Runtime；
- 每次 Target Binding 与版本可追踪；
- Runtime A 中断后，Runtime B 能根据 Shadow 状态继续长期工作；
- 不需要同步 Runtime 内部 Planner 或 Subtask Graph；
- 模型不可用不会破坏健康检查和恢复机制。

## Stage 7：Memory 生命周期

实现：

- Canonical Memory；
- Evidence Reference；
- Memory Candidate；
- Candidate commit；
- user correction / delete / supersede；
- periodic consolidation trigger；
- Recall permission boundary；
- derived state rebuild。

退出条件：

- 更换 Memory Intelligence 不迁移或丢失 Canonical Memory；
- 外部资料只在需要时通过 Connector 读取；
- Memory 整理失败不破坏已有 Memory。

多 Memory Component 的动态组合、路由和结果融合不在本阶段实现。

## Stage 8：Observation 与 World State

实现：

- Observation Proposal；
- subject / property / value 和关系；
- provenance、observed_at、received_at；
- TTL / expires_at；
- fresh / stale / unknown；
- conflict preservation 与 accepted projection；
- Canonical World State 恢复；
- type-specific Observation Retention；
- State Resolver Proposal；
- source unavailable；
- State Source Adapter；
- World State 条件触发；
- 用户查看、纠正和使状态失效。

退出条件：

- 移除 State Source 不会伪造当前状态；
- 过期数据自动变为 stale 或 unknown；
- 外部 Source 不能绕过 Shadow 提交 World State；
- 领域采集、复杂融合与预测不进入 Core。

## Stage 9：归属、隐私、保留与删除

实现：

- User / Space Owner Reference；
- Personal Space / Home Space Record；
- created_by 与 owner_ref 分离；
- public / personal / sensitive / restricted；
- Model Binding 数据边界与上下文裁剪；
- 分类器只升不降规则；
- logical delete / restore / physical erase；
- source_dependency；
- Erasure Request 与组件完成状态；
- Secret Reference。

退出条件：

- 家庭公共状态可以归 Home Space；
- 未知数据默认 sensitive；
- 超出 Model Binding 的上下文不会发送；
- 删除请求能够传播到受管派生组件；
- pending / unreachable 不会被报告为删除成功。

## Stage 10：能力资产与外部动作

实现：

- Skill Asset；
- Executable Asset 管理；
- Extension Registry；
- Integration Registry；
- MCP Connection；
- Capability Registry；
- Provider Binding；
- Policy Enforcement；
- Approval；
- Action Ledger；
- Unknown Outcome / Reconciliation。

退出条件：

- 用户可以查看和迁移已配置的能力资产；
- 外部副作用不会绕过 Shadow 治理路径。

## Stage 11：升级、可移植性与 Store 故障

实现：

- Schema Version；
- Export / Import；
- Migration；
- Integrity Verification；
- component compatibility check；
- Durable Store replacement；
- standard portable export；
- separately encrypted full-device backup；
- Store availability state；
- restricted mode；
- persistent Outbox 和 reconciliation；
- backup metadata。

退出条件：

- 可以在新环境恢复 Shadow Canonical Assets；
- 数据库实现替换后 Stable ID、关系和历史保持一致；
- 派生数据可以重建；
- Secret 不进入标准导出；
- Store 故障时未记录的现实副作用被阻止；
- 紧急 Outbox 操作可以幂等恢复和 reconciliation。

## Stage 12：使用便利性

在 Core 和 Adapter Contract 稳定后，提供统一用户体验：

- Reference Shell；
- 管理界面；
- Approval Inbox；
- Integration 配置；
- Memory、World State、Skill 和 Executable Asset 管理；
- Voice / Device Endpoint 接入。

具体 Voice、STT、TTS、设备协议和 UI 技术继续由可替换组件提供。

## Stage 13：可选主动智能

只有基础正确性和成本边界可观测后，再评估：

- Semantic Pulse；
- 多模型智能路由；
- Target 质量、成本和延迟评估；
- 主动 Recall 与建议；
- 多 Memory Component 组合与融合。

退出条件由真实使用数据另行定义。这些能力全部可以关闭或替换，且不得成为系统健康、状态过期、权限执行或任务恢复的依赖。

## 延后设计

以下内容保留兼容可能，但在基础闭环完成前不设计：

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

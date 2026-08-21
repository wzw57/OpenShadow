# OpenShadow 开发路线

- 状态：需求与责任边界收紧阶段
- 原则：先明确完整需求，再决定 Core 与 External 的边界，最后选择具体实现

OpenShadow 不按外部项目名称制定路线，也不因为某项能力可能有用就提前实现。每个阶段都必须产生可审阅的工程产物和退出条件。

## Stage 0：需求基线

目标：统一产品定义、术语、用户资产和顶层行为。

需要完成：

- 明确 Shadow 是完整 Agent，Runtime 是内部可替换组件；
- 明确所有请求经过 Shadow；
- 明确最小 Run 与 Durable Task 的差异；
- 明确 Canonical Memory、外部信息资产和 Memory Intelligence 的差异；
- 明确 Skill、Extension、Integration、Capability 和 Provider Binding；
- 明确单用户优先但不封死未来扩展；
- 删除没有经过讨论的具体组件选择和实现方案。

退出条件：

- README、Requirements 和 Architecture 使用相同术语；
- 文档不把具体数据库、Runtime 或 Memory 项目写成既定选择；
- 已确认需求与推测性设计明确分离。

## Stage 1：Core / External 责任矩阵

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
- Durable Task；
- Runtime；
- Memory；
- Durable Store；
- Skill；
- Extension / Integration；
- Capability / Provider；
- Event / Scheduler；
- Context；
- User Interface / Voice。

退出条件：

- 每项能力都明确 Core 持有什么 Contract；
- 每项能力都明确哪些实现必须外置；
- Core 中不存在仅因“以后可能需要”而加入的机制。

## Stage 2：关键用例

先设计用户可观察行为，不设计数据库表。

第一批用例：

1. 普通请求经过 Shadow 并产生最小 Run；
2. 普通 Run 晋升为 Durable Task；
3. Runtime 执行、失败和恢复；
4. Runtime A 到 Runtime B 接力；
5. Memory Component 从交互形成 Candidate；
6. Shadow 提交 Canonical Memory；
7. 周期性 Memory 整理；
8. 按需访问外部信息资产；
9. 安装和配置 Integration；
10. 执行受治理的外部 Action；
11. 更换 Memory Intelligence；
12. 更换 Durable Store；
13. 导出和恢复 Shadow 长期资产。

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
- 不依赖尚未选择的具体外部项目。

## Stage 3：领域模型与状态机

根据用例冻结最小领域对象和状态机。

优先顺序：

1. Request / Run；
2. Durable Task；
3. Runtime Binding / Checkpoint；
4. Memory Candidate / Canonical Memory；
5. Extension / Integration；
6. Capability Request / Action；
7. Migration / Export。

退出条件：

- 对象只包含长期稳定语义；
- Runtime 私有状态和 Engine 私有状态不进入 Canonical Model；
- 状态转换具有明确提交者和失败语义。

## Stage 4：Port Contract 与 Adapter SDK

定义最小、版本化的 Port：

- Durable Store Port；
- Runtime Port；
- Memory Intelligence Port；
- Source Connector Port；
- Capability Provider Port；
- Interaction Port；
- Infrastructure Port。

同时定义：

- Extension Manifest；
- Capability Declaration；
- Permission Declaration；
- Version Negotiation；
- Health Contract；
- Contract Test Suite。

退出条件：

- 可以用 Fake Adapter 完成所有核心用例；
- Contract 不依赖某个具体外部项目；
- Optional Capability 可以演进而不扩大基础接口。

## Stage 5：最小纵向闭环

实现第一个端到端闭环：

~~~text
Request
   ↓
Minimal Run
   ↓
Replaceable Runtime
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
- 用户可以查看和导出长期资产。

退出条件：

- 闭环中至少包含一个真实 Runtime Adapter；
- Durable Store 和 Memory Intelligence 都通过 Port 接入；
- 没有外部组件直接写 Shadow 权威状态。

## Stage 6：Task Continuity 与 Runtime Handoff

实现：

- Durable Task lifecycle；
- Runtime Checkpoint Reference；
- Semantic Checkpoint；
- Runtime health；
- pause / resume / cancel；
- failure recovery；
- cross-runtime handoff。

退出条件：

- Runtime A 中断后，Runtime B 能根据 Shadow 状态继续长期工作；
- 不需要同步 Runtime 内部 Planner 或 Subtask Graph。

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

## Stage 8：能力资产与外部动作

实现：

- Skill Asset；
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

## Stage 9：升级与可移植性

实现：

- Schema Version；
- Export / Import；
- Migration；
- Integrity Verification；
- component compatibility check；
- Durable Store replacement；
- backup metadata。

退出条件：

- 可以在新环境恢复 Shadow Canonical Assets；
- 数据库实现替换后 Stable ID、关系和历史保持一致；
- 派生数据可以重建。

## Stage 10：使用便利性

在 Core 和 Adapter Contract 稳定后，提供统一用户体验：

- Reference Shell；
- 管理界面；
- Approval Inbox；
- Integration 配置；
- Memory 和 Skill 管理；
- Voice / Device Endpoint 接入。

具体 Voice、STT、TTS、设备协议和 UI 技术继续由可替换组件提供。

## 延后设计

以下内容保留兼容可能，但在基础闭环完成前不设计：

- 多 Memory Component 自动组合；
- 动态 Capability Router；
- 多用户和家庭权限；
- 分布式麦克风与扬声器；
- 多节点同步；
- Plugin Marketplace；
- 微服务和高可用集群；
- 通用 Workflow Engine；
- 多模型智能路由。

## 路线验收原则

路线中的每个阶段都必须继续满足：

1. 不重造已有优秀基础项目；
2. External Component 可以替换；
3. Canonical Asset 不随组件消失；
4. 所有权威状态通过 Shadow 提交；
5. 用户能够查看、纠正、删除和导出长期资产；
6. 新机制只在真实用例证明必要后加入。

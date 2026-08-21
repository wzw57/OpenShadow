# Architecture Decision Records

OpenShadow 计划长期运行，而 Runtime、Memory Intelligence、数据库、模型、Runner、Router、Provider 和交互技术会持续变化。任何改变 Shadow Core 与可替换组件边界的决定，都必须记录其原因、后果和重新评估条件。

## 已接受 ADR

- [ADR-0001：完整目标架构与分阶段实现](0001-target-architecture-and-phased-delivery.md)
- [ADR-0002：第一套参考实现 Profile](0002-reference-implementation-profile.md)

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

什么问题迫使我们作出这个决定？

## Decision

决定采用什么边界或行为？

## Rationale

为什么采用这个方案？

## Alternatives considered

考虑过哪些方案，为什么没有采用？

## Consequences

正面和负面后果是什么？

## Revisit triggers

什么证据或技术变化会触发重新评估？
~~~

## 已确认决策索引

以下索引用于检查文档一致性。影响 Core、Canonical State 或实现 Profile 的成组决定已经通过上述 ADR 记录；未来发生边界变化时再新增独立 ADR。

1. **Shadow 是完整 Agent，Agent Runtime 是 Shadow 内部可替换组件。**
2. **所有输入经过 Shadow Admission；被接受的 Request 创建 Root Run，准入失败只创建最小 Admission Record。**
3. **所有执行由 Shadow 绑定和治理，但并非所有执行都经过 Agent Runtime。**
4. **Shadow Core 只持有 Domain Contract、Authority、Continuity、最小 World State、Execution Dispatch、Extension Control 和 Portability。**
5. **Agent Runtime、Model Worker、Deterministic Runner、Workflow Target 和 Capability Provider 是不同的 Execution Target。**
6. **智能 Routing 外置；Router 只提出 Binding Proposal，Core 校验并提交 Binding。**
7. **脚本和固定程序是可迁移的 Executable Asset，实际运行时与隔离由 Runner 提供。**
8. **Runtime 持有执行分解，Shadow 持有 Durable Task。**
9. **Runtime Handoff 使用 Semantic Checkpoint，不迁移隐藏推理状态。**
10. **Canonical Memory 属于 Shadow，Memory Intelligence 可以替换。**
11. **数据库引擎通过 Durable Store Port 接入，不定义 Shadow Domain Semantics。**
12. **派生索引、Embedding、Graph、Projection 和 Engine State 可以删除重建。**
13. **外部信息资产默认只登记和按需访问，Shadow 不负责复制和长期存储其原始内容。**
14. **World State 是由 Observation 形成的最小当前状态投影，不是领域数字孪生。**
15. **State Source 只提交 Observation Proposal，不能直接修改 World State。**
16. **Skill、Executable Asset、Extension、Integration 和 MCP Connection 是用户长期能力资产。**
17. **External Component 只能返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage，不能绕过 Shadow 提交权威状态。**
18. **System Health Heartbeat 必须确定性运行，不依赖 LLM。**
19. **Semantic Pulse 是可选、可替换、仅能提议的主动智能组件。**
20. **具体基础技术优先复用外部项目，通过 Adapter 组合。**
21. **近期实现单用户场景，但稳定 Contract 不封死未来多用户可能。**
22. **Accepted World State 是可恢复、可迁移、允许过期的 Canonical State。**
23. **Observation 使用类型级 Retention Policy，不要求全部永久保存。**
24. **用户明确状态优先，但更新、更可靠的 Observation 可以替换；复杂冲突由外部 State Resolver 提议。**
25. **所有 Canonical Asset 从第一版具有 Owner Reference 和 Space ID，Owner 可以是 User 或 Space。**
26. **第一版只实现正式 Personal Space 与隐式 Home Space，不实现成员、角色或共享。**
27. **家庭公共状态归 Home Space，而不是固定归某个用户。**
28. **本地优先约束用户控制、可迁移和可验证，不冻结 Store 的物理位置。**
29. **Core 执行 public、personal、sensitive、restricted 四级数据边界；未知默认 sensitive。**
30. **外部分类器可以提高敏感度，但不能自行降低。**
31. **Model Binding 必须声明数据、Memory、World State、外部资产、Retention、Training 和地域边界。**
32. **Secret 属于用户能力资产，但标准导出只包含 Secret Reference；完整备份必须独立加密授权。**
33. **Canonical Memory 默认先逻辑删除，用户保留最终物理清除权。**
34. **统一 Erasure Request 追踪受管组件删除状态，无法确认时不得报告成功。**
35. **标准可移植导出与完整设备备份是不同的兼容和安全承诺。**
36. **Primary Store 故障时进入受限模式，未记录现实副作用默认禁止。**
37. **只有预先配置的紧急能力可以先写可靠持久 Outbox，再执行并恢复 reconciliation。**
38. **被接受的 Request 是不可变准入记录，并创建且只创建一个 Root Run。**
39. **准入失败只产生受保留策略控制的最小 Admission Record，不创建 Run。**
40. **失败重试是同一 Run 下的新 Execution Attempt，不能覆盖旧 Attempt。**
41. **Run 采用 Core 管理的最小通用状态机，Runtime 私有业务状态不进入 Canonical Model。**
42. **取消必须区分 cancelling、cancelled 和 cancellation_unknown。**
43. **Durable Task 由连续性需求决定；外部组件只能提交 Task Proposal。**
44. **Run 成功不自动完成 Durable Task，最终完成状态由 Shadow 校验并提交。**
45. **Stage 1 责任矩阵是后续用例和领域模型的责任归属基线。**

46. **Execution Binding 与 Capability Envelope 是独立、版本化的 Canonical Record。**
47. **Message 是独立且不可变的 Canonical Record；Conversation 保存有序引用。**
48. **Observation 接收与 World State Projection 提交是可恢复的两阶段流程，不要求跨 Adapter 分布式事务。**
49. **Memory 是 Aggregate Root；MemoryVersion 不可变并由 current version pointer 指向。**
50. **ActionProposal 与 Action 分离；通过校验和授权后才创建 Action。**
51. **Domain Event 使用最小公共信封，但不要求 Event Sourcing。**
52. **完整目标架构由 Interaction、Access、Core、Execution、Adapter、Canonical State、Infrastructure 与 External 边界组成。**
53. **逻辑模块不强制微服务，默认从模块化单体开始。**
54. **所有触发统一进入 Admission，不为 Event、Schedule、World State 或 Pulse 建立特权旁路。**
55. **Adapter 使用统一 Manifest、Capability Negotiation、Version、Health、Data Boundary 和 Contract Test。**
56. **Adapter Contract 不固定进程内、stdio、本机服务、容器或远程 Transport。**
57. **Canonical State、Derived State 与 External Source Asset 必须分离。**
58. **Phase 0–5 表示实现顺序，每个 Phase 都是完整目标架构的真子集。**
59. **第一套参考 Core 使用 Python，Server 使用 FastAPI，Web 使用 React + TypeScript + Vite。**
60. **OpenAPI 3.1 与 checked-in JSON Schema 是跨语言 Contract 事实源。**
61. **普通 Command / Query 使用 REST / JSON，Chat / Run 流使用 SSE，未来双向音频保留 WebSocket。**
62. **可信进程内 Adapter 使用 Python Port；第一种隔离 Transport 使用 JSON-RPC-style Envelope over stdio。**
63. **默认本地 Store Profile 使用 SQLite WAL、SQLAlchemy 与 Alembic；PostgreSQL 是第二官方 Profile。**
64. **首批参考执行实现为 Deterministic Test Adapter、OpenAI Model Adapter 与 Process Runtime Adapter。**
65. **具体 Framework 与 SDK 不得进入 Domain、Canonical Schema 或 Stable ID。**

## 何时必须新增 ADR

以下变化必须新增或更新 ADR：

- 把某项能力移入或移出 Shadow Core；
- 改变 Canonical Asset、Owner、Space 或 World State 的事实所有权；
- 改变所有请求经过 Shadow 的原则；
- 改变 Execution Target 或 Binding 的权威边界；
- 改变 Runtime、Memory、Model、Runner、Router 或 Store 的替换边界；
- 允许 Semantic Pulse 或其他模型参与系统正确性路径；
- 允许外部分类器自行降低数据保护等级；
- 改变 Model Binding 的数据披露边界；
- 改变 Secret、标准导出或完整备份的边界；
- 改变逻辑删除、物理清除或 Erasure 完成语义；
- 在 Primary Store 不可用时扩大允许的现实副作用；
- 引入不可重建的外部私有状态；
- 改变 Adapter Contract 的兼容性策略；
- 改变用户资产导出和迁移承诺；
- 引入新的权威状态提交者。

## 核心原则

> **Shadow owns the user relationship, assets, continuity, current state and authority.**

> **User or Space ownership is explicit from the first canonical record.**

> **Privacy, erasure and degraded operation are authority boundaries, not optional intelligence.**

> **Replaceable components own intelligence, storage implementation and execution.**

# OpenShadow 分阶段实现计划

- 状态：Stage 4 实现演进基线
- 依赖：[完整技术架构](technical-architecture.md)
- 原则：阶段决定交付顺序，不改变目标架构

## 1. 为什么分阶段

OpenShadow 的目标架构需要覆盖长期记忆、任务连续性、World State、多种执行方式、外部动作、多端入口和组件升级，但不应一次实现所有能力。

分阶段的目的不是建立一个独立的“简化版 Shadow”，而是逐步填充同一套架构：

- 第一阶段建立稳定骨架和可运行纵向闭环；
- 后续阶段增加新的模块实现和 Adapter；
- 已落地的 Canonical ID、Owner / Space、Run、Binding、Adapter Manifest 和 Schema Version 不被推翻；
- 尚未实现的能力保留 Contract 或字段，不伪造空壳服务。

## 2. 成熟度标记

每项架构能力使用以下状态：

| 状态 | 含义 |
|---|---|
| Foundation | 从第一条 Canonical Record 起就必须正确 |
| Implemented | 当前阶段有可用实现 |
| Contract-only | 稳定边界已定义，但尚无生产实现 |
| Deferred | 方向明确，内部协议暂不冻结，等待对应 Phase 的真实用例 |
| Replaceable | 具体实现必须通过 Adapter 接入 |

Contract-only 不意味着创建空数据库表、空 Service 或空微服务，只意味着当前实现不能堵死该边界。

## 3. 从第一版就不能省略的基础字段

所有 Canonical Record 从第一次迁移起应具有或可追踪：

- stable_id；
- schema_version；
- owner_ref；
- space_id；
- created_by；
- created_at / updated_at；
- data_classification；
- retention_policy_ref；
- lifecycle state；
- correlation_id / causation reference；
- provenance 或 source reference；
- optimistic version 或等价并发控制信息。

允许字段初期只有默认值，例如单用户阶段使用固定 User、默认 Personal Space 和隐式 Home Space；不允许用“当前用户”这种无法迁移的隐式假设代替正式身份。

## 4. 阶段总览

~~~mermaid
flowchart LR
    P0["Phase 0<br/>Engineering Foundation"]
    P1["Phase 1<br/>Personal Shadow Loop"]
    P2["Phase 2<br/>Memory & Capability Assets"]
    P3["Phase 3<br/>Continuity & World State"]
    P4["Phase 4<br/>Governed Actions & Proactivity"]
    P5["Phase 5<br/>Multi-endpoint & Multi-user Evolution"]

    P0 --> P1 --> P2 --> P3 --> P4 --> P5
    P2 -->|"capability foundation"| P4
    P3 -->|"state triggers"| P4
~~~

阶段编号是实现阶段，不替代需求和设计阶段编号。

## 5. Phase 0：工程基础

目标：建立可以长期演进的代码和数据骨架。

### 实现

- 模块化单体目录与依赖规则；
- Domain Core 与 Port Contract 独立于具体 Framework；
- Schema Migration 机制；
- Stable ID、Owner、Personal Space 和隐式 Home Space；
- Canonical Record 基础信封；
- Adapter Manifest、Binding 和最小 Capability Negotiation；
- 配置与 Secret Reference 分离；
- 结构化错误、日志关联 ID 和健康检查；
- Fake Store、Fake Execution Adapter 和 Contract Test Harness；
- 本地开发、测试、升级和回滚命令。

### 暂不实现

- 智能 Router；
- Memory 整理算法；
- World State Resolver；
- 现实动作；
- Semantic Pulse；
- 多用户认证；
- 外部消息队列。

### 退出条件

- Domain 模块不依赖 Web、ORM、模型 SDK 或数据库驱动；
- Fake Adapter 可以通过版本协商和 Contract Test；
- 空数据和已有数据都可重复执行迁移；
- 固定单用户仍通过正式 owner_ref 和 space_id 表达。

## 6. Phase 1：个人 Shadow 基本闭环

目标：用户可以通过 Web 使用同一个可持久化 Shadow。

~~~text
Web
  -> Admission
  -> Conversation / immutable Message
  -> Request / Root Run
  -> static Execution Binding
  -> Execution Attempt
  -> one real Execution Adapter
  -> Result / assistant Message
  -> Primary Durable Store
~~~

### 实现

- Web Client 和稳定 Shadow API；
- Conversation、Message、Admission、Request、Run、Attempt；
- static Binding；
- Capability Envelope 最小数据边界；
- Direct Model 或 Agent Runtime 的一个真实 Adapter；
- Primary Durable Store 的一个 Adapter；
- 流式响应；
- Run 失败、超时、取消和重启后状态恢复；
- 对话、Run 和结果的基础查看；
- 标准化导出骨架。

### 保留但不提前实现

- execution_mode 枚举包含完整五类 Target；
- Binding 可以指向不同 Adapter 和版本；
- Run 可以关联未来 Durable Task；
- Message 可以引用 Artifact；
- API 使用 Endpoint Context，但只启用 Web Endpoint；
- Adapter Transport 不限定进程位置。

### 退出条件

- 删除真实 Runtime 后，Conversation、Message 和 Run 仍可读取；
- Shadow 重启后可以恢复已提交状态；
- 同一 client_request_id 不产生重复 Root Run；
- Adapter SDK 对具体 Runtime 没有反向依赖；
- 更换一个测试 Target 不需要改变 Domain Schema。

## 7. Phase 2：Memory 与能力资产

目标：用户开始积累不会随智能组件替换而丢失的记忆和能力。

### 实现

- Memory、MemoryVersion、MemoryCandidate；
- Memory Authority；
- 一个可替换 Memory Intelligence Adapter；
- 周期性和按需 Memory Maintenance Job；
- Recall 的 Scope 与数据边界；
- Integration、Extension、Skill、Executable Asset 和 MCP Connection 的统一 Registry；
- Asset Catalog 与外部资产按需读取；
- Adapter 安装、禁用、健康、版本和 Secret Reference；
- 派生 Index 的删除与重建；
- Memory 查看、纠正、逻辑删除和恢复。

### 保留但不提前实现

- 多 Memory Engine 组合；
- 高级 Graph、Embedding 和 Reranking 策略；
- 自动 Adapter 市场；
- 复杂 Erasure 跨系统工作流。

### 退出条件

- 删除 Memory Intelligence 后 Canonical Memory 仍存在；
- 新 Memory Engine 可以读取 Canonical Memory 或重建派生状态；
- 外部笔记不被默认复制进 Shadow；
- Integration 的配置元数据可以导出，Secret 内容不会进入标准导出；
- Memory Correction 产生新的不可变版本，不覆盖历史。

## 8. Phase 3：任务连续性与 World State

目标：Shadow 可以跨时间继续工作，并诚实表达当前现实状态。

### 实现

- Durable Task、Task Proposal 和 Task Completion Proposal；
- Runtime Checkpoint Reference 与 Semantic Checkpoint；
- waiting、pause、resume、deadline、trigger 和 handoff；
- Schedule / Clock Port；
- Observation、WorldStateProjection、TTL、fresh / stale / unknown；
- State Source Adapter；
- 确定性 Projection 规则；
- 可选 State Resolver Adapter；
- Integration 删除后的 source unavailable；
- World State Condition 重新进入 Admission；
- OperationJob 用于迁移、整理和长操作。

### 保留但不提前实现

- 完整数字孪生；
- 实时同步所有来源；
- 复杂预测和异常检测；
- 多 Runtime 自动 Handoff 优化；
- 分布式 Scheduler 集群。

### 退出条件

- Runtime 崩溃后 Task 可以从 Canonical State 和 Checkpoint Reference 恢复；
- Runtime 不可用时可以使用 Semantic Checkpoint 切换实现；
- Shadow 重启后知道最后 World State、来源和过期原因；
- 删除 Source Integration 不会把旧状态继续伪装成 fresh；
- World State 不能直接触发未准入的现实动作。

## 9. Phase 4：受治理动作与主动能力

目标：Shadow 可以安全地改变外部世界，并提供可选主动智能。

### 实现

- Capability Declaration 和 Provider Binding；
- ActionProposal、Approval、Action 和 Action Ledger；
- Action idempotency、unknown outcome 和 reconciliation；
- Provider Adapter；
- Primary Store restricted mode；
- 可靠 Outbox Capability；
- Routing Adapter 和 Route Proposal；
- 用户可查看、保存和删除的 Routing Rule；
- 确定性 System Health Heartbeat；
- 可选 Semantic Pulse；
- Pulse Proposal 的预算、数据和副作用限制；
- 完整 Erasure Request 状态跟踪。

### 保留但不提前实现

- 自动进行高风险动作；
- 无确认的权限扩大；
- 由模型决定系统健康；
- Shadow 自研通用 Router、Workflow Engine 或消息队列。

### 退出条件

- 每个现实动作在执行前存在持久 Action ID 和授权；
- Provider 超时不会被错误标记为未执行；
- Store 不可用时普通副作用停止；
- 删除 Router 后静态 Binding 仍可工作；
- 删除 Semantic Pulse 后健康、调度、TTL 和任务恢复仍然正确。

## 10. Phase 5：多端与多用户演进

目标：在不改变 Canonical Asset 身份的前提下扩展交互范围。

### 实现候选

- Voice / Audio Endpoint；
- 多设备 Endpoint Registry；
- 本地网络或远程安全访问；
- 用户认证与会话；
- Space Membership、Role、Invitation 和 Sharing；
- Home Space 多成员访问；
- Endpoint 级权限和隐私；
- 音频路由、STT、TTS 和 Wake Word Adapter；
- 多端通知与 Presence。

### 约束

- 单用户历史资产无需迁移为无主数据；
- 已存在的 Personal Space 和 Home Space ID 保持稳定；
- 设备状态属于 Home Space，而不是绑定到第一个用户；
- 语音识别结果仍通过 Admission；
- Speaker Recognition 只能提供身份 Proposal，不能自行取得用户权限。

### 退出条件

将在开始该阶段前根据真实使用场景重新确认，不在当前阶段冻结完整家庭权限模型。

## 11. 架构能力矩阵

| 能力 | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 |
|---|---|---|---|---|---|---|
| Owner / Space identity | Foundation | Implemented | Implemented | Implemented | Implemented | Extended |
| Conversation / Message | Contract | Implemented | Implemented | Implemented | Implemented | Extended |
| Run / Attempt | Contract | Implemented | Implemented | Implemented | Implemented | Implemented |
| Durable Task | Contract-only | Reference only | Reference only | Implemented | Implemented | Implemented |
| Execution Binding | Foundation | Static | Multiple profiles | Dynamic-capable | Router proposals | Extended |
| Agent / Model Target | Contract | One real adapter | Replaceable | Handoff-capable | Routed | Extended |
| Program / Workflow Target | Contract-only | Contract-only | Executable registry | Optional | Optional | Optional |
| Canonical Memory | Contract | Reference only | Implemented | Implemented | Implemented | Extended scope |
| Memory Intelligence | Replaceable | Fake / none | One adapter | Replaceable | Optional composition | Extended |
| World State | Contract-only | Contract-only | Source references | Implemented | Trigger integration | Extended |
| Action Governance | Contract-only | Contract-only | Capability registry | Proposal boundary | Implemented | Extended |
| Semantic Pulse | Deferred | Deferred | Deferred | Contract-only | Optional | Optional |
| Integration Registry | Foundation | Minimal target profile | Implemented | Extended sources | Extended providers | Extended endpoints |
| Export / Migration | Foundation | Basic export | Capability assets | Store migration | Full workflow | Multi-user scope |
| Erasure | Foundation semantics | Basic record deletion | Memory deletion | Source cleanup | Cross-adapter tracking | Multi-user scope |
| Multi-user authorization | Contract-only | Default owner | Default owner | Space-safe | Space-safe | Implemented |

“Contract”表示设计中存在稳定入口；“Reference only”表示记录可以引用未来对象，但不需要创建空实现。

## 12. 每阶段共同工程规则

每次增加能力都必须：

1. 先补充或确认用例与验收条件；
2. 判断其状态属于 Canonical、Derived 还是 External；
3. 明确 Authority、Intelligence 和 Execution；
4. 定义或扩展 Port Capability；
5. 使用 Fake Adapter 编写 Contract Test；
6. 编写迁移和回滚方案；
7. 验证关闭或替换外部组件后的行为；
8. 验证 Owner、Space、数据等级和 Erasure；
9. 验证失败、超时、取消和重复请求；
10. 更新 ADR、架构矩阵和用户可见控制。

## 13. 禁止的阶段性捷径

为了快速交付，仍不得：

- 让 Web Client 直接写数据库；
- 让 Runtime 直接写 Memory 或 World State；
- 用具体 SDK Session ID 代替 Run 或 Task ID；
- 把模型返回当作已授权 Action；
- 把 Embedding Store 当作 Canonical Memory；
- 把外部资产全文默认复制到 Shadow；
- 在单用户阶段省略 owner_ref 和 space_id；
- 把 Secret 写进普通配置或导出；
- 用进程内函数签名代替版本化 Adapter Contract；
- 因当前没有 Router 而把模型选择硬编码进 Domain；
- 因当前没有多服务而让 Domain 依赖 Framework；
- 因未来可能需要而提前实现微服务、队列或复杂多主一致性。

## 14. 已接受的参考实现

Stage 4 已经接受 [参考实现 Profile](implementation-profile.md)：Python Core、FastAPI、React + TypeScript + Vite、REST / OpenAPI、SSE、checked-in JSON Schema、进程内 Python Port、进程外 JSON-RPC-style stdio Transport、SQLite WAL、SQLAlchemy、Alembic、PostgreSQL Store Profile，以及 Deterministic Test、OpenAI Model、Process Runtime 三类 Reference Adapter。

这些是实现选择，不改变本文件或完整技术架构定义的长期边界。具体依赖按 Release 锁定并通过 Contract Test 与 Migration 验证；任何具体项目未来都可以由兼容 Adapter 替换。

开始 Phase 0–1 编码前剩余工作只有字段级 Port Schema、可执行 Contract Example、项目脚手架和本地开发命令。

# OpenShadow 开发路线

**状态：前期设计对齐 / MVP 实现前**

当前原则：**先冻结边界，再实现最小机制；逻辑架构完整，物理实现保持简单。**

V0.1 不按“十几个模块”推进，而围绕五个逻辑域逐步形成闭环：

```text
1. Task & Continuity
2. Memory & Personal Assets
3. Control & Governance
4. World State & Scheduler
5. Integration & Runtime Bridge
```

这些域在 V0.1 中都属于同一个模块化单体。

---

## Stage 0：文档与边界对齐

冻结以下原则：

- Shadow owns durable work; Runtime owns execution decomposition；
- Shadow supervises execution; it does not plan execution；
- Memory truth / Skill assets 属于 Shadow，智能实现可替换；
- Intelligence may be outsourced; authority may not；
- 五个逻辑域只是责任边界，不是微服务边界；
- PostgreSQL 是 V0.1 主要权威状态源。

退出条件：README、Requirements、Architecture、Roadmap 不存在核心概念冲突。

---

## Stage 1：最小 Contract

先定义语义，不先设计复杂框架。

第一批 Contract：

```text
Task
Semantic Checkpoint
Runtime Binding / SRI
Event / World State
Memory Access
Skill Asset / Projection
Policy / Approval
Capability Request
Artifact Ref
Execution Record
```

暂不冻结 Runtime 内部 Planner、Subtask Graph、Skill Resolver、Learned Memory Router 或复杂 Model Router。

---

## Stage 2：Task & Continuity 主干

实现：

- Durable Task Store；
- 最小 Task Supervisor；
- Semantic Checkpoint；
- Runtime Checkpoint Ref；
- Artifact metadata；
- Runtime Binding；
- Handoff / Recovery 基础流程。

Supervisor 先只做 deterministic-first：

```text
wait / resume
retry
runtime health
checkpoint request
completion commit
```

退出条件：没有 Runtime 时 Task 仍然存在；Shadow Core 重启不丢 Task / Checkpoint。

---

## Stage 3：第一个 Runtime

首个通用 Runtime 建议使用 Hermes。

实现：

- SRI v0.1；
- Hermes Adapter；
- Runtime status / health；
- Context / Hydration；
- 同 Runtime native resume。

退出条件：Runtime Session 删除后 Shadow Task 仍然独立存在，Runtime 内部 Subtask / Planner 不需要同步进入 Shadow。

---

## Stage 4：Memory & Personal Assets

先建立所有权，再接智能实现。

实现：

```text
Raw Evidence
Canonical Memory
Task Working Memory
Canonical Skill
Skill Version / Provenance / Trust
Runtime Skill Projection
```

接入：

- Mem0：第一版在线 Recall；
- LangMem：后台 Memory Candidate / Consolidation；
- Hermes Skill Projection。

退出条件：删除 Mem0 或 Runtime Projection 不会丢失 Canonical Memory / Skill。

Graphiti、MemOS、Learned Memory Router 留到后续实验。

---

## Stage 5：Control & Governance

实现最小治理闭环：

```text
Policy
Approval
Capability Request
Provider Binding
Idempotency
Execution Ledger
```

先接：

1. 一个只读用户资源能力；
2. 一个具有真实副作用的能力。

退出条件：Runtime 的执行意图和 Shadow 的授权 / durable record 分离；Crash / Retry 不盲目重复已完成副作用。

Capability 与 Runtime-native Tool 的精确边界继续通过真实场景收敛，不提前把所有 Tool 纳入 Shadow。

---

## Stage 6：World State & Scheduler

实现：

- Event persistence；
- 最小 World State projection；
- Scheduler；
- Condition；
- background worker；
- waiting Task resume。

V0.1 不引入 Kafka / RabbitMQ。默认使用普通 service 调用 + PostgreSQL durable state/events + 单 worker。

退出条件：没有 Chat Prompt 时，Event / Schedule 仍可以创建、恢复或检查 Task。

---

## Stage 7：第二 Runtime 与跨 Runtime Handoff

接入第二个 Runtime，例如 DSH。

核心 Demo：

```text
Runtime A executes
      ↓
Semantic Checkpoint
      ↓
Runtime A unavailable
      ↓
Shadow hydrates Runtime B
      ↓
Runtime B continues durable work
```

退出条件：Task、Artifact、Working Memory、Skill availability 和关键副作用状态不丢失。

---

## Stage 8：稳定化与真实使用

只有在前面闭环真实运行后，再补：

- logging / tracing；
- retry / recovery；
- secret isolation；
- schema/version migration；
- runtime compatibility checks；
- provider reconciliation；
- backup / restore。

这些属于横切工程能力，不增加一级架构域。

---

## 后续实验

只有真实使用证明有收益时再增加：

- Graphiti Derived Memory Graph；
- MemOS alternative Memory Engine；
- Learned Memory Attention；
- Semantic Verifier；
- multi-model routing；
- advanced Skill Manager；
- richer Runtime evaluation / upgrade manager。

原则：

> **新技术主要替换 Adapter、Engine 或派生表示，不迁移 Canonical Assets。**

---

## V0.1 物理部署目标

```text
1 Shadow process
1 PostgreSQL
1 artifact directory
1 background worker
1 primary Runtime
several adapters
```

明确不做：

- 微服务化；
- Kubernetes；
- Kafka / RabbitMQ；
- 自研 Agent Loop；
- 同步 Runtime Subtask Graph；
- 完整 Workflow Engine；
- 自研 Skill Resolver；
- 自研 Vector / Graph DB；
- 复杂 Intelligence Gateway；
- 多模型路由平台；
- 多数据库事实源。

---

## V0.1 验收

| 场景 | 目标 |
| --- | --- |
| Durable Task | Runtime 消失后 Task 仍存在 |
| Runtime Freedom | Runtime 自由拆 Subtask / Planner，不要求同步进入 Shadow |
| Runtime Continuity | Runtime A → Semantic Checkpoint → Runtime B 可继续 |
| Memory Ownership | 更换 Memory Engine 不迁移 Canonical Memory |
| Skill Ownership | 删除 Runtime Projection 不丢 Canonical Skill |
| Governance | Runtime 执行意图与 Shadow 授权 / Ledger 分离 |
| Autonomous Operation | 无 Chat Prompt 时 Event / Scheduler 可推进 Task |
| Non-Memory Core | 禁用 Memory 后 Task / Control / Event / Runtime 主干仍成立 |

当前下一步：继续冻结少量 Contract，而不是增加新的一级模块。
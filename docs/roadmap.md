# OpenShadow 开发路线

**状态：前期设计对齐 / MVP 实现前**

当前优先级不是继续增加模块，而是先冻结核心对象、所有权边界和可替换接口。详细设计在这些概念稳定后再展开。

## 阶段 0：前期文档对齐

目标：确保 README、需求基线、概要设计和路线图使用同一套概念。

需要确认：

- Shadow 的稳定核心层边界；
- Task / Memory / Skill / Capability / Policy 的定义；
- Skill Authority 与 Runtime Skill Execution 的边界；
- Memory Authority 与 Memory Intelligence 的边界；
- Capability / Provider / Tool / MCP 的关系；
- Runtime 与 Shadow 的所有权边界；
- Event / World State / Scheduler 的位置。

退出条件：

- 前期文档不存在互相冲突的对象定义；
- 不再使用 Runtime / Memory Engine 私有概念作为核心对象事实源；
- 明确哪些能力属于稳定核心，哪些属于可替换 Manager / Adapter / Runtime；
- 详细模块文档暂不提前展开。

---

## 阶段 1：冻结核心契约

先定义语义，再设计数据库。

第一批 Contract：

```text
Event / World State
Task / Semantic Checkpoint
Memory Authority / Access
Skill Authority
Capability
Policy / Approval
SRI
Artifact
```

Memory Contract 先冻结：

```text
Raw Evidence / Canonical Memory ownership
scope / privacy / provenance / validity
Recall Intent / Memory Access boundary
Task Working Memory semantics
candidate vs canonical distinction
engine adapter boundary
```

Skill Contract 只冻结长期所有权需要的信息：

```text
skill_id
version
raw source ref
provenance
trust / security metadata
enabled / scope
runtime compatibility
projection / sync state
```

暂不冻结 Runtime 内部的 Skill Resolver / Skill Graph Executor / Progressive Disclosure，也不冻结复杂 Learned Memory Router。

退出条件：

- 每个 Contract 有清晰版本边界；
- durable 字段与 derived / replaceable 字段分离；
- Contract 不依赖 Hermes / DSH / Claude / Mem0 / Graphiti 私有类型；
- Memory Authority、Skill Authority 与外部执行智能不再混淆。

---

## 阶段 2：持久化与 Task 主干

目标：建立最小可恢复核心。

实现：

- Python + FastAPI 模块化单体；
- PostgreSQL migration；
- Event Store；
- 最小 World State projection；
- Task Store；
- Semantic Checkpoint；
- Artifact metadata；
- Execution Ledger；
- Structured Logging。

退出条件：

- Shadow Core 重启不丢 Event / Task / Checkpoint / Ledger；
- 没有任何 Runtime 时，Task 仍可以创建、暂停、检查点化和恢复。

---

## 阶段 3：第一个 Runtime 与 Context Compiler

先接入一个通用 Runtime，例如 Hermes。

实现：

- SRI v0.1；
- Runtime Registry；
- Hermes Adapter；
- Task Runtime Binding；
- 最小 Context Compiler；
- Runtime health / status。

退出条件：

- Runtime Session 删除后 Shadow Task 仍存在；
- Runtime 不能成为 Task / Memory / Skill 的唯一事实源。

---

## 阶段 4：Skill Authority 最小闭环

目标：证明用户长期 Skill 可以独立于 Runtime 保存和迁移，但不重做 Runtime Skill Engine。

实现：

- Canonical Skill Store；
- Raw Skill Source；
- Version / Provenance / Trust；
- Enable / Disable / Scope；
- Runtime compatibility；
- Hermes Skill Adapter；
- Runtime Projection / Sync；
- Runtime Skill Change → Candidate 导入路径。

核心 Demo：

```text
Canonical Skill
      ↓
Hermes Adapter
      ↓
Disposable Projection
      ↓
Hermes 自己完成 discovery / activation / disclosure / execution
```

退出条件：

- Runtime Projection 可以删除并重新生成；
- Runtime 不能直接修改 Canonical Skill；
- Runtime-created Skill 只能先进入 Candidate；
- Shadow 只控制 Skill availability，Runtime 控制 activation。

本阶段不做 Skill Resolver、Skill Graph Executor、Progressive Disclosure Engine、自动 Skill Evolution。

---

## 阶段 5：Memory Authority 与在线 Recall

目标：验证 Memory 默认不注入、Runtime 可以按需 Recall，并且底层检索 Engine 可替换。

### Shadow 实现

- Raw Evidence；
- Canonical Memory；
- Scope / Privacy / Provenance / Temporal Validity；
- Memory Access API；
- Task Working Memory；
- Candidate → Create / Merge / Supersede / Ignore 基础规则；
- candidate result governance；
- Deep Recall 基础路径。

### 外部组件

首个在线检索后端使用 **Mem0 OSS**，通过 `MemoryEngineAdapter` 接入，负责候选检索 / reranking，不成为事实源。

基础执行链：

```text
Runtime
  ↓ Recall Intent
Shadow Memory Access API
  ↓
Mem0 Adapter
  ↓
Candidate Memories
  ↓
Shadow Governance
  ↓
Task Working Memory / Runtime
```

退出条件：

- 简单 Task 可以完全不触发 Recall；
- 需要历史信息时 Runtime 能主动调用 Memory Access；
- Canonical Memory 有 provenance / validity；
- Task Working Memory 可跨 Runtime 保留；
- 删除或替换 Mem0 不迁移 Canonical Memory。

---

## 阶段 6：后台 Memory Consolidation

目标：把交互关键路径和记忆整理分开。

实现：

- Shadow Scheduler / Background Memory Job；
- **LangMem Adapter**；
- conversation / task / event → Memory Candidate；
- consolidation / update suggestion；
- duplicate / conflict candidate；
- Candidate Review / Policy。

链路：

```text
Event / Task / Conversation
        ↓
Background Job
        ↓
LangMem
        ↓
Memory Candidate / Consolidation Suggestion
        ↓
Shadow
        ↓
Create / Merge / Supersede / Ignore
```

退出条件：

- LangMem 不能直接成为 Canonical Memory 事实源；
- Background Worker 失败不影响在线 Task 主链；
- 重跑后台整理不会破坏 provenance / version history。

---

## 阶段 7：Capability 与治理

先接一个只读 Capability，再接一个有副作用的 Capability。

实现：

- Capability Registry；
- Provider Binding；
- Capability Gateway；
- Policy / Risk；
- Approval；
- action_id / idempotency_key；
- Execution Ledger；
- result sanitization；
- secret / credential boundary。

协议边界：

```text
Capability
    ↓
Provider Binding
    ↓
MCP / REST / CLI / IPC / Local API
```

退出条件：

- Runtime 不能绕过 Gateway；
- 重试成功动作不会重复执行；
- Runtime 原生 MCP / Tool Calling 不会破坏统一治理。

---

## 阶段 8：第二 Runtime 与语义接力

接入第二个 Runtime，例如 DSH。

实现：

- DSH Adapter；
- Canonical Task hydration；
- Runtime switch / rebind；
- last durable checkpoint recovery；
- side-effect reconciliation；
- 第二个 Runtime Skill Adapter / Projection。

核心 Demo：

```text
Runtime A 执行 Task
        ↓
Semantic Checkpoint
        ↓
Runtime A 中断
        ↓
Shadow 重新提供 Task / Working Memory / Available Skills / Policy
        ↓
Runtime B 继续执行
```

退出条件：

- Task 语义、Artifact、Task Working Memory、Skill 可用性和副作用状态不丢失；
- 同一 Canonical Skill 可投影给两个不同 Runtime。

---

## 阶段 9：Event-driven 持续运行

目标：证明 Shadow 不是 Chat 聚合器，也不是 Memory Engine 外壳。

实现：

- Scheduler；
- Event → World State → Task；
- waiting Task resume；
- notification；
- deterministic rules；
- 可选 tiny Pulse。

退出条件：

- 没有用户 Chat Prompt 时，Event / Scheduler 仍可触发 Task；
- 即使暂时禁用 Memory，Task / Runtime / Capability / Skill / Event 主干仍能运行。

---

## 阶段 10：Memory Association Graph 实验

目标：验证自动联想和多跳关系是否真正提高长期个人 AI 的 Recall 质量。

增加 **Graphiti Adapter**，把 Entity / Relation / Temporal Graph 作为 Derived Intelligence：

```text
Canonical Memory / Event
        ↓
Graphiti Adapter
        ↓
Derived Memory Graph
        ↓
Graph-assisted / multi-hop Recall
```

实验比较：

```text
Mem0-only
   VS
Mem0 + Graph Association
```

关注：

- multi-hop question / recall quality；
- irrelevant memory rate；
- task success；
- token overhead；
- stale / wrong relation rate；
- user correction；
- association gain。

退出条件：

- Graph 删除后可从 Canonical Memory / Raw Evidence 重建；
- 低置信度 relation 不覆盖 Canonical Memory；
- 能证明关联图带来可测收益，否则不提升为默认主链。

---

## 阶段 11：可插拔 Manager 与升级验证

只有真实使用出现明确缺口后，才增加高级 Manager。

候选扩展：

- Learned Memory Attention / Personal Memory Router；
- Advanced Skill Manager；
- MemOS Adapter / alternative Memory Engine；
- Runtime evaluation manager。

同时实现：

- historical replay；
- dry-run / sandbox；
- canary；
- promote / rollback；
- Adapter / Manager compatibility checks。

退出条件：

- 更换 Memory Router 不迁移 Canonical Memory；
- 更换 Skill Manager 不迁移 Canonical Skill；
- 更换 Runtime / Memory Engine / Provider 不迁移核心资产。

---

## v0.1 验收矩阵

| ID | 场景 | 目标 |
| --- | --- | --- |
| AC-01 | Runtime Continuity | Runtime A 中断后 Runtime B 继续同一 Task |
| AC-02 | Skill Portability | 同一 Canonical Skill 可投影到两个 Runtime |
| AC-03 | Skill Ownership | Runtime 修改 Projection 不直接修改 Canonical Skill |
| AC-04 | Cross-Runtime Memory | Runtime B 可使用 Runtime A 形成的长期 Memory |
| AC-05 | Memory Selectivity | 简单 Task 无 Recall；需要历史时只注入少量相关 Memory |
| AC-06 | Memory Engine Replaceability | 替换在线检索 Engine 不迁移 Canonical Memory |
| AC-07 | Autonomous Event Handling | 无 Chat Prompt 时 Event 可触发 Task |
| AC-08 | Capability Governance | Runtime 不能绕过 Policy / Gateway 执行高风险动作 |
| AC-09 | Exactly-once Side Effect | Crash / Retry 不重复执行已完成动作 |
| AC-10 | Non-Memory Core | 禁用 Memory 后 Task / Skill / Capability / Event 主干仍工作 |

## v0.1 明确不做

- 自研完整 Agent Loop；
- 自研 Skill Resolver；
- Skill Graph Executor；
- Progressive Disclosure Engine；
- 自动 Skill Evolution；
- Learned Memory Router；
- 把 Graphiti / Knowledge Graph 放进默认主链；
- 自研 Browser Agent；
- 自研 Coding Agent；
- 完整 Workflow Engine；
- 完整 RAG Framework；
- 自研 Vector DB / Graph DB；
- 完整 Chat / Voice 平台；
- Home Assistant 替代品；
- Plugin Marketplace；
- Multi-user SaaS；
- Kubernetes / 复杂微服务。

## 当前执行顺序

```text
文档对齐
  ↓
核心 Contract
  ↓
PostgreSQL 逻辑模型
  ↓
Event / Task / Checkpoint / Ledger
  ↓
第一个 Runtime
  ↓
Skill Authority / Projection
  ↓
Memory Authority + Mem0
  ↓
LangMem Background Consolidation
  ↓
Capability / Provider / Protocol
  ↓
第二 Runtime / Handoff
  ↓
Event-driven Runtime
  ↓
Graphiti Association Experiment
  ↓
按真实缺口增加可插拔 Manager
```

在 Contract 冻结之前，不继续扩展详细模块设计。
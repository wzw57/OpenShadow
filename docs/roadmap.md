# OpenShadow 开发路线

**状态：前期设计对齐 / MVP 实现前**

当前优先级不是继续增加模块，而是先把核心对象、所有权边界和对象关系冻结。详细设计在这些概念稳定后再展开。

## 阶段 0：前期文档对齐

目标：确保 README、需求基线、概要设计和路线图使用同一套概念。

需要确认：

- Shadow 的稳定核心层边界；
- Task / Memory / Skill / Capability / Policy 的定义；
- Skill 与 Capability 的关系；
- Capability / Provider / Tool / MCP 的关系；
- Runtime 与 Shadow 的所有权边界；
- Event / World State / Scheduler / Pulse 的位置。

退出条件：

- 前期文档不存在互相冲突的对象定义；
- 不再使用 Runtime 私有概念作为核心对象事实源；
- 详细模块文档暂不提前展开。

---

## 阶段 1：冻结核心契约

先定义语义，再设计数据库。

第一批 Contract：

```text
Event / World State
Task / Semantic Checkpoint
Memory
Skill
Capability
Policy / Approval
SRI
Artifact
```

其中 Skill Contract 至少需要明确：

- canonical skill identity；
- level；
- version；
- activation / when-to-use；
- dependencies；
- required capabilities；
- memory needs；
- verification criteria；
- provenance；
- runtime compatibility；
- lifecycle / maturity。

退出条件：

- 每个 Contract 有清晰版本边界；
- 所有 durable 字段与 replaceable / derived 字段分离；
- Contract 不依赖 Hermes / DSH / Claude 私有类型；
- Skill 与 Capability 不再混淆。

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
- 没有任何 Runtime 时，Task 仍然可以创建、暂停、检查点化和恢复。

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

- Runtime Session 删除后 Shadow Task 仍然存在；
- Runtime 不能成为 Task / Memory / Skill 的唯一事实源。

---

## 阶段 4：Memory 最小闭环

目标：验证 Memory 是决策基础，而不是长期 RAG。

实现：

- Raw Evidence；
- Canonical Memory；
- Memory Candidate；
- 简单 Memory Policy；
- MemoryNeed；
- Memory Broker；
- MemoryBundle；
- Task Working Memory；
- Deep Recall 基础路径。

退出条件：

- Memory 注入由 Task / Step 需要驱动；
- Canonical Memory 有 provenance；
- 派生索引可以删除并重建。

---

## 阶段 5：Skill 最小闭环

目标：证明用户长期方法可以独立于 Runtime 保存和迁移。

实现：

- Skill Registry；
- canonical Skill representation；
- Strategy / Domain / Procedure 基础层级；
- SkillNeed；
- Skill Resolver；
- SkillBundle；
- required_capabilities / memory_needs；
- Skill version / provenance；
- 一个 Runtime Projection；
- 一个 Skill Import / Export 基础路径。

核心 Demo：

```text
Canonical Skill
      ↓
Runtime A Projection
      ↓
执行
      ↓
切换 Runtime
      ↓
Runtime B Projection
      ↓
保持核心方法语义继续执行
```

退出条件：

- 一个 Skill 可以跨两个 Runtime 投影；
- Skill 不依赖某个 Runtime 私有 Prompt 作为唯一事实源；
- Skill 需要的 Capability 由声明依赖获得，而不是 Skill 自己拥有权限。

---

## 阶段 6：Capability 与治理

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
- secret proxy / credential boundary。

同时预留 MCP 边界：

- MCP Tool → Capability Candidate / Provider Binding；
- MCP Resource → Context / Evidence Source；
- MCP Prompt → Skill Candidate / Runtime Template；
- Runtime 通过 Shadow 暴露的 Gateway 使用能力，而不是绕过治理直连 Provider。

退出条件：

- Runtime 不能绕过 Gateway；
- 重试已成功动作不会重复执行；
- Skill 声明 Capability 依赖不会自动获得权限。

---

## 阶段 7：第二 Runtime 与语义接力

接入第二个 Runtime，例如 DSH。

实现：

- DSH Adapter；
- Canonical Task hydration；
- Runtime switch / rebind；
- last durable checkpoint recovery；
- side-effect reconciliation。

核心 Demo：

```text
Runtime A 执行 Task
        ↓
Semantic Checkpoint
        ↓
Runtime A 中断
        ↓
Shadow 重新编译 Task + Memory + Skill
        ↓
Runtime B 继续执行
```

退出条件：

- Task 目标、事实、产物、Skill 语义和副作用状态不丢失。

---

## 阶段 8：Event-driven 持续运行

目标：证明 Shadow 不是 Chat 聚合器。

实现：

- Scheduler；
- Event → World State → Task；
- waiting Task resume；
- notification；
- deterministic rules；
- 可选 tiny Pulse。

Pulse 只作为低成本注意力优化，不作为核心架构依赖。

退出条件：

- 没有用户 Chat Prompt 时，Event 也可以更新状态并触发 Task。

---

## 阶段 9：升级、回放与真实部署

把“可替换”变成真实能力。

实现：

- Runtime candidate；
- Skill candidate；
- historical replay；
- dry-run / sandbox；
- canary；
- promote / rollback；
- drain；
- local-first continuous deployment。

需要积累的数据：

- Runtime handoff outcome；
- Skill projection / portability outcome；
- Memory recall outcome；
- Capability retry / idempotency event；
- user correction；
- task success / failure；
- Skill version success history。

---

## v0.1 验收矩阵

| ID | 场景 | 目标 |
| --- | --- | --- |
| AC-01 | Runtime Continuity | Runtime A 中断后 Runtime B 继续同一 Task |
| AC-02 | Skill Portability | 同一 Canonical Skill 可投影到两个 Runtime |
| AC-03 | Cross-Runtime Memory | Runtime B 可使用 Runtime A 形成的长期 Memory |
| AC-04 | Autonomous Event Handling | 无 Chat Prompt 时 Event 可触发 Task |
| AC-05 | Capability Governance | Runtime 不能绕过 Policy / Gateway 执行高风险动作 |
| AC-06 | Exactly-once Side Effect | Crash / Retry 不重复执行已完成动作 |
| AC-07 | Runtime Upgrade | Replay + Canary + Promote / Rollback 不迁移核心资产 |

## v0.1 明确不做

- 自研完整 Agent Loop；
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
Memory
  ↓
Skill
  ↓
Capability / MCP Boundary
  ↓
第二 Runtime / Handoff
  ↓
Event-driven Runtime
  ↓
Replay / Canary / Real Deployment
```

在 Contract 冻结之前，不继续扩展详细模块设计。
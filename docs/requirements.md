# OpenShadow 需求基线

**状态：前期需求对齐 / 待核心契约冻结**  
**目标：OpenShadow v0.1 MVP**

> **Shadow 持有连续性。Runtime 负责推理与执行，但不拥有用户的长期状态。**

## 1. 产品定义

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它负责持有必须跨模型、跨 Runtime、跨设备、跨 Session 和跨时间持续存在的个人资产，并让不同 Runtime、Memory Engine、Skill 实现和 Capability Provider 可以被替换、升级和迁移。

OpenShadow 不以“成为最聪明的 Agent”为目标，也不重造已有成熟 Runtime、浏览器 Agent、Coding Agent、Memory Engine 或设备平台。

## 2. 核心问题

OpenShadow 需要解决：

- 用户状态被某个 Agent / Session / 产品锁定；
- 长期 Task 随 Runtime Session 消失；
- Memory 被简化成不可治理的长期 RAG；
- 用户长期积累的 Skill 被锁在某个 Runtime 私有格式；
- Tool、Capability、Provider、MCP 等概念混杂，导致能力难以迁移和统一治理；
- 不同 Runtime 分别持有权限和外部副作用状态；
- 更换 Runtime、Memory Engine、Skill 版本或 Provider 时缺少稳定迁移边界；
- 系统过度依赖 Chat UI，缺少 Event / World State 驱动的持续运行机制。

## 3. 产品边界

判断一个功能是否属于 Shadow 的原则：

> **必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致的状态和契约，由 Shadow 持有；其余能力优先复用外部成熟系统。**

### Shadow 必须持有或治理

- Identity / Policy；
- Event / World State；
- Task / Semantic Checkpoint；
- Raw Evidence / Canonical Memory；
- Skill Registry / Skill Version / Skill Relation；
- Capability Contract / Registry；
- Runtime Registry / SRI；
- Context Compiler；
- Capability Gateway / Execution Ledger；
- Artifact 引用；
- authoritative Scheduler；
- 核心对象的升级、迁移与 provenance 元数据。

### 优先复用

- Agent Loop / Planning；
- Hermes、DSH、Claude、Codex 等 Runtime；
- Mem0、LangMem、Graphiti 等 Memory Engine；
- Browser Agent / Coding Agent / Research Agent；
- Home Assistant / PC Agent / Server Agent；
- Email / Calendar / Browser Provider；
- MCP / REST / CLI / IPC 等集成协议；
- STT / TTS / Messaging；
- Embedding / Vector DB / Graph DB / LLM Serving。

## 4. 核心一等对象

| 对象 | 定义 |
| --- | --- |
| **Identity** | 用户身份、长期偏好、信任与隐私基线 |
| **Event** | 已发生事实的持久记录 |
| **World State** | 当前世界状态的紧凑投影 |
| **Task** | 需要持续完成的工作及其状态 |
| **Memory** | 对历史证据形成的可追溯、可修正认知 |
| **Skill** | 可复用的方法、经验、策略和程序性知识 |
| **Capability** | 稳定、可治理、可版本化的动作或查询契约 |
| **Policy** | 权限、风险、隐私、预算与审批规则 |
| **Artifact** | 文件、报告、日志、工具结果等任务产物 |
| **Runtime Binding** | 当前执行 Runtime 与临时 Session 引用 |

对象关系的基本语义：

```text
Memory      = 我知道什么
Skill       = 这类事情应该怎么做
Capability  = 系统实际上能做什么
Task        = 我现在要完成什么
Policy      = 哪些行为被允许
```

## 5. Task 与 Semantic Checkpoint 需求

- Task 必须由 Shadow 持有，不能以 Runtime Session 作为唯一事实源。
- Task 必须保留目标、阶段、已完成工作、已知事实、决策、Artifact、剩余工作、权限与副作用状态。
- Runtime 中断或替换后，Task 必须能够从最近持久化 Semantic Checkpoint 恢复。
- Shadow 不要求迁移隐藏思维链、KV Cache 或 Runtime 私有 Planner 状态。
- 跨 Runtime 接力的最低保证是：Task 语义、证据、产物、剩余工作和副作用状态不丢失。

## 6. Memory 需求

### 6.1 三层数据模型

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

- Raw Evidence 作为长期证据源；
- Canonical Memory 必须可修正、可追溯、支持时间有效性；
- embedding、向量索引、摘要和图等派生结果必须可重建；
- Memory Engine 不能成为 Canonical Memory 的唯一事实源。

### 6.2 召回

- Recall 必须以当前 Task / Step 的决策需要为中心；
- 支持显式 `MemoryNeed`；
- 支持结构化、时间、实体、全文和语义检索组合；
- 输出紧凑 `MemoryBundle`；
- Canonical Memory 不足时允许 Deep Recall Raw Evidence、历史 Task 与 Artifact。

## 7. Skill 需求

Skill 是 Shadow 的一等长期资产。

### 7.1 基本原则

- Shadow 必须持有跨 Runtime 的规范化 Skill 表示；
- Runtime-native Skill 可以存在，但不能成为需要长期迁移 Skill 的唯一事实源；
- Skill 必须支持版本、来源、依赖、验证状态和 Runtime compatibility；
- Skill 描述“怎么做”，但不授予 Capability 权限；
- Skill 可以依赖其他 Skill 和 Capability。

### 7.2 分层 Skill

当前需求基线支持以下概念层级：

1. **策略级 Skill**：高层方法论与长期工作方式；
2. **领域级 Skill**：某领域解决一类问题的方法；
3. **程序级 Skill**：较具体的执行步骤、依赖与验证标准；
4. **Runtime 投影**：面向某一 Runtime 的具体 Skill 表达。

前三层由 Shadow 规范化管理。第四层允许按 Runtime 重新生成或适配。

### 7.3 Skill 选择与注入

- Task 可以产生 `SkillNeed`；
- Skill Resolver 根据 Task intent、当前阶段、Skill 层级、Runtime compatibility、Policy、所需 Capability 和历史验证结果选择 Skill；
- 输出 `SkillBundle`；
- Context Compiler 将 SkillBundle 与 MemoryBundle、Task、World State 等共同编译给 Runtime；
- 不允许把全部 Skill 默认注入所有 Runtime Context。

### 7.4 Skill 迁移

Skill 迁移目标是语义可移植，而不是 Runtime 私有格式逐字一致。

至少应保留：

- purpose；
- activation / when-to-use；
- method / procedure；
- dependencies；
- required capabilities；
- memory needs；
- verification criteria；
- provenance；
- maturity / validation status。

## 8. Capability、Provider 与 MCP 需求

### 8.1 Capability

Capability 表示稳定、可治理的动作或查询契约，例如：

```text
calendar.create
email.send
server.logs.read
server.restart
home.light.set
file.read
```

Capability 必须独立于具体 Provider 和 Transport。

### 8.2 Provider

Provider 是 Capability 的实际实现者。Provider 可以被替换，但 Capability 语义应尽量稳定。

### 8.3 Tool 与 MCP

以下概念必须明确区分：

> **Tool 是接口；Capability 是长期能力资产；Skill 是可复用经验；MCP 是协议。**

- MCP Tool 可以映射为 Capability Candidate 或 Provider Binding；
- MCP Resource 可以作为 Context Source / Evidence Source；
- MCP Prompt 可以作为 Skill Candidate 或 Runtime Template；
- 使用 MCP 不得绕过 Capability Gateway / Policy / Execution Ledger。

## 9. Runtime 与 SRI 需求

- Runtime 被视为可替换执行器；
- Shadow 通过 SRI 统一执行、恢复、暂停、取消、检查点、状态、能力发现和健康检查；
- 至少支持两个不同 Runtime Adapter 以验证 Runtime-neutral；
- Runtime Router 可考虑 Task 类型、Runtime 能力、隐私、成本、延迟、健康状态和 Policy；
- Runtime-native Session 只作为 Binding，不作为 Task 事实源；
- Runtime 切换通过 Context Compiler 从 Shadow 规范化状态重新 hydrate。

## 10. Event、World State 与持续运行需求

- Event 采用 append-oriented 方式持久记录；
- World State 由 Event 投影生成；
- Runtime 默认读取 Task 相关的紧凑 World State，而不是全量事件历史；
- Task 可以由 User、Event、Schedule 或 Condition 触发；
- 删除 Chat UI 后系统仍应能接收事件、维护状态、恢复任务并执行允许的动作；
- Pulse 可以作为低成本注意力层，但属于实现优化，不属于核心所有权原则。

## 11. Capability Gateway 与治理需求

所有现实副作用统一经过：

```text
Identity
→ Schema Validation
→ Policy / Risk
→ Approval when required
→ Idempotency
→ Provider
→ Execution Ledger / Audit
```

必须保证：

- Runtime 不直接持有长期 raw secrets；
- 高风险 Capability 支持审批；
- 每个副作用动作具有稳定 action_id / idempotency_key；
- Runtime crash / retry 不重复执行已完成动作；
- 结果可以被 Artifact 化并按 Runtime trust profile 脱敏。

## 12. Context Compiler 需求

Context Compiler 至少需要组合：

```text
Task / Checkpoint
MemoryBundle
SkillBundle
World State
Policy / Trust Profile
Allowed Capabilities
Artifact / Evidence references
```

并转换为具体 Runtime 能理解的输入格式。

## 13. 可替换组件升级需求

Runtime、Skill、Memory Engine 和 Provider 的长期升级机制应支持：

```text
Candidate
→ Compatibility Check
→ Historical Replay / Test
→ Canary
→ Promote
→ Rollback / Deprecate
```

核心资产不得因为更换外围组件而整体迁移。

## 14. 非功能需求

| 维度 | 要求 |
| --- | --- |
| 本地优先 | Raw Evidence、核心 Memory、Policy 默认本地持有 |
| 可移植性 | 核心数据不依赖单一 Runtime / Provider 私有格式 |
| 可审计性 | 重要状态和现实动作可追溯 |
| 可恢复性 | Core 重启不丢 Task / Event / Ledger；Runtime crash 可恢复 |
| 可升级性 | Runtime / Skill / Provider 等具有清晰替换边界 |
| 最小权限 | Cloud Runtime 和外部 Provider 只获得所需数据与权限 |
| 可重建性 | 派生索引和 Runtime 投影可重新生成 |

## 15. v0.1 范围

### 必做

- Event / World State；
- Task / Semantic Checkpoint；
- Raw Evidence / Canonical Memory / MemoryNeed / MemoryBundle；
- Skill Registry / SkillNeed / SkillBundle / 基础 Runtime Projection；
- Capability Registry / Gateway / Provider Binding；
- Policy / Approval / Idempotency / Execution Ledger；
- SRI + 至少两个 Runtime Adapter；
- Context Compiler；
- 基础 Scheduler / Event-driven execution；
- PostgreSQL 单机持久化；
- CLI / 最小管理入口。

### 暂不做

- 自研 Agent Loop；
- 自研 Browser Agent / Coding Agent；
- 完整 Workflow Engine；
- 自研 Vector DB / Graph DB；
- Plugin Marketplace；
- 完整 IM / Voice 平台；
- Multi-user SaaS；
- Kubernetes / 复杂微服务。

## 16. v0.1 验收场景

| 场景 | 通过条件 |
| --- | --- |
| Runtime Continuity | Runtime A 中断后 Runtime B 能继续同一 Task |
| Skill Portability | 同一规范化 Skill 能投影到两个 Runtime 并保持核心方法语义 |
| Cross-Runtime Memory | Runtime A 形成的长期 Memory 可被 Runtime B 正确使用 |
| Autonomous Event Handling | 无 Chat Prompt 时 Event 也能更新状态、创建 Task 并触发执行 |
| Capability Governance | Runtime 无法绕过 Policy 执行高风险外部动作 |
| Exactly-once Side Effect | Crash / Retry 不重复执行已完成现实动作 |
| Runtime Upgrade | Candidate Runtime 可回放、灰度、晋升与回滚且核心资产不迁移 |

## 17. 当前文档原则

当前阶段不继续展开过细模块设计。下一步先冻结：

```text
Event / World State
Task
Memory
Skill
Capability
Policy
SRI
Artifact
```

这些核心契约严格对齐后，再进入数据库 Schema、API、详细设计和实现。
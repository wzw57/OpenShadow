# OpenShadow 需求基线

**状态：前期需求对齐 / 待核心契约冻结**  
**目标：OpenShadow v0.1 MVP**

> **Shadow 持有连续性。Runtime 负责推理与执行，但不拥有用户的长期状态。**

## 1. 产品定义

OpenShadow 是一个**本地优先、运行时无关的个人 AI 连续性与控制层**。

它负责持有必须跨模型、跨 Runtime、跨设备、跨 Session 和跨时间持续存在的规范化个人资产，并让 Runtime、Memory Engine、Skill 执行机制、Capability Provider 和工具协议可以被替换、升级和迁移。

OpenShadow 不以“成为最聪明的 Agent”为目标，也不重造已有成熟 Runtime、Browser Agent、Coding Agent、Skill Execution Engine、Memory Engine 或设备平台。

## 2. 核心原则

### 2.1 资产所有权原则

> **Shadow 可以依赖外部生态提供实现，但不能依赖外部生态持有规范化个人资产。**

### 2.2 核心边界原则

> **必须跨模型、跨 Runtime、跨设备、跨 Session 或跨年份保持一致的状态和契约，由 Shadow 持有；其余功能优先复用外部成熟系统。**

### 2.3 外部格式原则

外部格式只允许作为：

- Import；
- Export；
- Adapter；
- Projection；
- Derived View。

外部格式不能直接成为 Shadow 核心事实源。

## 3. Shadow 不是 Memory Engine

Memory 只是 Shadow 的一个子系统。

即使 Memory 子系统暂时不可用，Shadow 仍必须能够：

- 创建、保存、暂停、恢复 Task；
- 保存 Semantic Checkpoint；
- 在不同 Runtime 间接力 Task；
- 持有 Canonical Skill 并同步 Runtime Projection；
- 管理 Capability / Policy / Approval / Execution Ledger；
- 接收 Event、维护 World State、执行 Scheduler；
- 保存 Artifact、历史和副作用状态。

如果移除 Memory 后这些能力无法存在，则说明系统边界发生错误退化。

## 4. 核心一等对象

| 对象 | 定义 |
| --- | --- |
| **Identity** | 用户身份、长期偏好、信任与隐私基线 |
| **Event** | 已发生事实的持久记录 |
| **World State** | 当前世界状态的紧凑投影 |
| **Task** | 需要持续完成的工作及其状态 |
| **Memory** | 对历史证据形成的可追溯、可修正认知 |
| **Skill** | 可复用的方法、经验和程序性知识 |
| **Capability** | 稳定、可治理、可版本化的动作或查询契约 |
| **Policy** | 权限、风险、隐私、预算与审批规则 |
| **Artifact** | 文件、报告、日志、工具结果等任务产物 |
| **Runtime Binding** | 当前执行 Runtime 与临时 Session 引用 |

基本语义：

```text
Task        = 我现在要完成什么
Memory      = 我知道什么
Skill       = 这类事情应该怎么做
Capability  = 系统实际上能做什么
Policy      = 哪些行为被允许
```

## 5. Task 与 Semantic Checkpoint 需求

- Task 必须由 Shadow 持有，Runtime Session 不得作为唯一事实源；
- Task 必须保留目标、阶段、已完成工作、已知事实、决策、Artifact、剩余工作、权限与副作用状态；
- Runtime 中断或替换后，Task 必须能从最近持久化 Semantic Checkpoint 恢复；
- Shadow 不要求迁移隐藏思维链、KV Cache 或 Runtime 私有 Planner 状态；
- 跨 Runtime 接力最低保证：Task 语义、证据、产物、剩余工作和副作用状态不丢失。

## 6. Memory 需求

### 6.1 Memory 的基本边界

> **Memory 默认可访问，但默认不注入 Runtime Context。**

长期拥有大量 Memory 不意味着每个 Task 都需要 Recall。简单、确定、与个人历史无关的任务允许 `Memory Recall = 0`。只有当当前 Task、阶段或决策可能依赖历史信息时，才应触发 Recall。

Memory 的核心问题分为三个不同层次：

```text
什么时候应该回忆？
        ↓
应该回忆哪一类信息？
        ↓
应该回忆到多深？
```

这三个问题与底层向量搜索、图数据库或具体 Memory Engine 解耦。

### 6.2 三层事实模型

```text
Raw Evidence
    ↓
Canonical Memory
    ↓
Derived Index / Summary / Graph
```

- **Raw Evidence** 是长期证据源；
- **Canonical Memory** 是当前可修正、可追溯、带时间有效性的规范化认知；
- **Derived Layer** 包括 embedding、向量索引、全文索引、图关系、摘要、聚类等，可以删除和重建；
- Memory Engine、Vector DB、Graph DB 不得成为 Canonical Memory 的唯一事实源。

### 6.3 自动 Recall / Memory Attention

系统不能依赖用户反复明确提醒“回想一下以前的某件事”。

Runtime 或可插拔的 Memory Attention 组件应能够在执行过程中识别：

- 当前问题可能依赖用户长期偏好；
- 当前实体、项目或人物曾在历史中出现；
- 当前决策可能存在既往决策、失败经验或约束；
- 当前事实可能与已有 Memory 冲突；
- 当前任务需要历史原因、关系、时间线或证据。

当出现此类情况时，可以产生语义化的 `Recall Intent / Memory Need`，而不是要求 Runtime 构造底层数据库查询。

概念链路：

```text
Task / Current Step / Decision
            ↓
      Memory Attention
            ↓
       Recall Intent
            ↓
      Memory Access API
            ↓
      Memory Engine(s)
```

V0.1 不冻结复杂 Learned Memory Router；Memory Attention 必须允许后续通过独立组件升级或替换。

### 6.4 Recall Intent 应表达“需要什么”，而不是“怎么搜”

Runtime 应优先表达语义需求，例如：

- 某项目以前的关键架构决策；
- 某人的相关历史与关系；
- 用户对此类问题已有的稳定偏好；
- 相似任务中过去的成功或失败经验；
- 某个事实的来源与历史变化。

底层到底使用结构化查询、全文搜索、embedding、entity matching、knowledge graph 或其他算法，由 Memory Engine / Adapter 决定。

### 6.5 Scoped Retrieval

Memory 必须支持逻辑作用域，以避免海量长期记忆全部进入同一搜索空间。

至少应能够表达或派生：

```text
Global
Project
Task
Entity
Relationship
Episode
```

默认优先在与当前 Task 最相关的 Scope 内 Recall，需要时再逐步扩大搜索范围。

### 6.6 Multi-index Retrieval

Memory 不得仅依赖语义相似度。

长期 Recall 应允许组合以下索引维度：

- Semantic；
- Entity；
- Temporal；
- Project / Scope；
- Memory Type；
- Relationship；
- Current / Superseded validity；
- Provenance；
- Lexical / Full-text。

Vector similarity 只是候选信号之一。

### 6.7 分层记忆与逐级召回

除事实层级外，还需要支持不同认知粒度的派生表示，例如：

```text
Raw Evidence
     ↓
Concrete Memory / Episode / Decision
     ↓
Topic / Project Summary
     ↓
Higher-level Profile / Current Project View
```

上层 Summary 用于低成本获取概况，但不能替代底层事实源。

Recall 应支持逐级加深，而不是默认一次搜索全部历史：

```text
NONE
 ↓
LIGHT        当前 Project / Entity / Summary
 ↓
NORMAL       Canonical Memory
 ↓
DEEP         Historical Task / Episode / Relation
 ↓
EVIDENCE     Raw Evidence / Artifact
```

绝大多数 Task 应停留在 `NONE / LIGHT / NORMAL`。

### 6.8 时间有效性与历史认知

长期 Memory 必须区分：

- 当前仍有效的事实 / 偏好 / 决策；
- 历史上曾经有效但现在已失效的认知；
- 被新 Memory supersede 的旧认知；
- 对同一事实存在冲突或不确定性的记录。

Runtime 默认优先获取当前有效认知，但在解释“为什么会变成这样”或进行历史分析时，应能够回溯旧版本和原始证据。

### 6.9 Task Working Memory

长期 Memory 与 Runtime Context 之间应存在 Task 级 Working Set。

已被证明对当前 Task 有用的 Memory 可以暂时进入 Task Working Memory，供后续 Step 重复使用，避免每一步重新查询长期 Memory。

```text
Long-term Memory
      ↓ recall
Task Working Memory
      ↓
Runtime Context
```

Task Working Memory 是任务级派生状态，不替代 Canonical Memory。

### 6.10 Asset Promotion

并非所有长期重要信息都应该永远以普通 Memory 形式存在。

当某项信息具有更强的系统语义时，应允许晋升或转化为其他长期资产：

- 稳定方法 / 程序性经验 → Skill Candidate；
- 强制约束 / 权限 / 隐私规则 → Policy；
- 当前事实 → World State；
- 持续目标 / 待完成工作 → Task；
- 可执行动作 → Capability / Provider Binding。

这可以避免把 Memory 变成所有长期状态的垃圾桶。

### 6.11 后台联想、图关联与 Consolidation

系统应允许在非交互关键路径中，对新增或近期 Memory / Event 进行低优先级后台处理，以构建和维护可重建的关系层。

目标包括：

- Entity extraction / entity linking；
- 相同人物、项目、系统、概念之间的自动关联；
- Memory ↔ Memory、Memory ↔ Event、Memory ↔ Task、Memory ↔ Artifact 的关系发现；
- 时间线与前后因果 / supersede 候选关系；
- Topic / Cluster / Community 发现；
- 重复 Memory 合并候选；
- 冲突 Memory 检测；
- Project / Entity Summary 重建；
- 对新证据触发旧 Memory 的重新评估。

概念上：

```text
New Events / Memories
        ↓
Background Association / Consolidation
        ↓
Entity / Relation / Cluster / Summary Candidates
        ↓
Derived Memory Graph / Indexes
        ↓
Future Recall
```

后台联想的结果默认属于 **Derived Intelligence**，而不是新的事实源。任何关系应尽量保留 provenance、confidence 和时间信息；低置信度自动关联不得静默覆盖 Canonical Memory。

该机制可以由 Graphiti、MemOS、LangMem 或未来 Memory Engine 提供，也可以由 Shadow Scheduler 触发独立 Memory Worker；Shadow 只要求通过稳定 Memory API / Adapter 接入，不绑定具体实现。

V0.1 不要求实现完整的全量 Knowledge Graph 或持续全库重算，但需要为增量后台 Consolidation / Association 保留边界。

### 6.12 Memory Governance

外部 Memory Engine 返回候选结果后，Shadow 仍需控制：

- Privacy / Scope；
- Runtime Trust Profile；
- Current validity / superseded state；
- Provenance；
- 去重；
- Token / Context budget；
- Local-only / cloud restrictions。

外部 Memory Engine 提供检索与整理智能，Shadow 持有 Memory truth 与访问边界。

### 6.13 Memory Engine 可替换性

Memory Intelligence 必须通过稳定 API / Adapter 接入。

可替换组件包括：

- Extraction / Consolidation Engine；
- Vector / Lexical Retrieval；
- Graph Engine；
- Entity Linker；
- Reranker；
- Memory Attention / Recall Router；
- Background Association Worker。

替换这些组件时，不得要求迁移 Raw Evidence、Canonical Memory、Task 或其他规范化个人资产；派生索引和图可以重建。

### 6.14 Memory 设计目标

Memory 的长期目标不是最大化 Recall 数量，而是：

> **在尽量少占用 Runtime 注意力的前提下，自动提供足以改善当前决策的最少相关 Memory。**

因此未来评估应关注：

- irrelevant memory rate；
- injected memory count；
- token overhead；
- memory actually referenced；
- stale / superseded memory rate；
- user correction rate；
- task outcome；
- deep recall recovery rate；
- memory utility density。

V0.1 不要求冻结复杂 Memory Router 或图算法，但必须保留上述概念边界。

## 7. Skill 需求

### 7.1 Skill 所有权边界

Skill 是 Shadow 的一等长期资产，但**Skill 的具体执行编排不属于 Shadow 稳定核心**。

核心规则：

> **Shadow controls availability; Runtime controls activation.**

Shadow 决定某个用户 / Runtime / Task 可以使用哪些 Skill；Runtime 决定本次执行中何时发现、加载、激活和组合这些 Skill。

### 7.2 Shadow 必须持有的 Skill 信息

至少包括：

- Canonical Skill identity；
- Raw Skill Source；
- Version；
- Provenance；
- Trust / Security metadata；
- Enable / Disable / Scope；
- Runtime compatibility；
- Runtime Projection / Sync records；
- Import / Export / Migration / Rollback 元数据。

### 7.3 Runtime 负责的 Skill 能力

优先交给 Runtime：

- Skill discovery；
- Skill activation；
- progressive disclosure；
- Skill composition / orchestration；
- Runtime-native bundle / prompt / reference 加载；
- Runtime 内部 Tool 使用策略。

Shadow V0.1 不自研这些机制。

### 7.4 Runtime Projection

Runtime-specific Skill 表示必须视为可删除、可重建派生资产：

```text
Raw Skill Source
      ↓
Canonical Skill
      ↓ Runtime Skill Adapter
Runtime Projection
      ↓
Runtime
```

Runtime 不得直接修改 Canonical Skill Store。

如果 Runtime 新建或修改 Skill，应进入：

```text
Runtime Change
→ Skill Candidate / Change Event
→ Shadow Import / Review / Normalize
→ Canonical Skill update
```

### 7.5 可插拔 Skill Manager

Skill Manager 可以作为未来独立扩展组件，用于：

- 高级 Skill 检索；
- Skill 关系 / Graph；
- 冲突处理；
- 路由；
- 自动评估与演化。

但必须满足：

- 不持有 Canonical Skill 唯一事实源；
- 可以整体替换；
- 升级失败不破坏 Canonical Skill；
- 不绕过 Runtime / Capability / Policy 边界。

因此 V0.1 **不要求** SkillNeed、Skill Resolver、SkillBundle、Skill Graph Executor 或自研 Progressive Disclosure Engine。

## 8. Capability、Provider 与协议需求

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

Provider 是 Capability 的实际实现者。Provider 可以替换，但 Capability 语义应尽量稳定。

### 8.3 Tool 与 MCP

必须明确区分：

> **Tool 是接口；Capability 是长期能力资产；Skill 是可复用经验；MCP 是协议。**

- MCP Tool 可以映射为 Capability Candidate 或 Provider Binding；
- MCP Resource 可以成为 Context / Evidence Source；
- MCP Prompt 可以成为 Skill Candidate 或 Runtime Template；
- 使用 MCP 不得绕过 Capability Gateway / Policy / Execution Ledger。

## 9. Runtime 与 SRI 需求

- Runtime 是可替换执行器；
- Shadow 通过 SRI 统一执行、恢复、暂停、取消、检查点、状态、能力发现和健康检查；
- 至少支持两个不同 Runtime Adapter 以验证 Runtime-neutral；
- Runtime-native Session 只作为 Binding，不作为 Task 事实源；
- Runtime 切换通过 Shadow 规范化状态重新 hydrate；
- Runtime Adapter 必须可独立替换升级。

## 10. Event、World State 与持续运行需求

- Event 采用 append-oriented 方式持久记录；
- World State 由 Event 投影生成；
- Task 可以由 User、Event、Schedule 或 Condition 触发；
- 删除 Chat UI 后系统仍应能接收 Event、维护状态、恢复 Task 并执行允许的动作；
- Pulse / 小模型分层属于实现优化，不属于核心所有权原则。

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
- 高风险 Capability 支持 Approval；
- 每个副作用动作有稳定 action_id / idempotency_key；
- Runtime crash / retry 不重复执行已完成动作；
- Runtime 原生 MCP / Tool Calling 不能绕过 Gateway。

## 12. Context Compiler 需求

Context Compiler 负责把 Shadow 规范化资产转换为当前 Runtime 可以消费的上下文。

可能包括：

```text
Task / Checkpoint
Relevant Memory
Available Skill refs / projections
World State
Policy / Trust Profile
Allowed Capabilities
Artifact / Evidence refs
```

Context Compiler 不负责替代 Runtime 的 Skill 激活或 Agent Loop。

## 13. 可替换组件升级需求

下列组件必须通过稳定边界接入：

- Runtime；
- Memory Engine；
- Memory Attention / Association Engine；
- Skill Manager；
- Runtime Skill Adapter；
- Provider；
- MCP / Protocol Adapter；
- Search / Index Engine。

升级目标：

> **新技术主要替换 Adapter、Manager 或派生表示，不迁移规范化个人资产。**

## 14. 非功能需求

| 维度 | 要求 |
| --- | --- |
| 本地优先 | Raw Evidence、Canonical Memory、Policy、Canonical Skill 默认本地持有 |
| 可移植性 | 核心数据不依赖单一 Runtime / Provider / Skill / Memory Engine 格式 |
| 可审计性 | 重要状态、Memory provenance、Skill 来源和现实动作可追溯 |
| 可恢复性 | Core 重启不丢 Task / Event / Ledger；Runtime crash 可恢复 |
| 可升级性 | Runtime / Memory Engine / Skill Adapter / Manager / Provider 具有清晰替换边界 |
| 最小权限 | Runtime 与外部 Provider 只获得所需数据与权限 |
| 可重建性 | 派生索引、Memory Graph、Summary、Runtime Projection 可以重新生成 |

## 15. v0.1 范围

### 必做

- Event / World State；
- Task / Semantic Checkpoint / Artifact；
- Raw Evidence / Canonical Memory 基础闭环；
- Memory Access API / Adapter 边界；
- 基础 Scope / Validity / Provenance / Governance；
- Skill Store / Version / Provenance / Trust / Runtime Projection / Sync；
- Capability Registry / Gateway / Provider Binding；
- Policy / Approval / Idempotency / Execution Ledger；
- SRI + 至少两个 Runtime Adapter；
- Context Compiler；
- Scheduler / Event-driven execution；
- PostgreSQL 单机持久化；
- CLI / 最小管理入口。

### 预留但不要求完整实现

- 自动 Memory Attention / Learned Recall Router；
- 全量 Memory Graph；
- 大规模后台联想 / Community Detection；
- 高级 Memory Consolidation；
- 多 Memory Engine 联邦检索。

### 暂不做

- 自研 Agent Loop；
- 自研 Skill Resolver；
- Skill Graph Executor；
- Progressive Disclosure Engine；
- 完整 Workflow Engine；
- 自研 Browser Agent / Coding Agent；
- 自研 Vector DB / Graph DB；
- Plugin Marketplace；
- 完整 IM / Voice 平台；
- Multi-user SaaS；
- Kubernetes / 复杂微服务。

## 16. v0.1 验收场景

| 场景 | 通过条件 |
| --- | --- |
| Runtime Continuity | Runtime A 中断后 Runtime B 能继续同一 Task |
| Skill Portability | 同一 Canonical Skill 可投影到两个 Runtime |
| Skill Ownership | Runtime 修改 Projection 不直接修改 Canonical Skill |
| Cross-Runtime Memory | Runtime A 形成的长期 Memory 可被 Runtime B 使用 |
| Memory Isolation | 不相关长期 Memory 不默认注入当前 Task Context |
| Memory Recoverability | 派生索引或图删除后可从 Canonical Memory / Raw Evidence 重建 |
| Autonomous Event Handling | 无 Chat Prompt 时 Event 仍可更新状态、创建 Task 并触发执行 |
| Capability Governance | Runtime 无法绕过 Policy / Gateway 执行高风险动作 |
| Exactly-once Side Effect | Crash / Retry 不重复执行已完成现实动作 |

## 17. 当前文档原则

当前阶段不继续展开过细模块设计。下一步先冻结：

```text
Event / World State
Task / Semantic Checkpoint
Memory Authority / Access Boundary
Skill Authority / Projection Boundary
Capability / Provider / Protocol
Policy / Approval
SRI
Artifact
```

这些边界严格对齐后，再进入数据库 Schema、API、详细设计和实现。
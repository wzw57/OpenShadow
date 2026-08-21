# OpenShadow 关键用例

- 状态：Stage 2 设计
- 输入：[需求基线](../requirements.md)、[概要设计](../architecture.md)、[责任矩阵](../responsibility-matrix.md)
- 目标：用用户可观察流程验证责任边界、持久状态和失败语义
- 非目标：不定义数据库表、传输协议、类、函数或具体外部组件

## 1. 用例格式

每个用例包含：

| 字段 | 含义 |
|---|---|
| Actor | 发起者与参与者 |
| Trigger | 触发条件 |
| Preconditions | 执行前提 |
| Main Flow | 正常可观察流程 |
| Alternative / Failure | 分支、拒绝、失败和未知结果 |
| Durable State Changes | Canonical State 变化 |
| External Side Effects | Shadow 之外的影响 |
| Policy / Privacy | 权限、数据、预算和保留约束 |
| Acceptance Criteria | 可测试的完成条件 |

## 2. 用例目录

### A. 交互与准入

- [UC-001 普通请求闭环](01-interaction-and-admission.md#uc-001-普通请求闭环)
- [UC-002 请求拒绝、重复提交与降级](01-interaction-and-admission.md#uc-002-请求拒绝重复提交与降级)
- [UC-UI-001 Web 多端连接与继续](01-interaction-and-admission.md#uc-ui-001-web-多端连接与继续)

### B. 执行与连续性

- [UC-003 直接 Model Worker 执行](02-execution-and-continuity.md#uc-003-直接-model-worker-执行)
- [UC-004 Executable Asset 与 Runner](02-execution-and-continuity.md#uc-004-executable-asset-与-runner)
- [UC-004A 外部 Workflow Target 执行](02-execution-and-continuity.md#uc-004a-外部-workflow-target-执行)
- [UC-005 Run 晋升为 Durable Task](02-execution-and-continuity.md#uc-005-run-晋升为-durable-task)
- [UC-006 Runtime 故障恢复与 Handoff](02-execution-and-continuity.md#uc-006-runtime-故障恢复与-handoff)

### C. Memory 与 World State

- [UC-007 Memory Candidate 提交与周期整理](03-memory-and-world-state.md#uc-007-memory-candidate-提交与周期整理)
- [UC-008 Memory 纠正、来源失效与删除](03-memory-and-world-state.md#uc-008-memory-纠正来源失效与删除)
- [UC-009 Observation 更新 World State](03-memory-and-world-state.md#uc-009-observation-更新-world-state)
- [UC-010 World State 冲突、过期与来源删除](03-memory-and-world-state.md#uc-010-world-state-冲突过期与来源删除)

### D. 外部动作、故障与可移植性

- [UC-011 受治理的外部 Action](04-actions-resilience-portability.md#uc-011-受治理的外部-action)
- [UC-012 Action Unknown Outcome 与 Reconciliation](04-actions-resilience-portability.md#uc-012-action-unknown-outcome-与-reconciliation)
- [UC-013 Primary Store 故障与受限模式](04-actions-resilience-portability.md#uc-013-primary-store-故障与受限模式)
- [UC-014 标准导出、完整备份与恢复](04-actions-resilience-portability.md#uc-014-标准导出完整备份与恢复)
- [UC-015 Erasure 跨组件传播](04-actions-resilience-portability.md#uc-015-erasure-跨组件传播)

### E. Integration、外部资产与主动智能

- [UC-016 安装、配置与撤销 Integration](05-integrations-and-proactive.md#uc-016-安装配置与撤销-integration)
- [UC-017 按需访问外部信息资产](05-integrations-and-proactive.md#uc-017-按需访问外部信息资产)
- [UC-018 Semantic Pulse 提议与拒绝](05-integrations-and-proactive.md#uc-018-semantic-pulse-提议与拒绝)

## 3. 全局约束

所有用例继续满足：

1. 所有输入经过 Shadow Admission；
2. 被接受的 Request 创建一个 Root Run；
3. 重试是同一 Run 下的新 Execution Attempt；
4. External Component 只能返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 或 Usage；
5. 只有 Shadow Authority 提交 Canonical State；
6. Execution Target 受 Binding 和 Capability Envelope 约束；
7. 未知数据默认 sensitive；
8. 用户保留最终物理删除权；
9. Primary Store 故障时不产生未记录现实副作用；
10. Runtime、Memory、Model、Runner、Resolver、Store 和 Provider 均可替换。

## 4. Stage 2 退出条件

- 入口、准入、执行、连续性、Memory、World State、外部动作、故障、删除和迁移均有正常与失败流程；
- 每个用例明确 Canonical State Changes；
- 每个现实副作用都有授权、幂等和 unknown outcome 语义；
- 用例不依赖具体数据库、模型、Runtime 或 Provider；
- 用例足以提取 Stage 3 领域对象、关系和状态机；
- Stage 4 增补 Workflow Target 用例，不改变 Stage 2 已确认的 Authority 边界；
- 未决项只保留真正影响产品行为或 Core 边界的问题。

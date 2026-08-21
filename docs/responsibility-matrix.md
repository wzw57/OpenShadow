# OpenShadow Core / External 责任矩阵

- 状态：Stage 1 基线 / Stage 4 Core Diet 修订
- 输入：[需求基线](requirements.md)、[概要设计](architecture.md)与[ADR-0003](adr/0003-tiny-core-and-typed-profiles.md)
- 目标：逐项确定 Kernel、Contract、Profile、Intelligence 和 Execution 的归属
- 非目标：不定义数据库表、API 字段、具体组件或部署拓扑

## 1. 判定规则

每项能力必须回答：

| 维度 | 问题 |
|---|---|
| Identity | 是否必须有跨组件稳定身份？ |
| Authority | 谁可以校验并提交最终状态？ |
| Profile Semantics | 哪些 typed Schema、不变量和迁移需要兼容？ |
| Intelligence | 哪些判断和算法应可替换？ |
| Execution | 谁完成模型调用、程序运行、协议交互或现实动作？ |
| Portability | 替换组件时必须保留什么？ |

四级分类：

- **KERNEL**：2030 年外部 AI 范式变化后，Shadow 仍必须直接理解和执行；
- **CONTRACT-ONLY**：需要稳定安全或连续性边界，但不把完整能力做进 Core；
- **PROFILE / EXTENSION**：属于 Shadow 的兼容能力，但通过版本化 Profile / Adapter 演进；
- **LATER PHASE / DERIVED**：没有证据表明当前需要固化，或可以重建。

统一规则：

1. External Component 只能提交 typed Proposal 或 Result，不能直接写 Canonical Repository；
2. Canonical Envelope 统一身份和治理，Profile 定义 typed payload 与领域不变量；
3. Run / Attempt 是 Kernel 控制事实；Runtime 私有 Session 不能代替；
4. Adapter 公共 Descriptor 保持最小，复杂能力按 Family 协商；
5. Derived State 可以删除重建；
6. 统一 UI 不等于统一成万能聚合；
7. Aggregate、Repository 和服务边界在实现阶段由并发与一致性需要决定，不冻结成公共协议。

## 2. Core Diet 总表

| 能力 | 分类 | Kernel / Contract | Profile / External |
|---|---|---|---|
| Stable ID、Version | KERNEL | 生成、并发、引用 | 无 |
| Owner / Space | KERNEL | 明确归属和 created_by | 多用户 ACL 后续 |
| Canonical Envelope | KERNEL | Schema ref、provenance、lifecycle、retention | typed payload 由 Profile 定义 |
| Proposal / Commit | KERNEL | Validate、Authority、ExpectedVersion、Commit | 外部组件产生 Proposal |
| Work Admission | KERNEL | 工作准入、幂等、Request | UI / Trigger 负责输入 |
| Run / Attempt | KERNEL | 生命周期、Binding、结果与取消事实 | Target 完成执行 |
| Durable Task | CONTRACT-ONLY + PROFILE | stable ID、Run / checkpoint refs、completion commit | Goal、规划、分解、Workflow |
| Execution Binding | KERNEL | target_kind、capability、envelope 校验 | Router 提出 BindingProposal |
| Conversation | PROFILE | 身份、Commit、通用删除 | Message 顺序等 Profile 规则 |
| Memory | PROFILE | Candidate Commit、版本、Owner、删除 | 提取、整理、召回、Embedding、Graph |
| State | PROFILE | Proposal Commit、通用时间有效性 | Observation Schema、freshness、Resolver、预测 |
| Skill | PROFILE | SkillAsset 治理和权限 | Agent Skills Bundle、发现、加载、执行 |
| Integration | PROFILE | Stable ID、Binding、Secret Reference | Family config、协议与执行 |
| Action | CONTRACT-ONLY + PROFILE | 先持久化、Approval、unknown / reconciliation | 参数生成、Provider 调用 |
| Policy | KERNEL minimum + EXTENSION | data class、capability、approval、budget、side effect、expiry、revocation | 复杂 Policy Engine |
| Store | FAMILY PORT | Canonical Repository Contract、restricted mode | DB、Migration、Backup、Outbox 等 Capability |
| Export / Migration / Erasure | CONTRACT-ONLY | Intent、标准格式、状态与完整性 | 具体执行由 Store / Adapter |
| Domain Event | NARROW CONTRACT | 通知 Envelope | Bus / delivery implementation |
| Semantic Pulse | EXTENSION | Proposal Admission | 小模型或规则 |
| Voice / Device | EXTENSION | Endpoint identity、permission | STT、TTS、Audio、协议 |
| Search / RAG | EXTENSION / DERIVED | 数据授权和 Evidence ref | Index、Retrieval、Reranking |

## 3. Work Admission、Run 与 Task

### Kernel Authority

- 识别工作承载输入；
- 提交 AdmissionRecord、Request、Root Run 和 ExecutionAttempt；
- 校验 Run 状态转换；
- 提交 Binding、Usage、Result / Failure summary；
- 区分 cancelling、cancelled 和 cancellation_unknown；
- 提交 Task / Completion Proposal 的接受或拒绝；
- 保持 Task、Run、Checkpoint 和 Artifact 的稳定引用。

### 不创建 Root Run 的路径

- health / readiness；
- 静态资源；
- 只读控制面 Query；
- 订阅已有 Run 事件；
- 内部 recovery / reconciliation step。

这些路径仍执行身份、权限、速率和必要审计。

### External

- Runtime、Model、Runner、Workflow 和 Provider 执行 Attempt；
- Runtime 维护私有 Planner、Subtask、Subagent、Tool Loop 和 Session；
- Task Planner / Workflow Engine 维护复杂分解；
- Target 返回事件、结果、失败和 capability-specific acknowledgement。

Run 成功不自动完成 Durable Task。Task 最终状态必须通过 CompletionProposal 和 Commit。

## 4. Execution Binding 与 Capability

Binding 使用 namespaced `target_kind`，不是封闭枚举。首批 well-known kinds：

- `shadow.agent-runtime`；
- `shadow.model-worker`；
- `shadow.deterministic-runner`；
- `shadow.workflow-target`；
- `shadow.capability-provider`。

Kernel 校验：

- required / resolved capabilities；
- Adapter 与 Contract Version；
- data classification；
- resource / budget；
- side-effect level；
- approval；
- expiry / revocation；
- health。

Router 负责分类、评分、质量 / 延迟 / 成本预测和 Route Proposal。Core 不理解这些算法，只接受或拒绝 BindingProposal。

## 5. Adapter Family

### 公共 Descriptor

~~~text
adapter_id
adapter_family
contract_versions
capabilities
config_schema_ref
implementation_ref
health
~~~

### Family-specific Capability

| Family | 基础能力 | 可选能力 |
|---|---|---|
| Runtime | describe、execute、events | cancel、progress、usage、checkpoint、native resume、handoff |
| Model | describe、execute | streaming、structured output、usage |
| Runner | describe、execute | sandbox、artifact、cancel |
| State Source | describe、observe | subscribe、refresh |
| Provider | describe、execute action | idempotency、cancel、reconcile |
| Store | canonical repository | migration、export、backup、outbox、integrity |
| Secret | resolve reference | rotate、revoke |
| Interaction | deliver / receive | voice stream、device presence |

权限、Secret、Checkpoint、Migration、Data Boundary 和 Reconciliation 不进入所有 Adapter 的统一必填 Manifest。Adapter 不得伪造不支持的 Capability。

Execution / Intelligence Family 可以使用 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 和 Usage 等输出族。Infrastructure Family 使用自己的 typed Result，只共享 Message Envelope、Correlation、Version 和结构化错误。

## 6. Memory Profile

### Kernel / Profile Authority

- Stable Memory ID 与 Owner / Space；
- MemoryCandidate Schema 验证；
- create、correct、merge、supersede、delete、erase Commit；
- ExpectedVersion；
- source_dependency；
- anti-resurrection Tombstone；
- Profile Migration。

### External Intelligence

- extraction；
- consolidation；
- deduplication；
- retrieval / reranking；
- summary；
- embedding / graph / cluster；
- Evidence 相关性和 source dependency 建议。

Memory Engine、Index 和 Graph 均不拥有 Canonical Memory。Memory Profile 可以升级，但必须提供语义 Migration。

## 7. State Profile

### Kernel / Profile Authority

- StateProposal Schema、Owner、Space、ExpectedVersion；
- 通用 observed_at / expires_at 校验；
- accepted state version；
- source unavailable；
- delete / erase；
- Profile Migration。

### State Profile Semantics

- state_key；
- typed value / value_schema_ref；
- source / Evidence；
- fresh / stale / unknown；
- Observation Retention；
- correction / supersede。

### External

- Source Connector 采集；
- Resolver 处理语义冲突；
- 预测、异常检测和刷新建议；
- 领域本体、查询和数字孪生。

World State 不是 Kernel 的固定知识图谱。Accepted State 仍是可恢复、可迁移的 Canonical Record。

## 8. Skill、Executable 与 Integration

### SkillAsset Profile

Shadow 保存：

- Stable ID、Owner / Space；
- format；
- source reference；
- pinned revision / immutable snapshot；
- digest；
- trust；
- permission policy；
- classification；
- install status；
- Runtime / Provider external refs。

标准 Bundle 保持 Agent Skills 的 `SKILL.md`、`scripts/`、`references/`、`assets/`。Shadow 不修改 Bundle，不自创内容格式，也不把 `allowed-tools` 当作最终权限。

### External

- Skill discovery / recommendation；
- 内容加载与 Prompt projection；
- 脚本执行、依赖、Sandbox；
- Provider upload；
- MCP / Extension / Device 协议；
- 风险检测建议。

Executable Asset 继续保存 source、checksum、I/O contract 和权限请求；具体语言 Runtime 外置。

Integration 具有 Stable ID 和 Secret Reference，但 Family Profile 定义配置、权限、健康和生命周期。

## 9. Policy 与现实 Action

Core 只实现确定性 Policy primitives：

- data class；
- capability；
- approval；
- budget；
- side-effect；
- expiry；
- revocation。

复杂 Policy Engine 可以返回 PolicyEvaluationProposal，不能自行签发授权。

现实 Action Contract 必须保证：

1. ActionProposal 与 Action 分离；
2. Provider 调用前持久化 pending / approval；
3. 使用 idempotency key；
4. 结果为 succeeded、failed 或 unknown；
5. unknown 需要 reconciliation；
6. Store 不可用且没有可靠 Outbox 时禁止执行。

Provider 执行协议调用，返回外部 ID、结果和 Evidence。

## 10. Store、导出与 Erasure

Store Family 能力：

| Capability | Shadow 保证 | 外部实现 |
|---|---|---|
| Canonical Repository | Version、ExpectedVersion、读写语义 | 数据库与事务 |
| Migration | Migration Intent / Result | 物理 Schema 与数据转换 |
| Portable Export / Import | 标准 Manifest 与兼容性 | 打包与传输 |
| Backup / Restore | 独立授权和状态 | 实现相关完整备份 |
| Durable Outbox | Action 与投递引用 | 可靠存储和发送 |
| Integrity | 期望清单 | checksum / scan |

Primary Repository 不可用时：

- 只读和显式 Ephemeral Interaction 可以继续；
- Canonical Commit 暂停；
- 现实副作用默认禁止；
- 预配置紧急 Action 必须先写可靠 Outbox；
- 恢复后幂等 reconciliation。

Erasure Intent 由 Shadow 提交，各 Profile / Adapter 删除具体副本。无法确认时显示 pending 或 unreachable。

## 11. Event、Outbox 与 OperationJob

- Domain Event：通知和最终一致，不是 Event Sourcing；
- Outbox：只解决可靠跨边界副作用，不是通用 Queue；
- OperationJob：只处理 export、import、migration、backup、erasure；
- Scheduler、Memory Maintenance 和 Workflow Engine 继续作为独立 Extension / Service。

## 12. Interaction、Voice 与主动智能

Core：

- work-bearing Admission；
- Owner / Space / Endpoint；
- data boundary；
- user correction / approval / rejection；
- Proposal Commit。

External：

- Web / Mobile UX；
- STT / TTS / Wake Word；
- speaker recognition；
- audio routing；
- device transport；
- Semantic Pulse；
- proactive suggestion ranking。

Semantic Pulse 可以提出 Recall、State、Run、Task 或 escalation Proposal，但不直接 Commit，也不是系统健康、TTL、Lease、Timeout 或恢复的依赖。

## 13. 必须由 Tiny Core 实现

1. Stable ID、Owner / Space、Version 与 Canonical Envelope；
2. Schema / Profile Registry 与 ExpectedVersion；
3. Proposal / Validate / Commit；
4. work-bearing Admission、Request、Run 与 Attempt；
5.最小 Durable Task continuity；
6. Execution Binding、Capability 与 deterministic Policy enforcement；
7. minimal Adapter Registry；
8. Profile Migration / Export / Erasure Intent；
9.受治理 Action 的最小安全 Contract；
10.用户查看、纠正、撤销、删除和导出 API。

## 14. 必须由 Profile / Extension / Infrastructure 负责

1. Conversation、Memory、State、Task、Action、Skill 与 Integration 的可演进业务 Schema；
2. Runtime、Planner、Subagent、Tool Loop 与 Workflow Engine；
3. Model、Router、Memory Intelligence、State Resolver、Search / RAG；
4. Script Runtime、依赖、Sandbox；
5.数据库、复制、物理备份、Secret Store、Queue 与 Scheduler；
6.复杂 Policy Engine；
7. Skill discovery、loading、execution 与 Provider projection；
8. STT、TTS、Wake Word、Audio 与设备协议；
9.领域本体、预测、数字孪生；
10.浏览器 Agent、Coding Agent 与 Provider 实现。

## 15. 退出条件

- 每项概念已有 KERNEL / CONTRACT-ONLY / PROFILE-EXTENSION / LATER-PHASE 分类；
- External Component 没有直接 Commit 路径；
- Canonical Envelope 与 typed Profile 没有混成万能 JSON；
- 新增 target_kind 不要求修改 Core 主流程；
- Adapter 只承诺 Family Capability；
- Store Contract 没有膨胀为数据库产品抽象；
- Skill 使用外部标准；
- Run、Task、Memory、State 和 Action 的关键安全不变量仍然可验证；
- 分阶段实现不需要预建空服务或表。

# OpenShadow Core / External 责任矩阵

- 状态：Stage 1 设计基线
- 输入：[需求基线](requirements.md)与[概要设计](architecture.md)
- 目标：逐项确定 Authority、Canonical State、Intelligence 和 Execution 的归属
- 非目标：不定义数据库表、API 字段、具体组件或部署拓扑

## 1. 判定规则

每项能力必须回答四个问题：

| 维度 | 含义 |
|---|---|
| Authority | 谁能校验并提交最终状态 |
| Canonical State | 哪些状态必须由 Shadow 语义持有并可迁移 |
| Intelligence | 哪些推理、分类、融合和优化交给可替换组件 |
| Execution | 谁完成模型调用、程序运行、协议交互或现实动作 |

统一规则：

1. Core 可以定义稳定语义、状态机、权限点和 Port，但不因此实现对应算法或基础设施。
2. External Component 可以返回 Result、Proposal、Observation、Progress、Failure、Checkpoint Reference 和 Usage，但不能绕过 Core 提交权威状态。
3. Canonical State 通过 Durable Store Port 持久化；数据库物理模型不定义领域语义。
4. Derived State 可以删除重建，不作为组件替换的阻塞条件。
5. 用户界面中的统一体验不要求所有能力位于同一个实现组件。

## 2. 总体责任矩阵

| 领域 | Authority | Canonical State | External Intelligence | External Execution |
|---|---|---|---|---|
| Request / Run | Core 准入并提交生命周期 | Request metadata、Root Run、Attempt summary | 任务理解、结果摘要可外置 | Runtime、Model、Runner、Provider |
| Durable Task | Core 提交创建、暂停、恢复、完成 | Task、Checkpoint refs、conditions、completion | 规划、分解、进度判断 | Agent Runtime 与其他 Target |
| Execution Dispatch | Core 校验 Binding、Envelope、预算和权限 | Requirements、Binding、Envelope、Status、Usage | Router、模型评估、降级建议 | 各 Execution Target |
| Memory | Core 提交 Candidate、修正和删除 | Canonical Memory、Evidence refs、versions | 提取、整理、召回、融合、排序 | Memory Intelligence |
| World State | Core 提交 accepted projection | Observation、Projection、conflicts、freshness | State Resolution、预测、异常检测 | Source Connector / Model / Runner |
| Owner / Space | Core 提交归属和生命周期 | User/Space refs、created_by | 不需要智能实现 | 管理界面通过 Core API |
| Data Governance | Core 执行等级、披露和保留约束 | labels、policies、decisions | 内容分类只能提出标签 | Binding 负责实际数据处理 |
| Asset / Capability | Core 提交身份、版本和 Binding | Skill、Executable、Extension、Integration metadata | Skill 选择、兼容性建议可外置 | Extension、Runner、Provider |
| External Action | Core 授权并提交 Action 状态 | Action、Approval、Ledger、Reconciliation | 参数生成、风险建议可外置 | Capability Provider |
| Durable Store | Core 定义持久语义和故障模式 | Store Binding、migration、integrity metadata | 无 | 外部数据库、备份、Outbox |
| Retention / Erasure | Core 提交意图和完成状态 | policy、tombstone、component status | 分类与保留建议可外置 | 各 Adapter 删除具体副本 |
| Scheduler / Pulse | Core 提交 Trigger 与 Proposal 结果 | schedule、trigger、bounded Run | Semantic Pulse、主动建议 | Scheduler、Model、Runner |
| Interaction / Voice | Core 准入请求并执行权限 | endpoint / session refs、user choices | STT、TTS、唤醒、对话表现 | Voice / UI Adapter |

## 3. Request、Run 与 Durable Task

### 3.1 对象关系

~~~mermaid
flowchart TB
    INPUT["Incoming Input"]
    ADMISSION["Admission"]
    REJECTED["Admission Record<br/>rejected / invalid / replay"]
    REQUEST["Accepted Request<br/>immutable admission metadata"]
    RUN["Root Run"]
    A1["Execution Attempt 1"]
    A2["Execution Attempt 2"]
    PROPOSAL["Durable Task Proposal"]
    TASK["Durable Task"]
    LATER["Later Runs"]

    INPUT --> ADMISSION
    ADMISSION -->|"rejected"| REJECTED
    ADMISSION -->|"accepted"| REQUEST
    REQUEST --> RUN
    RUN --> A1
    A1 -->|"retry"| A2
    RUN --> PROPOSAL
    PROPOSAL -->|"Core validates"| TASK
    TASK --> LATER
~~~

确定边界：

- Request 是不可变的准入记录；每个被接受的 Request 创建一个 Root Run。
- 准入失败只创建最小 Admission Record，不创建 Run。
- 重试是同一 Run 下的新 Execution Attempt，不创建重复 Root Run。
- Durable Task 可以跨时间产生多个 Run。
- Runtime 内部 Subtask 不进入 Shadow 模型；需要跨 Session 或 Runtime 存在时，必须提交 Durable Task Proposal。

### 3.2 Run 状态机

~~~mermaid
stateDiagram-v2
    [*] --> created
    created --> queued
    queued --> running
    running --> waiting
    waiting --> running
    running --> paused
    paused --> queued
    running --> completed
    running --> failed
    running --> cancelling
    waiting --> cancelling
    paused --> cancelling
    cancelling --> cancelled
    cancelling --> cancellation_unknown
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
    cancellation_unknown --> [*]
~~~

Core Authority：

- 分配 Request、Run 和 Attempt Stable ID；
- 校验生命周期转换；
- 提交 Binding、费用、Usage、结果状态和取消结果；
- 将 Task Proposal 提交为 Durable Task；
- 校验 Completion Proposal 和 Task 完成条件。

External：

- Target 返回 Attempt progress、Result、Failure 和 cancellation acknowledgement；
- Runtime 决定私有规划和 Subtask；
- 摘要模型可以提出 result summary，但不能修改状态。

内容保留：

- 最小记录保存身份、时间、状态、Binding、费用、结果摘要和必要审计引用；
- Prompt、Response 和 Tool Trace 受 Retention Policy 与 Data Classification 控制；
- Runtime 私有推理不要求保存；
- Run 成功不自动等于 Durable Task 完成。

## 4. Execution Dispatch 与 Capability Envelope

Core Authority：

- 接收 Execution Requirements；
- 校验 Target Descriptor 和健康状态；
- 接受或拒绝 Route Proposal；
- 提交 Execution Binding；
- 根据 Policy 签发 Capability Envelope；
- 执行数据、能力、资源、副作用、预算、有效期和版本边界；
- 无安全 Binding 时通过 Interaction Port 询问用户。

Canonical State：

- Execution Requirements；
- Target / Capability Descriptor；
- Execution Binding；
- Capability Envelope；
- Routing Rule；
- Attempt Status；
- Usage / Action Record；
- cancellation / unknown outcome。

External Intelligence：

- 任务分类；
- 模型、Runtime 和 Runner 能力评分；
- 质量、费用和延迟预测；
- Route Proposal；
- 降级与升级建议。

External Execution：

- Agent Runtime 执行开放式多步骤任务；
- Model Worker 执行单次受限推理；
- Deterministic Runner 执行登记程序；
- Workflow Target 通过外部 Workflow Engine 执行明确步骤、等待和补偿流程；
- Capability Provider 完成外部查询和现实动作。

边界：

- Runtime 可以在 Envelope 内管理私有执行；
- 跨 Adapter、预算或副作用边界必须产生最小记录；
- 越界按预设策略处理，没有策略时询问用户；
- 用户可以将选择保存为 Routing Rule；
- Runtime 恢复长期任务时重新验证 Envelope。

## 5. Memory

Core Authority：

- 校验 Memory Candidate；
- 提交 create、correct、merge、supersede、delete 和 erase；
- 执行 Owner、Space、数据等级、来源依赖和 Recall 权限；
- 防止已删除或被替代内容被派生组件重新提交。

Canonical State：

- Memory Stable ID；
- Claim / content；
- provenance 和 Evidence Reference；
- owner_ref、space_id 和 scope；
- validity、version 和 lifecycle；
- source_dependency：independent / dependent / unknown；
- correction / supersede 关系；
- Retention Policy、Tombstone 和 Erasure 状态。

External Intelligence：

- extraction、consolidation、deduplication；
- retrieval、reranking、summarization；
- embedding、graph、cluster；
- Evidence 相关性和 source dependency 建议。

External Execution：

- Memory Intelligence 读取授权上下文并返回 Candidate；
- Index / Search 实现派生查询；
- Adapter 执行派生副本清除和重建。

Memory Engine、Embedding、Index 和 Graph 均不拥有 Canonical Memory。

## 6. Observation 与 World State

Core Authority：

- 接受 Observation Proposal；
- 校验 Schema、来源、时间、TTL、Owner、Space 和权限；
- 处理确定性来源规则、过期、来源禁用和用户显式优先级；
- 提交 accepted projection、stale、unknown、correction 和 deletion；
- 校验 WorldState Proposal。

Canonical State：

- accepted World State projection；
- Observation 及其类型级 Retention Policy；
- conflict candidate 和 Evidence Reference；
- schema_ref；
- source availability；
- observed_at、received_at、expires_at；
- fresh / stale / unknown；
- owner_ref、space_id、version、provenance。

External Intelligence：

- 自然语言属于 Memory 还是 World State 的分类；
- 多来源语义冲突解决；
- 状态融合、预测和异常检测；
- 刷新和关注建议。

External Execution：

- State Source Connector 采集日历、天气、位置和设备信息；
- State Resolver 作为普通 Execution Target 返回 Proposal；
- Model Worker 或 Runner 可以完成领域转换；
- 外部系统继续持有完整领域数据。

边界：

- Accepted World State 可恢复、迁移，也可以过期；
- 用户明确陈述优先，但不会永久冻结状态；
- 删除 Integration 后最后状态标记 source unavailable，并按 TTL 进入 stale / unknown；
- State Resolver 没有特权提交路径；
- Core 不实现数字孪生或领域本体。

## 7. Owner、Space 与数据治理

Core Authority：

- 创建和提交 User / Space Owner Reference；
- 提交 Space 类型和生命周期；
- 区分 owner_ref 与 created_by；
- 执行 Data Classification、Retention 和 Binding 约束。

Canonical State：

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref: User | Space
├─ space_id / created_by
├─ data_classification
├─ provenance / version
├─ retention_policy / lifecycle_state
└─ typed payload
~~~

近期边界：

- 创建默认 Personal Space 和隐式 Home Space；
- 个人资产可以归 User；
- 家庭公共状态归 Home Space；
- 暂不实现成员、角色、邀请、共享和完整 ACL。

数据等级：

- Core 定义 public、personal、sensitive、restricted；
- 无法判断时默认 sensitive；
- 用户、来源和外部分类器可以提出标签；
- 分类器可以提高等级；
- 降低等级需要用户或确定性策略确认。

Model Binding 必须声明：

- local / remote；
- 允许的数据等级；
- 是否允许 Memory、World State 和外部资产内容；
- retention / training；
- 地域和组织约束。

## 8. Skill、Executable Asset、Extension 与 Integration

Core Authority：

- 提交 Stable ID、版本、来源、信任和生命周期；
- 校验 Manifest、权限、兼容性和 Binding；
- 签发安装、升级、禁用和执行授权；
- 管理 Secret Reference，不接管 Secret Store 实现。

Canonical State：

- Skill 方法与来源；
- Executable Asset 的 source ref、version、checksum、I/O Contract；
- Extension Manifest；
- Integration 配置结构；
- MCP Connection metadata；
- Runtime / Model / Runner Profile；
- Capability 和 Provider Binding；
- Secret Reference。

External Intelligence：

- Skill 搜索、推荐和组合；
- 兼容性与升级建议；
- Capability 发现；
- 恶意或风险检测建议。

External Execution：

- Extension 代码；
- Runner、语言运行时和 Sandbox；
- MCP Client / Server；
- Provider、设备和协议；
- Secret Store。

高风险 Executable 权限绑定具体版本或 checksum；普通权限可以绑定 Stable ID。代码实质变化后，高风险授权失效。

## 9. Capability 与现实动作

Core Authority：

- 校验 Action Proposal 和 Schema；
- 执行 Capability Envelope、Policy 和 Approval；
- 分配 Action ID；
- 提交 pending、executing、succeeded、failed、unknown；
- 管理 reconciliation 和用户可见审计。

Canonical State：

- Capability Declaration；
- Provider Binding；
- Action Proposal；
- Approval Decision；
- Action Ledger；
- idempotency key；
- external reference；
- unknown outcome 和 reconciliation state。

External Intelligence：

- 参数生成；
- 风险解释；
- 最佳执行时间建议；
- reconciliation 建议。

External Execution：

- Provider Adapter 调用账户、API、设备或服务；
- Provider 返回外部 ID、结果和可验证证据。

任何组件都不能把“已请求取消”直接写成“动作未发生”。无法确认时保持 unknown。

## 10. Durable Store、导出与 Erasure

Core Authority：

- 定义 Canonical Record 和一致性要求；
- 选择 Primary Store Binding；
- 提交 Migration、Export 和 Integrity 状态；
- 管理 restricted mode、Erasure Intent 和组件完成状态；
- Store 不可用时阻止无记录现实副作用。

Canonical State：

- Store Binding 和 Capability；
- Schema Version；
- Migration Plan / Result；
- Integrity Report；
- Export Manifest；
- Backup Metadata；
- Erasure Request、Tombstone、pending / unreachable status；
- Outbox reconciliation reference。

External Execution：

- 数据库、事务、复制和物理备份；
- 加密 Secret Store；
- 可靠持久 Outbox；
- Adapter 中的具体擦除；
- 导出打包和完整性计算。

两种产物：

1. 标准可移植导出不包含 Secret 内容和可重建状态；
2. 完整设备备份可以包含加密 Secret、Checkpoint 和部分派生状态，但必须独立授权和加密。

Primary Store 不可用时：

- 只读和明确标记的临时交互可以继续；
- Canonical Commit 暂停；
- 现实副作用默认禁止；
- 只有预先配置的紧急 Capability 可以先写可靠 Outbox，再执行；
- 恢复后进行幂等提交、去重和 reconciliation。

## 11. Scheduler、Health 与 Semantic Pulse

Core Authority：

- 提交 Schedule、Trigger、Lease、Timeout 和 bounded Run；
- 执行预算、权限和 Capability Envelope；
- 校验 Pulse Proposal；
- 提交由 Proposal 产生的状态或 Task。

Canonical State：

- schedule / trigger identity；
- next occurrence 和 last outcome；
- health / lease summary；
- Pulse Run、Usage 和 Proposal status。

External Intelligence：

- Semantic Pulse；
- 主动 Recall；
- 状态更新、Run、Task 和升级建议。

External Execution：

- Scheduler 和 Clock；
- Health Probe；
- Model Worker / rule program；
- Infrastructure Adapter。

System Health、TTL、Lease、Timeout、Scheduler Tick 和恢复不依赖 LLM。Semantic Pulse 可以自动运行无现实副作用且满足预算的 Run，但不能直接修改 Canonical State，也不能直接创建 Durable Task 或现实副作用。

## 12. Interaction、Voice 与设备入口

Core Authority：

- 准入 Chat、CLI、API、Voice、Event 和 Schedule 请求；
- 绑定 Owner、Space、Session 和 Endpoint；
- 执行数据和动作权限；
- 保存用户明确路由、纠正、批准和拒绝。

Canonical State：

- Interaction Endpoint metadata；
- Session reference；
- Device / Integration Binding；
- user decision 和 preference；
- minimal Admission / Run reference。

External Intelligence 与 Execution：

- STT、TTS、Wake Word；
- Speaker recognition；
- Audio routing；
- Voice UX；
- Device transport；
- 多麦克风和扬声器协调。

近期仅实现单用户入口 Contract，不实现家庭成员识别、角色权限和分布式音频系统。

## 13. 必须由 Core 实现

1. Stable ID 和 versioned Domain Contract；
2. Admission Record、Request、Run、Attempt 和 Durable Task 状态机；
3. Authority 和合法状态转换；
4. Execution Requirements、Binding 和 Capability Envelope 校验；
5. Canonical Memory 和 World State 提交语义；
6. Owner、Space、Data Classification 和 Retention 执行点；
7. Asset、Extension、Integration 和 Capability Registry；
8. Policy Enforcement、Approval 和 Action Ledger；
9. Migration、Export、Integrity、Erasure 和 restricted mode 状态；
10. Adapter Registry、版本协商和 Contract Test；
11. 用户查看、纠正、撤销、删除和导出 API。

## 14. 必须外置

1. Agent Runtime、Planner、Subagent、Tool Loop 和通用 Workflow Engine；
2. Model Provider、推理和智能 Router；
3. Memory 提取、整理、召回、Embedding、Graph 和 Index；
4. State Source、语义 Resolver、预测和数字孪生；
5. Script Runtime、依赖管理、Sandbox 和资源隔离；
6. 数据库、Secret Store、物理备份和可靠 Outbox；
7. Search Engine、Scheduler、Telemetry backend；
8. STT、TTS、Wake Word 和音频处理；
9. Browser Agent、Coding Agent、设备协议和 Provider 实现；
10. 领域 Schema 和领域数据生命周期。

## 15. Stage 1 退出条件

本阶段完成时必须满足：

- 每个需求领域都明确 Authority；
- 每类 Canonical State 都有稳定所有者；
- 每项智能能力都能被替换；
- 每项具体执行都通过 Port 或 Adapter 外置；
- Core 不持有模型评分、Memory 算法、State Resolver、数据库或设备协议；
- External Component 没有直接提交权威状态的路径；
- 单用户实现不阻塞未来 User / Space 扩展；
- Store、模型、Runtime 和 Adapter 故障路径不依赖隐式行为；
- 后续关键用例可以直接引用本矩阵确定参与者和责任。

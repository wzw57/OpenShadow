# OpenShadow 分阶段实现计划

- 状态：Stage 4 完整目标架构的实现顺序
- 目标：分阶段交付 Tiny Kernel、官方 Profile 与可替换 Extension
- 原则：Phase 是同一架构的真子集，不是独立 MVP 架构

## 1. 分阶段原则

OpenShadow 的完整目标覆盖长期记忆、任务连续性、State、能力资产、现实动作、多端入口和组件升级，但不应一次实现所有能力。

阶段化遵循：

1. 先实现 Kernel 原语，再增加 Profile；
2. 未实现能力保留必要 Contract，不预建空服务或表；
3. Profile 属于兼容承诺，但不通过硬编码类型分支扩张 Kernel；
4. namespaced target kind 与 Capability 允许后续增加执行方式；
5. 每阶段必须能独立运行和验证；
6. 任何临时实现不得绕过 Proposal / Commit；
7. 不以“以后可能需要”为理由建设插件操作系统、通用 Workflow、Event Bus 或 Policy Language。

## 2. 成熟度标记

| 标记 | 含义 |
|---|---|
| KERNEL | 当前实现且长期稳定 |
| CONTRACT-ONLY | 冻结最小边界，不实现完整能力 |
| PROFILE | 实现官方 typed Profile |
| ADAPTER | 接入可替换实现 |
| DERIVED | 可以删除重建 |
| LATER | 延后到有真实用例的 Phase |

## 3. 第一版不可省略的基础

- Stable ID；
- owner_ref / space_id / created_by；
- schema_ref / profile_id；
- Canonical version，以及 Mutation Input 的 expected_version；
- Canonical Envelope；
- Proposal / Commit identity；
- work-bearing Admission；
- Request / Run / Attempt；
- namespaced target_kind；
- Binding / minimal Capability Envelope；
- minimal AdapterDescriptor；
- Canonical Repository Capability；
- Secret Reference 与普通配置分离；
- correlation_id / causation_id；
- structured error；
- Migration version。

不要求第一版实现：

- 所有官方 Profile；
- 智能 Router；
- State Resolver；
- 现实 Action；
- Semantic Pulse；
- 复杂 ACL；
- Backup / Outbox；
- 通用消息队列或微服务。

## 4. 阶段总览

~~~mermaid
flowchart LR
    P0["Phase 0<br/>Kernel Foundation"]
    P1["Phase 1<br/>Personal Shadow Loop"]
    P2["Phase 2<br/>Memory & Capability Profiles"]
    P3["Phase 3<br/>Continuity & State Profile"]
    P4["Phase 4<br/>Action & Proactivity"]
    P5["Phase 5<br/>Multi-endpoint & Multi-user"]

    P0 --> P1 --> P2 --> P3 --> P4 --> P5
~~~

## 5. Phase 0：Kernel Foundation

### 实现

- Python / FastAPI 工程骨架；
- checked-in JSON Schema / OpenAPI；
- CanonicalEnvelope；
- Principal / Personal Space；
- Schema / Profile Registry；
- ProposalEnvelope / Canonical Commit；
- ExpectedVersion；
- AdmissionRecord / Request / Run / Attempt skeleton；
- ExecutionBinding / minimal CapabilityEnvelope；
- minimal AdapterDescriptor；
- Family Port interfaces；
- Canonical Repository Capability；
- SQLite WAL / SQLAlchemy / Alembic；
- Deterministic Test Adapter；
- Contract Test harness；
- health / readiness；
- structured logging and correlation。

### 暂不实现

- Conversation / Memory 完整 Profile；
- 智能 Router；
- Runtime checkpoint；
- State / Action；
- Skill installation；
- Portable Export UI；
- Queue / Outbox；
- 多用户。

### 退出条件

- Canonical Commit 可以原子创建新版本；
- expected-version conflict 被拒绝；
- Adapter 不能直接访问 Repository；
- Descriptor 和 Capability 可独立验证；
- unknown target kind 可按 Descriptor 处理，而不是 enum crash；
- Kernel package 不依赖 Profile payload、FastAPI DTO 或 SQLAlchemy Entity；
- Store 只承诺 Canonical Repository Capability。

## 6. Phase 1：Personal Shadow Loop

### 实现

- Local Web；
- Conversation / Message Profile；
- work-bearing chat Admission；
- Request → Root Run → Attempt；
- static Binding；
- `shadow.model-worker` 或 `shadow.agent-runtime` 之一；
- Runtime base Port：describe / execute / events；
- SSE Run stream；
- Result Commit；
- Memory Profile 最小 Candidate / Commit；
- restart recovery；
- explicit ephemeral interaction when Store unavailable。

### 保留但不提前实现

- `target_kind` 是 namespaced string，不预建所有 Target 实现；
- optional cancel / checkpoint / resume 只在 Adapter 声明后启用；
- Durable Task 只有 reference / contract；
- State / Action / Skill 只有 Profile registration ability；
- 复杂 Policy Engine 不实现。

### 退出条件

- 用户可以通过 Web 完成对话；
- 每个 Accepted Request 只有一个 Root Run；
- Retry 追加 Attempt；
- 只读 control-plane query 与 SSE subscription 不创建 Run；
- 更换 Model / Runtime Adapter 不改变 Run / Message ID；
- 普通 Result 不自动成为 Memory；
- Memory Candidate 必须经过 Commit；
- Store 不可用时不伪造持久成功；
- 没有声明 cancel 的 Adapter 返回 unsupported。

## 7. Phase 2：Memory 与 Capability Profiles

### 实现

- Canonical Memory Envelope version / correction / supersede；
- source_dependency；
- logical delete / physical erase；
- anti-resurrection Tombstone；
- Memory Maintenance Adapter；
- Recall Adapter；
- Integration Profile；
- SkillAsset Profile；
- Agent Skills Bundle validation；
- immutable snapshot / pinned revision / digest；
- Shadow sidecar governance metadata；
- Runtime Projection rebuild；
- Executable Asset / Runner；
- Asset Catalog 与按需读取；
- 基础 Portable Export / Import；
- derived index rebuild。

### 保留但不提前实现

- 多 Memory Engine composition；
- 自动 Router；
- 复杂 Skill marketplace；
- 自定义 Shadow Skill 内容格式；
- 领域知识图谱；
- 完整跨组件 Erasure orchestrator。

### 退出条件

- Memory Intelligence 替换不丢失 Canonical Memory；
- Profile major migration 有显式测试；
- Skill Bundle 可以被标准 Agent Skills 客户端读取；
- Shadow metadata 不修改原 Bundle；
- `allowed-tools` 不会绕过 CapabilityEnvelope；
- Provider Skill ID 仅为 External Reference；
- 删除 index 后可以重建；
- 外部资产仍按需读取，不复制为默认长期库。

## 8. Phase 3：Continuity 与 State Profile

### 实现

- Durable Task Profile；
- task / Run / checkpoint / artifact refs；
- waiting / pause / resume / deadline / trigger；
- Semantic Checkpoint / handoff；
- Schedule / Clock Adapter；
- State Profile；
- Observation / StateProposal；
- state_key / typed value / Evidence；
- observed_at / expires_at；
- fresh / stale / unknown；
- source unavailable；
- State Source Adapter；
- optional State Resolver；
- Migration / Integrity Store Capabilities；
- 受限 OperationJob：export / import / migration。

### 当前交付切片

Phase 3 全部当前范围已按 ADR-0013 与 ADR-0014 实现并合并到 `main`，覆盖
State/Observation/StateProposal Contract、TTL/freshness、Durable Task 生命周期、
Checkpoint/Handoff、Schedule/Clock、State condition Admission、Migration/Integrity、
Proposal/Commit、重启恢复和确定性 Adapter。真实外部 Integration 联动仍不在本阶段。

### 保留但不提前实现

- 复杂 Task Graph；
- 通用 Workflow Engine；
- 领域本体；
- 预测 / anomaly detection；
- 持续实时数字孪生；
- 完整家庭设备系统。

### 退出条件

- Runtime 崩溃后 Task 可以从 Canonical refs 恢复；
- 没有 native resume 时不会伪装原 Session 恢复；
- Run success 不自动完成 Task；
- State Resolver 只能 Proposal；
- 重启后知道最后 accepted state 与 expires_at；
- 过期状态不能保持 fresh；
- 删除 Integration 后状态进入 source unavailable / stale / unknown；
- State condition 重新进入 Admission。

## 9. Phase 4：Action 与 Proactivity

### 实现

- Action Profile；
- ActionProposal / approval；
- pending-before-provider-call；
- idempotency key；
- succeeded / failed / unknown；
- reconciliation；
- deterministic Policy primitives；
- optional Policy Engine Adapter；
- Router Adapter；
- Semantic Pulse；
- Durable Outbox Capability；
- 跨组件 Erasure；
- 完整标准 Export 与 encrypted device backup metadata。

### 保留但不提前实现

- 通用 Policy Language；
- 自动执行高风险现实 Action；
- 多主 Memory writing；
- 通用 Event Bus；
- 通用后台 Job Platform。

### 退出条件

- 未持久化 Action 不能执行；
- unknown outcome 不盲目 retry；
- Policy Engine 不能直接签发权限；
- Pulse 只能 Proposal；
- Store 故障时现实副作用默认暂停；
- Outbox 只用于可靠副作用；
- OperationJob 仍限定在 portability / erasure。

## 10. Phase 5：Multi-endpoint 与 Multi-user

### 实现候选

- endpoint pairing；
- 多 Web / Mobile client；
- Voice endpoint；
- STT / TTS / wake word adapters；
- Space membership / role / invitation；
- Home Space shared state；
- device trust；
- remote Store / synchronization profile；
- distributed audio。

### 约束

- 不改变现有 owner_ref / space_id；
- 不把个人 Memory 自动转成共享资产；
- 每个 Endpoint 仍经过 Admission；
- 家庭设备与音频协议外置；
- 多用户不能绕过现有 Proposal / Commit 和 data boundary。

### 退出条件

- 同一 Shadow 可从多个 Endpoint 继续；
- 共享 State 归正确 Space；
- 用户资产可以导出并迁移；
- 单用户部署仍然简单。

## 11. 架构能力矩阵

| Capability | P0 | P1 | P2 | P3 | P4 | P5 |
|---|---|---|---|---|---|---|
| Tiny Kernel | Implement | Stable | Stable | Stable | Stable | Stable |
| Canonical Envelope / Commit | Implement | Use | Use | Use | Use | Use |
| Profile Registry | Skeleton | Conversation / Memory min | Memory / Skill / Integration | Task / State | Action | ACL extensions |
| Run / Attempt | Skeleton | Implement | Stable | Task-linked | Action-linked | Endpoint-linked |
| target_kind | namespaced contract | one implementation | Runner added | Workflow compatible | Router selects | extended |
| Runtime optional capabilities | contract | negotiated subset | extended | checkpoint / handoff | reconcile | endpoint-aware |
| Canonical Repository | SQLite | Stable | Stable | Integrity / Migration | Outbox optional | remote profile |
| Memory Intelligence | Deferred | none / test | Adapter | Replaceable | optional composition | extended |
| State | Profile contract | Deferred | source refs | Implement | trigger integration | shared spaces |
| Skill | Standard contract | Deferred | Agent Skills Profile | Stable | provider projections | shared governance |
| Action | Safety contract | Deferred | registry refs | Proposal-only | Implement | multi-user approval |
| Semantic Pulse | Deferred | Deferred | Deferred | Contract-only | Optional | Optional |
| Multi-user ACL | Owner / Space fields | Deferred | Deferred | Deferred | Contract-only | Implement |

## 12. 每阶段共同工程规则

1. 所有 Canonical writes 经过 Commit；
2. 所有 Profile payload 有 schema_ref；
3. Profile Validator 不直接写 Repository；
4. Adapter 只声明真实 Capability；
5. unknown required Capability 拒绝 Binding；
6.未知 target kind 按 Descriptor / Capability 判断；
7. Secret 不进入普通记录或日志；
8. Derived State 可以删除重建；
9.每个 Phase 有 export / migration regression fixture；
10. failure / timeout / restart paths 必须测试；
11.用户可见状态不得把 unknown 显示为成功；
12.不引入没有真实使用者的基础设施抽象。

## 13. 禁止的阶段性捷径

- Web Client 直接写数据库；
- Runtime 直接写 Memory、State 或 Task；
- 用 SDK Session ID 代替 Run / Task ID；
- 把所有 Profile 写成 Kernel enum / switch；
- 把五个 well-known target kinds 冻结成全集；
- 让所有 Port 返回一个万能 Result union；
- 要求所有 Adapter 支持 cancel / checkpoint / migration；
- 把 Durable Store Port 做成数据库产品抽象；
- 修改 Agent Skills Bundle 写入 Shadow 私有元数据；
- 用 `allowed-tools` 授予实际权限；
- 把 Domain Event 当作事实源；
- 把 OperationJob 做成通用 Workflow；
- 为未来多用户提前实现完整 ACL；
- 以短期交付为理由绕过 Owner / Space / Version。

## 14. 已接受的参考实现

参考实现采用：

- Python Kernel；
- FastAPI；
- React + TypeScript + Vite；
- REST / JSON / OpenAPI 3.1；
- SSE；
- checked-in JSON Schema；
- in-process Python Family Port；
- isolated UTF-8 NDJSON Message Envelope over stdio；
- SQLite WAL、SQLAlchemy、Alembic；
- PostgreSQL 作为第二 Store Profile；
- Deterministic Test、OpenAI Model 与 Process Runtime Adapters。

这些是可替换 Profile，不进入 Canonical Domain 或 Stable ID。

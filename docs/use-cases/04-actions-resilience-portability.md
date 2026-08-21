# 外部动作、故障与可移植性用例

## UC-011 受治理的外部 Action

### 目标

Shadow 在调用账户、API、设备或其他现实能力前完成权限、审批、幂等和审计。

### Actor

User；Runtime / Model / Runner；Shadow Policy Authority；Capability Provider。

### Trigger

执行组件提交 Action Proposal，或用户明确请求一个有现实副作用的 Capability。

### Preconditions

- Capability Declaration 和 Provider Binding 有效；
- Owner / Space 和 Acting User 有权；
- Primary Store 可提交；
- Action Schema、风险和数据等级可判断；
- Provider 健康。

### Main Flow

1. 外部组件返回 Action Proposal，不直接调用 Provider。
2. Core 校验 Schema、Capability Envelope、数据范围、费用、风险和目标资源。
3. Core 分配 Action ID 和 idempotency key。
4. Policy 决定：
   - auto-approved；
   - approval required；
   - hard deny。
5. 需要批准时，Approval 发送到符合 Risk / Device Trust 的 Endpoint。
6. 用户看到动作、目标、关键参数、费用、数据披露和可取消时限。
7. 批准后 Core 先提交 Action pending。
8. Provider Adapter 使用 idempotency key 执行。
9. Provider 返回 external reference 和 Result。
10. Core 提交 succeeded / failed，并写 Action Ledger。
11. UI 更新所有设备上的状态。

### Failure Flow

- hard deny 不可覆盖；
- Approval 过期或版本变化时失效；
- Provider Binding 改变时重新校验；
- 请求取消只进入 cancelling，除非 Provider 确认未执行；
- Primary Store 不可用时默认禁止；
- 只有预配置紧急 Capability 可以先写可靠 Outbox 再执行。

### Durable State Changes

Action Proposal、Action ID、Approval、Policy Decision、Provider Binding、idempotency key、Action state、external reference、Ledger。

### External Side Effects

Provider 执行真实查询、写入、消息、设备控制或费用操作。

### Acceptance Criteria

- Runtime、Model、Runner 不能绕过 Shadow 调 Provider；
- Action 执行前已有可恢复 pending record；
- 重复提交相同 idempotency key 不重复副作用；
- 高风险 Approval 只能在合格 Trusted Device 完成；
- Policy、Binding 和参数版本可以审计。

## UC-012 Action Unknown Outcome 与 Reconciliation

### 目标

当网络、Provider 或 Runtime 故障导致动作是否发生无法确认时，Shadow 不误报成功或盲目重试。

### Actor

Shadow Core；Provider Adapter；Scheduler；User。

### Trigger

请求已发送但未获得可信最终结果，或取消确认丢失。

### Preconditions

Action 已有持久 Action ID、idempotency key 和 pending / executing record。

### Main Flow

1. Adapter 报告 transport failure with uncertain delivery。
2. Core 提交 unknown，而不是 failed。
3. Core 阻止同一 Action 的非幂等重试。
4. Reconciliation Job 使用 external reference、idempotency key 或查询 Capability 检查 Provider。
5. Provider 返回 confirmed succeeded、confirmed not executed 或 still unknown。
6. Core 提交最终状态或安排下一次受限检查。
7. 用户看到当前不确定性、潜在影响和可用操作。

### Failure Flow

- Provider 不支持查询时保持 unknown，并请求人工确认；
- 用户选择重试时创建明确的新 Action 或使用 Provider 保证的相同幂等键；
- Runtime Handoff 不重放 unknown Action；
- 长期无法确认时 Task 不能自动 completed。

### Durable State Changes

unknown state、reconciliation attempts、evidence、next check、user decision、final state。

### External Side Effects

只读查询或人工确认；任何重试仍受完整 Action Flow 管理。

### Acceptance Criteria

- uncertain delivery 不写成 failed 或 succeeded；
- Handoff 和恢复不会重复副作用；
- reconciliation history 可查看；
- Task 完成依赖明确结果或用户接受 unknown。

## UC-013 Primary Store 故障与受限模式

### 目标

Primary Durable Store 暂时不可用时，Shadow 保持有限可用，同时不破坏持久性和现实动作审计。

### Actor

User；Shadow Core；Store Adapter；Health / Scheduler；紧急 Capability Provider。

### Trigger

Store health、transaction 或 commit 失败。

### Preconditions

Shadow 已知当前 Primary Store Binding 和 Capability。

### Main Flow

1. 确定性 Health 将 Store 标记 unavailable。
2. Core 进入 restricted mode，并通知所有 Interaction Client。
3. 允许：
   - 读取仍可安全读取的已有 Snapshot；
   - 明确标记的临时对话；
   - 不产生长期状态和副作用的 Ephemeral Run。
4. 暂停：
   - Canonical Commit；
   - Durable Task 创建与完成；
   - Memory / World State 提交；
   - 普通外部 Action。
5. Store 恢复后执行健康验证和一致性检查。
6. Core 退出 restricted mode。
7. Ephemeral Result 默认不补写；用户可以将仍在进程中的结果显式保存为新资产，并记录 degraded provenance。

### Emergency Outbox Flow

1. 只有预配置的紧急 Capability 可以使用。
2. Core 先把意图写入独立、可靠、本地持久 Outbox。
3. Outbox 成功后才允许 Provider 执行。
4. Store 恢复后幂等导入 Action、去重并 reconciliation。
5. Outbox 不可用时禁止执行。

### Failure Flow

- Store 反复抖动时保持 restricted，避免部分提交；
- 只读 Snapshot 已过期时明确显示 stale；
- Shadow 进程重启会丢失普通 Ephemeral Run；
- Emergency Action outcome unknown 时按 UC-012；
- 不允许把普通所有请求都写入 Outbox。

### Acceptance Criteria

- Store 故障不会产生未记录现实副作用；
- 用户清楚知道临时结果不保证保存；
- Ephemeral Run 不自动变成伪造的 Canonical 历史；
- Outbox 先于紧急副作用持久化；
- 恢复后完成幂等导入和 reconciliation。

## UC-014 标准导出、完整备份与恢复

### 目标

用户可以跨实现迁移长期资产，或创建包含更多设备状态的加密恢复备份。

### Actor

User；Shadow Portability Authority；Store / Secret / Adapter；目标 Shadow 环境。

### Trigger

用户请求标准导出、完整设备备份、迁移或恢复。

### Preconditions

- 操作来自符合要求的 Trusted Device；
- User 对目标 Owner / Space 有权；
- Primary Store 可用且一致；
- 导出范围和数据等级已确认。

### Main Flow：标准导出

1. 用户选择 Owner、Space 和资产范围。
2. Core 创建 Export Plan 和版本化 Manifest。
3. 导出 Canonical Assets、关系、Integration metadata、Bindings、Schemas、Migration metadata 和 Secret References。
4. 排除 Secret 内容、Engine 私有状态和可重建索引。
5. 计算完整性摘要并生成可验证包。
6. 目标环境验证版本、完整性和兼容性。
7. Migration 生成计划和预览。
8. 用户批准后导入，保持 Stable ID、关系和 provenance。
9. 导入完成后运行 Contract / Integrity Check。

### Main Flow：完整设备备份

1. 用户单独选择 Full Backup。
2. UI 明确提示它不是通用兼容格式。
3. 备份可以包含加密 Secret、Checkpoint 和选择的派生状态。
4. 使用独立密钥或外部密钥引用加密。
5. 恢复时先验证身份、密钥、版本和完整性。
6. 不兼容私有状态可以丢弃重建，不能阻塞 Canonical Assets。

### Failure Flow

- unreachable Adapter 在 Manifest 中报告 incomplete；
- restricted 数据需要更高设备信任和确认；
- Secret 解密失败不阻止非 Secret Canonical Asset 导入；
- Stable ID 冲突进入显式 merge / replace / abort，不静默覆盖；
- Migration 失败不修改现有目标状态，或通过 Store transaction 回滚。

### Acceptance Criteria

- 标准导出不依赖具体 Store 或 Engine 私有格式；
- Secret 内容不进入标准导出；
- Full Backup 独立加密授权；
- Runtime、Memory Engine 和数据库替换后 Stable ID 与关系保持；
- 派生数据可以重建；
- 导入失败不会留下未声明的部分状态。

## UC-015 Erasure 跨组件传播

### 目标

用户物理删除 Canonical Asset 时，Shadow 追踪所有受管组件中的原始、派生、缓存和备份副本。

### Actor

User；Shadow Erasure Authority；Store、Memory、Index、Cache、Backup 和 Integration Adapter。

### Trigger

恢复窗口到期或用户要求立即物理清除。

### Preconditions

- Logical Delete 已存在，或用户明确跳过恢复窗口；
- 发起设备和 User 权限满足数据风险；
- Erasure Scope 可计算。

### Main Flow

1. Core 创建 Erasure Request 和受影响对象集合。
2. Primary Store 提交 erase intent，阻止新 Recall 和派生。
3. Core 向所有受管 Adapter 发送版本化 Erasure Command。
4. Adapter 返回 completed、scheduled、pending、unreachable 或 failed。
5. Backup Adapter 返回最长保留和清除计划。
6. Core 展示逐组件状态。
7. 全部满足 Policy 后提交 Erasure completed。
8. 只保留不含敏感原文的最小 Tombstone，防止旧 Candidate 复活。

### Failure Flow

- unreachable 组件保持未完成，不谎报成功；
- 外部来源不受 Shadow 控制时说明仅删除 Shadow 副本；
- 组件恢复后继续处理同一 Erasure Request；
- 新组件重建索引时必须消费 Tombstone / erase marker；
- 用户删除 Conversation 不自动删除已独立提交且策略允许保留的 Memory，除非 Erasure Scope 明确包含。

### Acceptance Criteria

- 用户可以查看每个组件的状态；
- pending / unreachable 不显示为完成；
- 敏感原文不保留在 Tombstone；
- 已删除内容不会由旧 Index 或 Candidate 自动恢复；
- 外部来源与 Shadow 管理副本的责任明确。

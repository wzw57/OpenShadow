# Memory 与 World State 用例

## UC-007 Memory Candidate 提交与周期整理

### 目标

Shadow 从对话、Task 或按需读取的外部资产中形成长期 Memory，同时允许更换 Memory Intelligence。

### Actor

User、Scheduler、Runtime；Memory Intelligence；Shadow Memory Authority；Source Connector。

### Trigger

- 当前 Run 产生可能有长期价值的信息；
- 用户明确要求记住；
- Task 完成；
- 周期性 Memory Consolidation Schedule；
- 授权的外部资料整理。

### Preconditions

- 数据 Owner、Space、Classification 和 Retention 已确定；
- Memory Component Binding 有效；
- 外部资产按需访问权限有效；
- Primary Store 可提交。

### Main Flow

1. Core 创建受限 Memory Processing Run。
2. Core 根据 Policy 裁剪 Conversation、Task、World State 或外部资产内容。
3. Memory Intelligence 执行提取、去重或整理。
4. 组件返回 Memory Candidate，不直接写 Canonical Store。
5. Candidate 包含 Claim / content、provenance、Evidence refs、scope、classification、source_dependency 和建议操作。
6. Core 校验来源、权限、冲突、版本和用户规则。
7. Core 创建、合并、替代或拒绝 Candidate。
8. Canonical Memory 提交到 Primary Store。
9. Embedding、Index、Graph 和 Projection 异步重建或更新。
10. 用户可以查看提交结果和来源。

### Failure Flow

- 外部资产不可访问时保留 unavailable evidence，不伪造内容；
- Memory Component 失败不改变已有 Canonical Memory；
- Candidate 缺少 provenance 或无法确定 classification 时默认 sensitive 或拒绝；
- 冲突 Candidate 不直接覆盖用户纠正；
- 派生索引失败时 Canonical Commit 仍然有效，并记录 rebuild pending；
- Semantic Pulse 只能触发受预算限制的 Run。

### Durable State Changes

Memory Candidate decision、Canonical Memory、Evidence refs、source_dependency、version / supersede、derived rebuild status。

### External Side Effects

按需读取外部资产；调用 Memory / Model / Search 组件。

### Acceptance Criteria

- 更换或删除 Memory Intelligence 后 Canonical Memory 仍存在；
- 组件不能绕过 Candidate 流程；
- 外部原始内容不因整理自动复制进 Shadow；
- 派生状态可删除重建；
- 周期整理失败不破坏已有 Memory。

## UC-008 Memory 纠正、来源失效与删除

### 目标

用户可以纠正、使 Memory 失效、逻辑删除并最终物理清除，同时防止旧派生状态使错误内容复活。

### Actor

User；Shadow Memory Authority；Source Connector；Memory / Index / Backup Adapters。

### Trigger

用户纠正或删除 Memory，或外部 Evidence Source 被删除、撤销或不可访问。

### Preconditions

Memory 存在且用户有权管理其 Owner / Space。

### Main Flow：纠正

1. 用户提交新值和可选原因。
2. Core 创建新 Memory Version。
3. 旧版本标记 superseded，并建立关系。
4. Recall 默认排除旧版本。
5. 派生组件收到 invalidation / rebuild。
6. 敏感内容需要彻底擦除时进入 Erasure Flow。

### Main Flow：来源失效

1. Source Connector 报告 unavailable / deleted。
2. Core 将 Evidence Reference 标记不可访问。
3. 根据 source_dependency：
   - independent：Memory 保留；
   - dependent：Memory 失效或删除；
   - unknown：进入 review required。
4. 用户界面显示来源状态和影响。

### Main Flow：删除

1. 用户请求删除。
2. Core 默认提交 logical deleted，并允许 Policy 定义的恢复窗口。
3. 到期或用户立即要求物理清除时，创建 Erasure Request。
4. 各 Adapter 删除内容、Index、Cache、Graph、Backup copy。
5. Core 记录 completed、pending 或 unreachable。
6. 最小 Tombstone 只保留防止错误复活所需的 ID、erase marker 和非敏感关系。

### Failure Flow

- Adapter 不可达时不能报告完成；
- Backup 无法立即删除时记录计划和最长保留；
- 用户无权管理该 Space 时拒绝；
- Memory Engine 再次提出已删除内容时，Tombstone 触发拒绝或人工复核；
- 敏感历史彻底擦除后，不保留原文版本审计。

### Acceptance Criteria

- 纠正不会被旧 Index 覆盖；
- dependent Memory 随来源删除进入正确状态；
- 用户拥有最终物理清除权；
- unreachable 组件明确显示；
- Tombstone 不包含被删除的敏感内容。

## UC-009 Observation 更新 World State

### 目标

用户或外部来源提交 Observation，Shadow 形成可恢复、带来源和时效的 accepted World State。

### Actor

User、State Source Connector；Shadow State Authority；可选 State Resolver。

### Trigger

设备、Calendar、Weather、Location、用户陈述或其他来源报告状态。

### Preconditions

- Source / Integration 有效；
- 领域 schema_ref 已注册；
- Owner / Space 和数据等级可确定；
- Primary Store 可提交。

### Main Flow

1. Source 提交 Observation Proposal，包含 subject、property、value、source、observed_at、received_at 和 TTL。
2. Admission 校验来源、Schema、权限和重放。
3. Observation 不自动创建 Run。
4. Core 应用确定性规则：用户明确优先、时间、TTL、来源禁用和已有固定 Policy。
5. 无复杂冲突时，Core 提交 Observation 和 accepted projection。
6. 复杂冲突时，Core 创建受限 Resolution Run。
7. State Resolver 返回 WorldState Proposal 和证据解释。
8. Core 校验并提交 accepted projection、conflict refs 和 freshness。
9. 有匹配 Condition 时创建 Run 或 Task Proposal。
10. Web 多端收到状态更新事件。

### Failure Flow

- Schema 无效或来源撤销时只产生 Admission Record；
- 无法可靠决定时保留 conflict，并将 Projection 标记 unknown，而非强行选值；
- Resolver 不可用时确定性 TTL 和 stale 转换仍然运行；
- 用户陈述优先但不会永久冻结；更新、更可靠的 Observation 可以替代；
- 高频 Observation 按类型 Retention Policy 压缩或删除。

### Durable State Changes

Observation、accepted World State Projection、conflicts、Evidence refs、freshness、expires_at、owner_ref / space_id、source status。

### External Side Effects

可能按需调用 Source 或 Resolver；不会自动产生现实动作。

### Acceptance Criteria

- Source 不能直接修改 Projection；
- Accepted World State 重启后可恢复；
- Resolver 删除后 TTL、stale 和 unknown 仍正常；
- 不确定状态不会伪装成确定事实；
- Observation 不默认创建 Run。

## UC-010 World State 冲突、过期与来源删除

### 目标

Shadow 在多来源冲突、TTL 到期或 Integration 删除时保持诚实、可解释的当前状态。

### Actor

Scheduler / Clock、User、State Source、State Resolver、Shadow State Authority。

### Trigger

新冲突 Observation、expires_at 到期、Source unavailable、Integration 删除或用户纠正。

### Preconditions

存在 World State Projection 或相关 Observation。

### Main Flow：过期

1. 确定性 Scheduler 检测 expires_at。
2. Core 将 Projection 从 fresh 转为 stale。
3. Policy 可以请求 Source Refresh。
4. 无可用来源或超过最大陈旧期时转为 unknown。
5. 最后接受值、来源、时间和不可信原因继续可恢复。

### Main Flow：冲突

1. Core 保存所有符合 Retention 的冲突 Observation。
2. 确定性规则先处理明确优先级。
3. 其余冲突交给可替换 Resolver。
4. Core 提交 accepted projection，保留候选与 Evidence refs。
5. 用户可以查看和纠正。

### Main Flow：删除 Integration

1. Integration Registry 提交 disabled / deleted。
2. 相关 Source 标记 unavailable。
3. 最后 Projection 保留，不立即假装消失。
4. 状态按 TTL 进入 stale / unknown。
5. 用户可以额外请求删除相关 Observation 和 Projection，进入 Erasure Flow。

### Failure Flow

- Refresh 失败不延长原 TTL；
- Resolver 结果缺少证据或超出 Scope 时拒绝；
- 用户纠正属于高优先级 Observation，但后续更可靠信息仍可替代；
- 多来源全部失效时不得继续显示 fresh；
- 删除 Source 不等于自动删除由其形成的 independent Memory。

### Acceptance Criteria

- 重启后仍知道最后状态为什么 stale / unknown；
- Integration 删除不会留下永久 fresh 状态；
- Resolver 不拥有最终提交权；
- 冲突证据可供未来 Resolver 重算；
- World State 与 Memory 生命周期保持分离。

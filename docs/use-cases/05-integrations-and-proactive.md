# Integration、外部资产与主动智能用例

> Integration 使用 Family Profile；Semantic Pulse 是可替换 Proposal producer。Skill Bundle 遵循 Agent Skills 标准，Shadow 只持有治理 sidecar。

## UC-016 安装、配置与撤销 Integration

### 目标

用户把一个外部账户、数据源或能力接入 Shadow，并将配置和权限作为可迁移能力资产管理。

### Actor

User；Trusted Web Endpoint；Extension / Integration Registry；Secret Store；Adapter。

### Trigger

用户选择安装 Extension、创建 Integration、更新配置、禁用或删除连接。

### Preconditions

- Manifest 和 Adapter Contract 版本可识别；
- 用户从符合风险要求的设备操作；
- Extension 来源、签名或 trust metadata 可检查。

### Main Flow

1. Web 展示 Extension / Integration 提供的 Capability、所需权限、数据边界、外部副作用和 Secret 要求。
2. 用户选择 Owner / Space 和允许范围。
3. Core 校验 Manifest、兼容性、权限和风险。
4. Secret 由 Secret Store 保存；Integration 只持有 Secret Reference。
5. Core 创建 Integration Stable ID、版本、Binding 和 lifecycle。
6. Adapter 执行连接测试并返回 Health / Capability Descriptor。
7. Core 提交 active 或 degraded 状态。
8. Integration 可以被 Asset Source、State Source 或 Capability Provider 使用。
9. 更新版本时重新执行兼容性和高风险授权检查。

### Disable / Delete Flow

1. Disable 立即阻止新 Binding，但保留配置和历史引用。
2. Delete 撤销 Secret Reference 和权限，并将 Source 标记 unavailable。
3. 相关 State Profile Record 按 TTL 进入 stale / unknown。
4. 相关 Memory 按 source_dependency 处理。
5. 用户可选是否对 Integration metadata、Observation 和 Shadow 副本发起 Erasure。

### Failure Flow

- Secret 验证失败时不提交 active；
- Adapter 不兼容时保持 disabled；
- 删除后收到事件只创建 revoked-source Admission Record；
- 外部账户中的原始数据不由 Shadow 自动删除；
- Extension 更新改变高风险代码或权限时重新批准。

### Durable State Changes

Extension / Integration Stable ID、Manifest version、Owner / Space、permissions、Secret Reference、Capability Binding、health、lifecycle 和 source availability。

### External Side Effects

写入或撤销 Secret Store 凭据、执行连接测试、调用外部账户；删除 Shadow Integration 不自动删除外部原始数据。

### Acceptance Criteria

- Secret 不进入普通 Canonical Asset 或标准导出；
- 删除连接后不能继续产生 Run 或 Action；
- Integration identity 与具体 Adapter 实现可分离；
- Source 删除对 State Profile 与 Memory Profile 的影响符合既定策略；
- 更换 Adapter 后配置和 Capability Binding 可迁移。

## UC-017 按需访问外部信息资产

### 目标

Shadow 知道外部资产存在，但只在当前任务、Recall 或整理确有需要且被授权时读取内容。

### Actor

User、Runtime、Memory Intelligence；Asset Catalog；Source Connector；Shadow Policy Authority。

### Trigger

Task、Recall、用户请求或后台 Memory 整理提出 Resource Request。

### Preconditions

- Asset Catalog 有 Stable Reference、Integration Binding 和可用状态；
- Capability Envelope 允许访问；
- 数据等级、Space 和 Model Binding 允许后续处理。

### Main Flow

1. 执行组件提交 Resource Request，说明资产引用、用途和所需范围。
2. Core 校验 Owner / Space、来源权限、数据最小化和目标 Binding。
3. Source Connector 按需读取必要片段。
4. 内容在受限 Execution Context 中交给 Runtime、Model 或 Memory Component。
5. Shadow 记录 access provenance 和最小 Usage。
6. 原始内容默认不复制进 Canonical Store。
7. 形成长期价值时，组件另行提交 Artifact 或 Memory Candidate。

### Failure Flow

- Source unavailable 时返回明确状态并保留引用；
- 权限撤销时拒绝且不尝试其他凭据；
- Model Binding 不允许相应等级时询问用户或选择合规 Target；
- 大范围读取超过预算时请求缩小范围或批准；
- 外部内容变化不自动覆盖已提交 Canonical Memory。

### Durable State Changes

Asset access provenance、Usage summary、Source availability，以及可选 Artifact / Memory Candidate reference；原始内容默认不成为 Canonical Asset。

### External Side Effects

按需读取外部来源的必要片段，可能产生外部 API 用量；不修改来源内容。

### Acceptance Criteria

- Asset Catalog 可以在不复制内容的情况下工作；
- 读取范围符合当前用途；
- 外部内容不会自动成为 Memory；
- Source 不可用不会删除引用或伪造内容；
- Access provenance 可供用户查看。

## UC-018 Semantic Pulse 提议与拒绝

### 目标

可选的小模型或规则 Worker 在预算内提供主动智能，但不参与系统正确性或直接提交状态。

### Actor

Scheduler；Semantic Pulse Worker；Tiny Kernel；User。

### Trigger

配置的周期、Event 或 World State 条件到达。

### Preconditions

- Pulse enabled；
- 独立预算、频率、并发和数据范围有效；
- Primary Store 可用；
- System Health 不依赖 Pulse。

### Main Flow

1. 确定性 Scheduler 创建 bounded Pulse Run。
2. Core 签发无现实副作用的 Capability Envelope。
3. Pulse 读取授权的 Event、World State 和近期活动摘要。
4. Pulse 返回零个或多个 Proposal：
   - Recall；
   - World State Update；
   - ordinary Run；
   - Durable Task；
   - stronger Target。
5. Core 分别执行 Schema、权限、预算、Owner / Space 和数据校验。
6. 符合自动策略的无副作用 ordinary Run 可以执行。
7. 其他 Proposal 被拒绝、排队或发送给用户确认。
8. Core 记录 Usage 和 Proposal decision。

### Failure Flow

- Pulse 超预算、超频或不可用时跳过，不影响 Health、TTL、Task 恢复和 Scheduler；
- Pulse 不能直接提交 Memory、State、Task 或 Action Profile Record；
- stronger Target 超出数据或费用边界时拒绝或询问用户；
- Store 不可用时不创建 Canonical Proposal decision；普通 Pulse 默认暂停；
- 删除 Pulse 组件不需要迁移 Canonical State。

### Durable State Changes

Pulse Schedule、bounded Run / Attempt、Usage、Proposal、Policy Decision 和可选后续 Run / Task Proposal reference。

### External Side Effects

调用小模型、规则 Worker 或只读 Source；Pulse 本身不执行现实 Action。

### Acceptance Criteria

- 关闭 Pulse 后基础系统完全正确；
- Pulse 只通过普通 Dispatch 和 Proposal 路径运行；
- 无副作用自动执行同时受预算限制；
- Durable Task 与现实 Action 不能由 Pulse 直接创建；
- 每个 Proposal 的接受、拒绝和费用可查看。

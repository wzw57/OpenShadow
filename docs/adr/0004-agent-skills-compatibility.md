# ADR-0004: Agent Skills 原生兼容与 Shadow SkillAsset 治理

- Status: Proposed — pending final PR review and merge
- Date: 2026-08-21
- Owners: OpenShadow maintainers

## Context

Skill 是用户长期积累的能力资产。若 Shadow 自创内容格式，用户会被 Shadow 锁定，Runtime Adapter 也必须维护额外转换。

[Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)已经定义以 `SKILL.md` 为核心、可包含 `scripts/`、`references/` 和 `assets/` 的目录结构。不同 Agent 可以发现、加载和投影这些 Bundle。

Provider 也可能提供自己的 Skill Object。例如 [OpenAI Skills API](https://developers.openai.com/api/reference/python/resources/skills/methods/create)支持上传目录或 zip，并维护 Skill ID 与版本。Provider Object 便于执行，但不能成为用户资产的唯一事实源。

## Decision

### 1. 内容格式

Shadow 不定义新的 Skill 内容格式。官方 Skill Profile 原生兼容 Agent Skills Bundle：

~~~text
skill-root/
├─ SKILL.md
├─ scripts/       optional
├─ references/    optional
└─ assets/        optional
~~~

### 2. Canonical SkillAsset

Shadow 保存独立治理 sidecar：

~~~text
skill_id
owner_ref / space_id
format
source_ref
pinned_revision
bundle_digest
trust
permission_policy
data_classification
install_state
runtime_projection_refs
provider_external_refs
~~~

Shadow 不向标准 Bundle 注入私有字段或修改其内容。

### 3. 可移植版本

用户拥有的 Skill 必须满足至少一种：

- 保存 immutable Bundle snapshot；
- 引用可验证且固定的 source revision，并保存 digest。

浮动分支或 Provider default version 不能单独构成长期可恢复版本。

### 4. Runtime Projection

Runtime-specific Prompt、索引、Provider upload、Provider Skill ID 和缓存均为 Derived State / External Reference，可以删除重建。

Adapter 负责：

- 发现标准 Bundle；
- 读取和验证；
- 把内容投影到 Runtime；
- 执行脚本或资源；
- 上传到 Provider；
- 映射 Provider version。

### 5. Trust 与 Permission

Shadow 独立执行 CapabilityEnvelope、数据边界、Approval 和用户策略。

Agent Skills 的 `allowed-tools` 当前是实验性字段，只能作为请求或提示，不能直接授予 Shadow Capability。

高风险权限绑定到具体 bundle digest / pinned revision。内容实质变化后需要重新验证或重新授权。

### 6. Location compatibility

默认优先 Agent Skills 标准位置。Codex、Claude 或其他 Runtime 的专用目录通过 Adapter path mapping 支持，不进入 Canonical Skill identity。

## Rationale

- 用户可以离开 Shadow 继续使用 Skill；
- 不同 Runtime 可以共享同一 Bundle；
- Shadow 只保留其不可外包的治理职责；
- Provider API 可以升级或替换；
- immutable snapshot / digest 保证长期可恢复；
- 独立权限防止内容元数据越权。

## Alternatives considered

### Shadow 自创 Skill Manifest

拒绝。增加生态转换成本并形成 framework lock-in。

### 只保存 Provider Skill ID

拒绝。Provider 删除、版本切换或 API 变化会丢失用户能力资产。

### 修改 SKILL.md 写入 Shadow 元数据

拒绝。破坏标准 Bundle 的原样可移植性，并可能影响其他 Agent。

### 信任 allowed-tools

拒绝。它是 Bundle 声明而非 Shadow 授权，且规范标记为实验性。

## Consequences

正面结果：

- Skill 可跨 Agent / Runtime 迁移；
- Shadow 可以统一管理身份、版本、信任和权限；
- Provider Projection 可重建；
- 不需要维护 Shadow-specific content parser。

代价：

- 需要 Bundle snapshot / digest 管理；
- 需要处理不同 Runtime 的发现位置和加载差异；
- 脚本执行仍需要 Runner / Sandbox；
- 标准可能演进，需要 format version 与 compatibility test。

## Revisit triggers

- Agent Skills 规范出现不兼容大版本；
- 主流 Runtime 不再支持目录 Bundle；
- 用户需要标准无法表达且不能通过 sidecar 治理的能力；
- Provider projection 无法从 Canonical Bundle 重建；
- 安全研究证明当前 Bundle / script trust model 不足。

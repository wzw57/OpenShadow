# Phase 2 设计闸门：Memory 与 Capability Profiles

状态：**Draft / 文档维护阶段**

本文件不启动 Phase 2 业务实现。只有在 Phase 0–1 合并、下列边界得到维护者接受，
并补齐对应 Contract / fixture / migration 方案后，才允许新增 Phase 2 代码。

## 已接受的方向

- Canonical Memory 继续使用通用 Envelope 的版本语义，不建立平行的
  `MemoryVersion` 当前指针。
- Correction 在同一个 Memory ID 上创建新版本，并要求目标版本的
  `expected_version`；跨 Memory merge 创建新 Memory，并显式 supersede 输入 Memory。
- Logical delete 是普通 Canonical 新版本；physical erase 是独立 Erasure 操作，并保留
  不含敏感内容的 Tombstone，防止被旧导出或旧索引复活。
- Memory Maintenance / Recall 是可替换 Adapter；Adapter 只能提交 typed Proposal，
  不能直接写 Canonical Repository。
- SkillAsset 保留标准 Agent Skills bundle 原样；Shadow 治理信息放在 sidecar，绑定
  immutable snapshot / pinned revision 和确定性 digest，不修改 `SKILL.md` 或 bundle。
- Integration 与外部资产默认按需读取；派生索引可删除并从 Canonical 记录重建。

## 必须在实现前明确的边界

1. **Memory 生命周期**：correction、supersede、logical delete、physical erase 的
   Proposal payload、状态转换、并发冲突和 anti-resurrection 测试。
2. **Adapter Contract**：Maintenance / Recall 的输入输出、source dependency、
   unavailable / stale 语义，以及 Proposal 审批和 Commit 的责任边界。
3. **Skill / Integration**：bundle digest、sidecar 版本、外部引用失效、按需读取和
   `allowed-tools` 不得绕过 CapabilityEnvelope 的验证方式。
4. **Portable Import / restore**：manifest 与 record digest 校验顺序、owner / space
   边界、身份映射、版本冲突、幂等键、tombstone 处理和失败后的原子性。
5. **Derived index rebuild**：索引删除、重建输入快照、重建期间的可见性和恢复证据。

## Phase 2 退出条件

- Memory Intelligence / Recall 替换不会丢失 Canonical Memory。
- correction、supersede、logical delete、physical erase 均有版本和恢复测试。
- 旧数据、旧导出和旧索引无法复活已删除或已擦除记录。
- Skill bundle 可被标准 Agent Skills 客户端读取，Shadow sidecar 不污染原 bundle。
- `allowed-tools` 不能授予实际 Capability；外部资产仍按需读取。
- Import / restore 只在完整性、身份边界、冲突和幂等规则被接受后实现。
- 派生索引删除后可从 Canonical records 确定性重建。

在本闸门关闭前，Phase 2–5 继续只维护文档。

# v0.2 R1 状态：ExtensionRegistry 与多 Contract Pack

状态：**Completed / merged into the v0.2 refactor line**
分支：`v02/r1-extension-registry`

R1 已实现 Kernel 内的最小注册边界：

- `ContractPack` 只接受本地目录和签入的 `manifest.json`；schema 文件执行路径边界、
  SHA-256 digest 和 JSON Schema 校验；不提供 URL fetch。
- `ContractRegistry` 继续支持 `ContractRegistry(repository_root)` 的 core pack 兼容构造，
  并新增 `register_pack`、pack provenance 和重复 schema id 处理。
- 相同 schema id 且字节相同的 pack 可以共享；相同 schema id 的不同 digest 返回
  `shadow.contract.schema-conflict`，不会部分注册。
- `ExtensionDescriptor` 和 `ExtensionRegistry` 提供 extension id/version、contract pack
  引用、record/input/target namespace 和 capability descriptor；重复 extension/namespace
  返回结构化冲突。
- `shadow_kernel` 只提供注册原语，不导入 Application、Server 或任何 vendor adapter。

测试：`tests/test_v02_r1_registry.py` 覆盖 core/extension pack、离线校验、digest mismatch、
path traversal、schema conflict、Extension namespace ownership 和缺失 pack。后续 R2–R5
已分别完成执行、generic API 和 Store capability 迁移。

验收证据：R0/R1/Phase 0 相关测试、Contract、Repository 和 peripheral 回归均通过；R6
全量 `pytest -q` 为 `292 passed`，新增 Kernel 代码 Ruff 通过。

## 当前边界

R1 本身不承担 Execution、Proposal/Input、generic records 或 Store capability 实现；这些边界
已在 R2–R5 独立切片完成，R6 的全量回归确认组合后仍保持离线 Contract 与 namespace 约束。

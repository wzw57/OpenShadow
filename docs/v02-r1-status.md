# v0.2 R1 状态：ExtensionRegistry 与多 Contract Pack

状态：**Implemented locally / contract regression passed**
分支：`v02/r0-architecture-tests`

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
path traversal、schema conflict、Extension namespace ownership 和缺失 pack。R0 的 strict
xfail 仍记录尚未进入 R2–R5 的执行、generic API 和 Store capability 迁移。

验收证据：R0/R1/Phase 0 相关测试 `11 passed, 7 xfailed`；Contract、Repository 和
peripheral 回归 `74 passed`；新增 Kernel 代码 Ruff 通过。整套 `pytest -q` 的一次运行
出现既有 `test_deterministic_adapter_enforces_capability_and_replay` 时间窗口 flake，单文件
复跑通过，未修改该无关业务路径。

## 当前边界

R1 不实现 `ExecutionRequest`、Proposal/Input handler dispatch、generic records API、
Conversation extraction 或 Store capability split；这些仍按 v0.2 计划进入后续阶段。

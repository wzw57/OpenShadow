# v0.2 R0 状态：架构测试与 Extension Fixtures

状态：**Scaffolded / migration gates recorded**
分支：`v02/r0-architecture-tests`

R0 已完成“先写验收测试”的部分：

- `tests/v02_fixtures/example_profile_extension.py` 提供无 Application/Server 依赖的最小
  Profile Extension 形状，包含 extension id/version、contract pack、record/input type 和
  semantic input handler；handler 只生成 commit intent，不直接写 Repository。
- `tests/v02_fixtures/example_runtime_extension.py` 提供 typed `ExampleExecutionRequest`
  和 Runtime/target/capability 形状，不导入任何厂商 Adapter。
- `tests/test_v02_r0_architecture.py` 将 Kernel 反向依赖、示例 Extension 形状和下一阶段的
  generic dispatch、typed runtime、generic API、Repository capability split 记录为测试。

## 已知 migration gates

当前 v0.1 仍会使以下测试以 `strict xfail` 记录预期差距；这不是把差距标记为已实现：

- generic Proposal dispatch 仍包含 State/Task/Action 分支；
- ConversationService 仍导入 deterministic 默认 Adapter；
- `RuntimeAdapter.execute` 仍是 `text: str`；
- generic `/v1/extensions`、`/v1/records`、`/v1/inputs` 尚未公开，示例 Profile 的创建/查询
  端到端测试尚未通过；
- Runtime discovery 仍未接入共享 ExtensionRegistry；
- `CanonicalRepository` 的可选能力尚未拆分。

这些 xfail 是 R2–R5 的迁移闸门。进入对应阶段后必须删除 xfail、让断言正常通过，且
不能通过放宽断言来“修复”测试。

## R0 边界

本阶段没有修改 Kernel/Application/Server 业务代码，没有新增数据库表、OpenAPI 路由或
生产 ExtensionRegistry。R0 完成后下一阶段才可实现 R1 的 `ExtensionRegistry` 与多
Contract Pack。

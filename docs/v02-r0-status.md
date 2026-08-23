# v0.2 R0 状态：架构测试与 Extension Fixtures

状态：**Completed / migration gates closed in R6**
分支：`v02/r0-architecture-tests`

R0 已完成“先写验收测试”的部分：

- `tests/v02_fixtures/example_profile_extension.py` 提供无 Application/Server 依赖的最小
  Profile Extension 形状，包含 extension id/version、contract pack、record/input type 和
  semantic input handler；handler 只生成 commit intent，不直接写 Repository。
- `tests/v02_fixtures/example_runtime_extension.py` 提供 typed `ExampleExecutionRequest`
  和 Runtime/target/capability 形状，不导入任何厂商 Adapter。
- `tests/test_v02_r0_architecture.py` 将 Kernel 反向依赖、示例 Extension 形状和下一阶段的
  generic dispatch、typed runtime、generic API、Repository capability split 记录为测试。

## Migration gates

R1–R5 已完成并在 R6 收口：generic proposal/input dispatch、typed Runtime boundary、
generic records/extensions API、共享 ExtensionRegistry 发现和 Store capability split 均由
正常架构测试覆盖，不再以 `strict xfail` 隐藏差距。

## R0 边界

本阶段没有修改 Kernel/Application/Server 业务代码，没有新增数据库表、OpenAPI 路由或
生产 ExtensionRegistry。R0 的 fixtures 仍作为扩展边界回归基线；R1 的 `ExtensionRegistry`
与多 Contract Pack 已由后续切片实现。

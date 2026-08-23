# v0.2 R4 状态：Generic Proposal/Input Handler Registry

状态：**Completed / built-in handlers migrated and generic boundary closed**

已完成：

- 新增 `shadow_application.inputs`：namespaced State/Task/Action/Approval proposal models、
  `ProposalCommand` union 和 `ProposalHandlerRegistry`。
- State、Task、Action/Approval 的 semantic validation 与 Service 调用留在各自 handler；
  generic Server 只负责 auth/context、解析命令并调用 registry。
- `POST /v1/proposals` 已删除 `isinstance`/Profile 分支；accept 流程按持久化
  `proposal_type → handler` dispatch。现有 friendly endpoints 和状态码保持兼容。
- R0 strict architecture gate 已从 xfail 变为正常断言：generic proposal dispatch 不再
  包含 State/Task/Action 类名或分支。
- 示例 input 可以在测试 composition 注册，不需要修改 Server dispatch。

验收证据：R0/R4、Phase 3 State/Completion、Phase 4 Action 定向测试通过；R5 已补齐 generic
records/inputs API、Extension discovery 和 Repository capability split，R6 全量回归为
`292 passed`，Ruff 通过。

## 当前边界

R4 不新增业务数据库表；`/v1/proposals` 的 generic boundary 由 R5 扩展为 `/v1/inputs`、
`/v1/records` 和 `/v1/extensions`，friendly API 仍作为兼容 facade，不复制新的 Server 分支。

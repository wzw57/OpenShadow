# ADR-0025：Runtime Management 与 Codex CLI Adapter

- Status: Accepted
- Scope: Runtime control plane、Hermes launcher、Codex CLI adapter、Project Management UI
- Date: 2026-08-23

## Context

OpenShadow 已能在进程外使用 Deterministic Adapter 或 Hermes Adapter，但目前 Runtime 选择只在
服务启动时通过环境变量完成。用户需要从项目管理页面看到 Runtime 状态、直接启动 Hermes、
切换到 Codex，并继续通过 Shadow 的 Conversation/Admission 路径调用 Agent。

## Decision

1. Runtime Manager 属于部署控制平面，不改变 `RuntimeAdapter`、Admission、CommitAuthority
   和 Canonical write boundary。
2. Runtime profiles 使用受 schema 校验的本地配置；进程 PID、health 和启动日志是 ephemeral
   supervisor state，不冒充用户 Canonical record。
3. Hermes 和 Codex 分别拥有独立 Adapter/launcher。Core、Application、Web UI 只依赖通用
   descriptor、lifecycle、health 和 normalized result。
4. Codex 采用官方 CLI 的子进程边界和 `codex exec --json` JSONL 协议；不导入 Codex 私有
   内部对象、不复制其 Agent Loop、不开放 bypass sandbox/approval 的默认参数。
5. Runtime 管理 API 只能启动、停止、重启、健康检查和选择 Runtime；所有真实工作仍由
   Conversation/Admission/Run/Attempt 执行，禁止管理 API 直接执行用户 prompt。
6. Web UI 只渲染通用 Runtime Management 数据，不按 Vendor 分支；显示的厂商名称来自服务端
   descriptor/profile metadata。
7. 本地 Windows 启动由 `scripts/start-shadow-management.ps1` 负责依赖检查、Web UI 构建、
   Shadow 启动和可选 Runtime auto-start；它不保存凭据、不下载外部 Runtime。

## Consequences

- 可以从同一管理界面启动/检查 Hermes，并在不改 Core/UI 的情况下切换 Codex 或其他 Adapter；
- Codex CLI 版本、JSONL event schema 和跨平台进程行为需要 Adapter contract tests 与版本 pin；
- 进程控制面仍是本机单用户能力，生产级认证、远程多主机和容器编排必须另立 ADR；
- 切换不能回溯已有 Run/Attempt，切换冲突必须显式返回，避免运行中的请求漂移到新 Runtime；
- Hermes Tool bridge、SSE/session resume 和 durable dispatch 不会因本 ADR 自动获得实现。

## Revisit conditions

当需要多主机 Runtime、租户级 process isolation、真实审批、远程 secret manager、工具副作用
或可恢复的 external session 时，分别建立新的安全/可靠性闸门，不扩大本 ADR 的启动 API。

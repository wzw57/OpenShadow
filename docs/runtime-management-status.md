# Runtime Management 实现状态

状态：**已实现 / 本地控制切片完成**

## 已实现

- Runtime profile JSON 与 schema 校验边界；
- `RuntimeSupervisor` 的 start / stop / restart / select / health / probe；
- 启动状态、健康状态、PID、错误和幂等重放的非敏感投影；
- 通用 Runtime Management API；
- Hermes profile 入口（进程命令由本地部署配置提供）；
- Codex CLI Adapter，通过 `codex exec --json` JSONL 进程边界调用；
- 项目管理 Web UI 页面；
- Windows `scripts/start-shadow-management.ps1` 启动脚本。

## 使用边界

默认 profile 启用 Deterministic Runtime 与 Codex CLI profile；Hermes profile 默认禁用，需在
`config/runtime-profiles.json` 中显式启用并配置本机 executable、workspace、health 和外部
Provider 环境。Codex 仍需本机安装 CLI 与配置 Provider，密钥不写入 profile。

启动管理界面：

```powershell
.\scripts\start-shadow-management.ps1 -Build -OpenBrowser
```

如果本机已安装 Codex CLI，可以在启动时选择它：

```powershell
.\scripts\start-shadow-management.ps1 -RuntimeId codex -AutoStartRuntime -OpenBrowser
```

Hermes 的 `launch.command` 必须按实际安装方式填写在 profile 中；不把未知的 Hermes 启动
命令硬编码进 Shadow。

Runtime 切换只改变后续 Conversation 的 Adapter binding；正在执行的 Run 会阻止切换。
Runtime Management API 不提供任意 prompt 执行入口，真实工作仍经过 Conversation、Admission、
Run/Attempt 和现有 Commit 路径。

## 尚未实现

- Hermes Tool/Capability bridge；
- Hermes SSE / Session resume；
- 远程多主机 Supervisor、容器编排和生产认证；
- Codex 内部 session/state 与 Shadow Canonical State 的自动同步。

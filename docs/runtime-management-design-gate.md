# Runtime Management 设计闸门

状态：**Accepted / 已获准实现**
范围：Runtime 组件目录、受控启动/停止、运行时切换、项目管理 Web UI 与本地启动脚本

## 1. 目标与边界

当前 Shadow 已有通用 `RuntimeAdapter`、Deterministic Adapter 和 Hermes HTTP Adapter，但
服务启动时只能通过环境变量选择一个 Adapter，不能在项目管理界面查看、启动、停止、健康检查
或切换 Runtime。本切片补齐本地单机控制面，不改变 Kernel 的 `RuntimeAdapter` Port、Admission、
CommitAuthority 或 Canonical record 语义。

Runtime Management 是部署/控制平面，不是新的 Agent Loop，不是通用 Queue，也不是业务
Profile Service。所有 work-bearing 输入仍必须经过现有 Conversation、Admission、Run/Attempt
和 Commit 路径。

## 2. 冻结的组件边界

```text
Project Management UI
        │ generic management HTTP API
        ▼
Runtime Supervisor / Catalog          ← local process boundary
        │                         │
        │ starts/checks/stops     │ creates adapter
        ▼                         ▼
 Hermes process ── Hermes Adapter   Codex CLI ── Codex Adapter
        │                         │
        └────────── RuntimeAdapter Port ──────────┘
                              │
                       ConversationService
```

- Core、Application 和 Web UI 只理解通用 runtime id、descriptor、health、lifecycle 和
  opaque external reference；不得判断 Hermes 或 Codex 的私有类型。
- Hermes 私有代码、Codex Rust/Python 内部对象和 Provider SDK 只能存在于各自 Adapter 或
  Supervisor launcher 中。
- Supervisor 可以管理本机受信任进程，但不得让浏览器提交任意 executable、shell 字符串、
  环境变量或工作目录。
- Runtime 进程状态是部署状态，不作为 Canonical 用户资产保存；仅保存非敏感的 profile 配置
  与受控状态快照。Provider key、session token 和 secret 原文只从进程环境/外部 secret
  reference 读取，不写入 UI、日志、Canonical record 或 localStorage。

## 3. Runtime Profile Contract

每个本地 Runtime Profile 使用受 schema 校验的配置（`.shadow/runtime-profiles.json`），最小字段：

| 字段 | 约束 |
| --- | --- |
| `runtime_id` | 稳定、namespaced、不可含路径分隔符 |
| `display_name` | 仅显示文本，不参与执行逻辑 |
| `adapter_factory` | 已安装 Python module factory，来自服务端 allowlist |
| `target_kind` | `shadow.agent-runtime` 或其他已注册 target kind |
| `launch.command` | 参数数组，不接受 shell 字符串；仅允许配置中的 executable |
| `launch.cwd` | 预注册 workspace 下的绝对路径 |
| `launch.env_refs` | 仅 secret/config reference 名称，不保存值 |
| `health.url` | 可选的 loopback/allowlisted URL |
| `auto_start` | 默认 false；显式配置才自动启动 |
| `enabled` | 默认 false；禁用 profile 不能被选择 |

Profile 不允许 `shell=true`、任意脚本片段、inline secret、`--dangerously-bypass-approvals-`
`and-sandbox`、未声明的工作目录或任意远程 callback URL。

## 4. Hermes Adapter 与 Supervisor

- Hermes 继续作为外部 Agent Runtime；Shadow 只通过 `shadow.agent-runtime` Adapter 调用。
- Supervisor 启动 Hermes 的命令、cwd、端口和下游 Provider 配置来自经过校验的 profile；
  不把 Hermes Python package 导入 Shadow Core。
- 健康检查使用 profile 声明的 endpoint 或 Adapter `health()`；启动成功不等于 Runtime
  可用，必须经过 health transition 才能被选择。
- Hermes tools 默认关闭。Tool/Capability bridge、SSE 细粒度事件和 session resume 仍由
  独立闸门负责。

## 5. Codex Runtime Adapter

本项目接入官方开源 `openai/codex` CLI 的**进程边界**，不复制 Codex 源码、不链接 Codex
Rust crate、不把 Codex 内部 session/state 当成 Shadow state。

- Adapter executable 由 profile 指向已安装、固定版本的 `codex`；服务端只接收 allowlist
  中的 executable identity。
- 调用形态固定为非交互 `codex exec --json`，逐行解析 JSONL，只抽取通用 normalized
  progress/result/error；stdout 之外的诊断进入隔离日志。
- 默认使用 Codex 自身的 sandbox/approval 约束；Shadow 不自动打开绕过审批或沙箱的参数。
- workspace、model/provider、network 和 approval policy 由 profile 明确声明；不从用户消息
  拼接 CLI 参数。
- Codex thread/session id 只作为 opaque `execution_ref` / resume reference；不得直接写入
  Shadow Memory、State 或 Action。
- Codex Adapter 不提供任意 shell endpoint。用户通过 Shadow Conversation/Admission 发起
  work-bearing 请求，管理 API 只负责启动、选择和健康检查。

## 6. Supervisor API Contract

首片只增加通用管理 API，不新增 Vendor 专用路由：

- `GET /v1/management/overview`：API、Store、Web UI、active runtime 摘要；
- `GET /v1/runtime/instances`：profile、descriptor、lifecycle、health、pid/external ref
  摘要，不返回 secrets；
- `POST /v1/runtime/instances/{runtime_id}/start`：幂等启动；
- `POST /v1/runtime/instances/{runtime_id}/stop`：受控停止；
- `POST /v1/runtime/instances/{runtime_id}/restart`：停止后启动；
- `POST /v1/runtime/instances/{runtime_id}/select`：将已 healthy 的 Runtime 设为新的
  active binding；存在 executing Run/Attempt 时拒绝切换；
- `GET /v1/runtime/instances/{runtime_id}/health`：刷新单个 Runtime health；
- `POST /v1/runtime/instances/{runtime_id}/probe`：仅执行无副作用 capability/health probe，
  不接受任意用户 prompt。

所有 mutation 要求 `Idempotency-Key`，统一返回结构化错误：`not-found`、`disabled`、
`invalid-profile`、`already-running`、`not-running`、`health-unavailable`、`selection-conflict`、
`process-start-failed`、`store-unavailable`。API 不直接让浏览器传 executable 或 secret。

## 7. 项目管理 Web UI

在现有 vendor-neutral Web UI 中增加 Project Management 页面/入口，页面只消费上述通用 API：

- Project readiness：API、Store、Web UI、active Runtime；
- Runtime cards：display name、target kind、adapter family、enabled、lifecycle、health、
  version 和最近错误；
- 操作：Start、Stop、Restart、Select、Health check；切换前显示当前 executing 状态；
- 配置：显示 profile 来源、workspace basename、secret reference 名称；永不显示 secret 值、
  原始环境变量或完整命令中的 token；
- UI 不出现 Hermes/Codex 专用分支；厂商名称只作为服务端 descriptor/display_name 数据。

## 8. 启动管理脚本

新增 `scripts/start-shadow-management.ps1`，负责本地开发启动：

1. 检查 Python、Node/npm、依赖和已构建 Web UI；
2. 可选执行 `npm install` / `npm run build`；
3. 校验 runtime profile，不打印 secret；
4. 启动 Shadow FastAPI；
5. 可选等待 `/readyz` 后打开 `/ui/management`；
6. `-RuntimeId` / `-AutoStartRuntime` 只选择 profile 中已启用的 Runtime；
7. Ctrl+C 时按登记顺序停止由脚本启动的子进程。

脚本不负责安装 Hermes/Codex、不下载二进制、不保存 API key。安装和凭据配置属于部署文档。

## 9. 原子性、切换与故障语义

- Start/stop/restart 是 Supervisor 状态机：`stopped → starting → healthy|failed`，
  `healthy → stopping → stopped|unknown`；异常退出进入 `failed`，不能伪造 healthy。
- active selection 只对已 healthy 的 descriptor 生效；新请求使用新 binding，已有 Run/Attempt
  保留原 runtime binding；存在不允许切换的 executing 任务时返回 `selection-conflict`。
- Runtime 调用失败仍由 Conversation/Run/Attempt 记录；Supervisor 不直接提交 Message、
  Action、Task 或 Memory。
- Store unavailable 时，管理 API 不声称 Canonical selection 已提交；进程状态可以报告为
  ephemeral unknown，并要求下一次 health/reconcile。
- 相同 idempotency key 重放返回稳定结果，不重复启动进程、不重复 stop side effect。

## 10. 实现顺序与闸门

1. 维护者接受本设计闸门与 ADR；
2. 先实现 profile schema、fixture、Supervisor 状态机和 deterministic fake process adapter；
3. 再实现通用 management API 和 runtime selection；
4. 增加 Hermes process launcher；
5. 增加 Codex CLI Adapter（固定 JSONL parser、sandbox/approval 默认值）；
6. 增加 Project Management UI 与启动脚本；
7. 完成本地进程、restart、health、切换、故障、幂等、权限和浏览器验收；
8. 合并后再单独建立 Runtime Reliability / Tool Bridge / Session resume 闸门。

## 11. 明确不在本切片

- 不把 Hermes 或 Codex 耦合进 Core、Application 或 UI；
- 不实现 Shadow 自己的 Agent Loop；
- 不开放任意 shell、任意 prompt-to-command、远程进程管理或浏览器命令执行；
- 不实现 Hermes Tool/Capability bridge、SSE token streaming、session resume；
- 不实现生产 OAuth/OIDC、远程 multi-host Supervisor、容器/Kubernetes 编排；
- 不把 Provider secrets、Codex thread 内容或 Hermes 私有 Memory 写入 Canonical Store。

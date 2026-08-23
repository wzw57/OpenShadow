# Runtime 集成状态

更新时间：2026-08-23

## 当前事实

| Runtime 能力 | 状态 |
| --- | --- |
| `RuntimeAdapter` 最小 Port | 已实现 |
| Deterministic Test Adapter | 已实现，仅 Echo/无副作用 |
| Hermes Agent Adapter | 已实现（HTTP / OpenAI-compatible） |
| OpenAI Model Adapter | 尚未实现 |
| DeepSeek V4 Flash（通过 Hermes） | 已完成在线 smoke / Shadow E2E 联调 |
| Ollama/vLLM/llama.cpp 直连 Shadow | 尚未实现，也不作为本切片目标 |
| Shadow 内部 Agent Loop | 明确不实现 |
| Hermes Tool/Capability 映射 | 尚未实现；联调配置全部关闭工具 |
| 单用户 Web UI Conversation Client | 已实现；通过 `/ui/` 使用 Shadow API |
| Runtime Supervisor / Management UI | 已实现；本地 profile、受控 lifecycle 和切换 |
| Codex CLI Runtime Adapter | 已实现；`codex exec --json` 进程边界，profile 默认启用但需本机 CLI/Provider |

## 当前边界

默认配置的 active runtime 是 Deterministic Adapter；Codex CLI profile 已启用但不会自动
启动，Hermes profile 默认关闭。部署可通过 `config/runtime-profiles.json`（或
`SHADOW_RUNTIME_PROFILE_PATH`）管理多个本地 Runtime，亦可继续使用
`SHADOW_RUNTIME_ADAPTER_FACTORY=<module>:<factory>` 注入单个通用 Adapter。Runtime
Supervisor 只依赖通用 `shadow.agent-runtime` Port，不把 Hermes/Codex 私有对象或 Provider
凭据写入 Canonical Repository。

Runtime Management 现在也可从 `config/runtime-profiles.json` 读取多个本地 Adapter profile，
通过 `/v1/runtime/instances/*` 受控启动、健康检查和选择。管理控制面不会执行任意 prompt；
后续工作仍经过 Conversation/Admission。Codex profile 只调用已安装的 `codex` CLI，解析
`codex exec --json` JSONL，不导入 Codex 内部对象。

如需复现 Hermes + DeepSeek 联调，必须显式启用 Hermes profile、填写本机 Hermes 的
`launch.command`/health 配置，并在 Hermes 进程侧配置 `deepseek-v4-flash`；这是一条可选
的 Adapter 部署路径，不是 Shadow 对 DeepSeek 的直连。

已完成的真实联调：

- Hermes API Server `0.20.5` health；
- DeepSeek V4 Flash 文本回复；
- Shadow Adapter 文本/usage/execution reference；
- FastAPI Conversation → Hermes Adapter → Hermes → DeepSeek → Run/Message Commit；
- Hermes API Server 联调 profile 的工具全部关闭。

当前 Adapter 使用非流式 Chat Completions 并生成本地完成事件；Hermes 原生 SSE
细粒度 token/tool event 映射、Session resume 和 Tool/Capability bridge 仍需单独
实现和验收。另需将 Provider 调用前的 Attempt 持久化从现有同步 Conversation
路径中拆出，才能满足 crash-safe durable dispatch。

Hermes 设计闸门见 [runtime-hermes-design-gate.md](runtime-hermes-design-gate.md)，
ADR 见 [ADR-0021](adr/0021-hermes-agent-runtime-adapter.md)。

## 下一步

1. 补充 Hermes SSE / Run Events 和 Session resume 映射；
2. 另立 Tool/Capability 设计闸门；
3. 让 Shadow Action / Outbox 接管获准的副作用；
4. Web UI 已提供 Runtime 状态和有限 Run event 展示；待 Runtime SSE/session 契约
   稳定后再扩展 token 级流式展示。

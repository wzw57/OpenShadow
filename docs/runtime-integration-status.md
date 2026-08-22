# Runtime 集成状态

更新时间：2026-08-22

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

## 当前边界

现有 ConversationService 默认仍使用 Deterministic Test Adapter。设置
`SHADOW_RUNTIME_KIND=hermes` 后，它可以通过独立 Hermes Adapter 调用 Hermes
API Server；Hermes 再通过 DeepSeek OpenAI-compatible API 使用
`deepseek-v4-flash`。Shadow 不直接调用 DeepSeek，也不把 Hermes 私有 Session
或 Memory 写入 Canonical Repository。

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

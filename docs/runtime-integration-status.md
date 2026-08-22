# Runtime 集成状态

更新时间：2026-08-22

## 当前事实

| Runtime 能力 | 状态 |
| --- | --- |
| `RuntimeAdapter` 最小 Port | 已实现 |
| Deterministic Test Adapter | 已实现，仅 Echo/无副作用 |
| Hermes Agent Adapter | 尚未实现 |
| OpenAI Model Adapter | 尚未实现 |
| Ollama/vLLM/llama.cpp 连接 | 尚未实现 |
| Shadow 内部 Agent Loop | 明确不实现 |
| Hermes Tool/Capability 映射 | 尚未实现 |

## 当前边界

现有 ConversationService 默认使用 Deterministic Test Adapter。它用于验证
Admission、Run、Attempt、Commit、Retry、SSE、幂等和故障语义，不代表已经拥有
真实模型或 Agent 能力。

Hermes 设计闸门见 [runtime-hermes-design-gate.md](runtime-hermes-design-gate.md)，
ADR 见 [ADR-0021](adr/0021-hermes-agent-runtime-adapter.md)。设计接受前不得创建
Hermes 业务 Adapter 或安装依赖来伪造联调完成。

## 下一步

1. 接受 Hermes Runtime 设计闸门；
2. 创建 `runtime/hermes-implementation` 分支；
3. 实现文本 session、事件、结果和失败映射；
4. 连接本地 Hermes API Server；
5. 在工具关闭条件下完成真实联调；
6. 另立 Tool/Capability 设计闸门。

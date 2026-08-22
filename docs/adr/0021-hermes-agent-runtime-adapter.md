# ADR-0021：Hermes Agent Runtime Adapter

- Status: Proposed
- Date: 2026-08-22
- Deciders: OpenShadow maintainers
- Related: ADR-0002、ADR-0003、ADR-0015

## Context

OpenShadow 已有 `RuntimeAdapter` 最小 Port 和无副作用的
`DeterministicTestAdapter`，但尚未接入真实 Agent Runtime。需要把 Agent Loop
放在可替换的外部 Runtime，而不是在 Shadow Application 或 Kernel 中重新实现。

Hermes Agent 是本切片的候选 Agent Runtime。Ollama、vLLM、llama.cpp 和云端
OpenAI-compatible 服务属于 Hermes 下游的模型提供者，不属于本 ADR 的 Runtime
实现。

## Decision

建立独立的 Hermes Adapter，注册 `shadow.agent-runtime`。Adapter 通过 Hermes
API Server 与外部 Runtime 通信，负责 Shadow request/event/result 与 Hermes
session/event 的边界映射。

Shadow 继续拥有：

- Admission；
- Run / Attempt；
- Capability、data scope、budget、approval、expiry 和 revocation 最终检查；
- Action / Outbox 的副作用提交；
- Canonical Memory、State、Task 和治理记录。

Hermes 继续拥有：

- Planner；
- Agent Loop；
- Session 内部状态；
- Tool selection 的内部建议；
- Model Provider 调用。

第一实现只做文本 session、事件、最终结果、usage、失败和未知状态映射。工具
执行必须保持关闭，或在后续独立闸门中通过 Shadow Capability/Action 边界接入。

## Rejected alternatives

1. **直接把 Ollama 接成 Agent Runtime**：拒绝。Ollama 是模型推理服务，不拥有
   Shadow 所需的 Agent Loop、工具治理和 Session 语义。
2. **在 Shadow 内实现 Planner/Tool Loop**：拒绝。会使 Kernel/Application 绑定
   快速变化的 Agent 实现，并违反可替换 Runtime 边界。
3. **导入 Hermes 私有 Python 对象并直接写 Store**：拒绝。会绕过 Commit、CAS、
   Admission 和长期记录治理。
4. **第一版开放 Hermes 任意工具**：拒绝。工具副作用必须先经过 Shadow
   Capability 和 Action/Outbox 边界。

## Consequences

- Shadow 可以更换 Hermes、其他 Agent Runtime 或纯 Model Worker，而不改变
  Canonical ID 和 Run 语义；
- 第一版需要记录外部 Session reference 和事件 cursor；
- 完整 Tool/Capability、Checkpoint 和 native resume 需要后续独立设计；
- 本 ADR 不新增表，不改变现有迁移，不提供多用户身份能力。

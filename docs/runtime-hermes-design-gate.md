# Hermes Agent Runtime 设计闸门

状态：**Accepted（文本调用切片）；持久化 dispatch、SSE、Session resume 与 Tool bridge 待后续闸门**

本闸门把 Hermes Agent 作为外部 Agent Runtime 候选接入 Shadow。它不改变
Kernel、Canonical Profile 或 Phase 0–4 的既有语义，也不把模型服务误认为
Agent Runtime。

## 1. 分层决定

本切片冻结以下分层：

```text
Shadow
  └─ shadow.agent-runtime Adapter
       └─ Hermes Agent Runtime
            └─ Model Provider（Ollama / vLLM / 云端兼容服务等）
```

- Hermes 负责自己的 Planner、Session、Tool Loop、Skill Projection 和内部
  Runtime 状态；Shadow 不重新实现这些组件。
- Ollama、vLLM、llama.cpp 和云端模型只是 Hermes 的 Model Provider 候选，
  不是 Shadow 的 Agent Runtime。
- 本仓库当前只有 `DeterministicTestAdapter`；本闸门接受前不声称已接入
  Hermes 或任何真实模型。

## 2. Adapter 身份与传输

- Adapter family：`shadow.execution`；
- target kind：`shadow.agent-runtime`；
- implementation ref：`openshadow://adapters/hermes-agent`；
- 外部 Runtime：Hermes Agent；
- 首选传输：Hermes API Server 的 HTTP/JSON 与事件流；
- 不把 Hermes Python 源码或内部 Session 对象导入 Kernel；
- Hermes Session ID 只能作为 `external_ref` 或 Runtime Checkpoint Reference，
  不能替代 Shadow Run ID、Attempt ID 或 Durable Task ID。

Adapter 必须负责：

1. 将 Shadow 的 work-bearing input 映射为 Hermes session/input；
2. 将 Hermes event 映射为 Shadow progress、usage、failure 或 result；
3. 保存并回传 correlation、external_ref 和最后事件 cursor；
4. 对 timeout、连接中断、未知结果和版本不兼容返回结构化错误；
5. 诚实声明 Hermes 实际支持的 capability。

Adapter 不得负责：

- 直接写 Canonical Repository；
- 直接提交 Memory、State、Task 或 Action；
- 绕过 Admission、Capability、Approval、Budget 或副作用检查；
- 把 Hermes 私有 Memory 当作 Shadow Canonical Memory；
- 把模型输出当作已提交的现实副作用。

## 3. 第一实现切片边界

第一切片只验证真实 Agent Runtime 的连接闭环：

- 创建 Hermes session；
- 发送一条文本输入；
- 接收 Hermes 的事件和最终文本结果；
- 记录 Shadow `Run / Attempt / Result / Usage`；
- 支持 Shadow 重启后依据 external session reference 查询或标记未知；
- Hermes 不执行未经过 Shadow 映射的工具。

第一切片暂不开放：

- 任意 shell、文件系统、浏览器或网络工具；
- Hermes 内部工具直接修改 Shadow 数据；
- 自动 Action 执行；
- Shadow Memory 与 Hermes 私有 Memory 的双向自动同步；
- 多 Agent、远程设备、语音和多用户 ACL。

后续 Tool/Capability 切片必须另立闸门：Hermes 只能提出 Tool Request，Shadow
依据 CapabilityEnvelope、data scope、side-effect、approval、budget 和 expiry
做最终检查，允许的副作用统一进入 Action/Outbox 边界。

## 4. Shadow 侧生命周期

```text
Web/API input
    │
    ▼
Admission
    │
    ▼
Commit Admission + Request + Run + Attempt（目标边界）
    │
    ▼
Hermes Adapter ──> Hermes Session / Agent Loop
    │                        │
    │                        └─ event / result / unknown
    ▼
Commit Result / Failure / Reconciliation
    │
    ▼
SSE events + Canonical records
```

完整 durable dispatch 要求 Provider 调用前已经持久化可恢复的 Shadow Attempt。
当前文本切片复用了 Phase 1 的同步 ConversationService，仍在同一请求内先取得
结果再提交 Canonical records；因此该要求标为后续可靠性切片，不把当前实现描述为
已完成的 crash-safe dispatch。未知结果不得盲目重试，只能依靠 Hermes 查询结果
或明确证据进行 reconciliation。

## 5. 错误与能力语义

至少映射以下错误：

- `runtime.unavailable`：Hermes API 不可达；
- `runtime.timeout`：请求超时；
- `runtime.protocol-incompatible`：响应不符合 Adapter Contract；
- `runtime.session-unknown`：外部 Session 状态无法确认；
- `runtime.capability-denied`：工具或能力未通过 Shadow 检查；
- `runtime.provider-error`：Hermes 下游 Model Provider 错误。

Adapter 只声明真实支持的能力。没有可靠取消确认时，不得声称 Run 已取消；
没有 native resume 时，只能创建新的 Attempt 或进入 reconciliation。

## 6. 设计接受标准

- [x] 明确 Hermes 版本、API Server 启动方式和本地配置；
- [x] `shadow.agent-runtime` Adapter 不依赖特定 Model Provider；
- [x] Hermes Session ID 与 Shadow Run/Attempt ID 分离；
- [ ] provider 调用前 Shadow Run/Attempt 已持久化；
- [x] 文本输入、完成事件、最终结果和 usage 可 round-trip；
- [x] Hermes 不可直接写 Shadow Repository；
- [x] Hermes 工具默认关闭或全部经过 Shadow Capability；
- [x] unavailable、timeout、protocol mismatch 有结构化错误；
- [x] 相同 idempotency key replay 不创建新的 Run/Attempt；
- [ ] 重启后可恢复或诚实标记外部 Session 状态（Session resume 待后续切片）；
- [x] 不新增数据库表、不改变 Phase 0–4 Canonical 语义。

设计接受后，才建立 `runtime/hermes-implementation` 分支并写业务代码。

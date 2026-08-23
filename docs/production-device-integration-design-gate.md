# Production Voice / Device / Integration 设计闸门

状态：**Accepted / 允许创建实现分支**  
分支：`production/device-integration-design-gate` → `production/device-integration-implementation`

本切片只实现 Vendor-neutral Adapter Port、确定性 Contract Adapter 和 capability/consent
边界。Voice、设备控制、消息发送等现实副作用不进入 Kernel，也不由 Web UI 直接调用。

## 固定决策

- Adapter 只能读取已验证的 `AuthContext`/Secret reference，返回 Observation/Result；不能
  直接 Commit、创建 Task/Action 或绕过 Admission。
- 每次副作用请求必须携带 `principal_ref`、`space_id`、`endpoint_ref`、
  `capability_ref`、`data_classification`、`consent_ref`、`expires_at` 和 idempotency key。
- 缺少 capability、consent 过期/revoked、scope 不匹配、inline Secret、provider unknown
  和 Store unavailable 都返回结构化错误；unknown 只能由 provider query/evidence reconcile
  收敛，不得盲目重试。
- Voice 输入默认 transient；除非用户明确 consent，不写入 Canonical。STT/TTS 结果只保存
  非敏感 digest/opaque external ref；原始音频和 Provider 私有 payload 不进入 Store。
- Device/Integration secret 只接受 `secret_ref`；OAuth/webhook/token rotation 由具体
  Adapter 负责。未验证的 webhook 不得产生 Shadow 写入。
- 首片不新增公开 Voice/Device 路由、不实现真实硬件、麦克风、OAuth provider 或后台 worker。

## 失败与重放

| 情形 | 结果 |
| --- | --- |
| valid capability + consent | Adapter 返回确定性 Result/Observation |
| expiry/revocation/scope mismatch | `403` structured deny；不调用 Provider |
| provider rejected | `failed`，保留 reason/external ref |
| provider timeout/ambiguous | `unknown`，保存 opaque ref；禁止自动 retry |
| same idempotency key + same digest | replay，不产生第二次副作用 |
| same key + different digest | conflict/idempotency-mismatch |

## 退出条件

- Generic Voice/Device/Integration Port 与 deterministic adapters 有 valid/invalid fixtures；
- consent、capability、expiry、revocation、scope、Secret redaction 和 unknown/reconcile 测试通过；
- 没有 Vendor 名称进入 Kernel/Application/OpenAPI/Web UI；
- 文档、状态、ADR 和 documentation-sync 保持一致。

实现状态：通用 Contract、确定性 Adapter 和边界测试已完成；真实硬件、语音 Provider、
OAuth/webhook 与设备副作用仍保持 Contract-only。

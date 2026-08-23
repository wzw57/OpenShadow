# Production Readiness 总体设计闸门

状态：**Accepted for Slices A–E / 本地发布基线已合并**
范围：生产化路线、认证与安全、Runtime 可靠性、远程 Store、备份同步、设备/语音、可观测性与发布

本闸门把“可运行参考项目”推进到“可发布产品”的工作拆成有依赖的切片。它不把尚未
验证的外部 Provider、认证平台或部署环境写进 Kernel，也不允许通过临时路由、临时表或
Vendor 分支绕过现有 Admission、CommitAuthority、CAS 和 Canonical 生命周期。

## 1. 现状与目标

当前已经具备：

- 单机单用户 FastAPI + SQLite + React/Vite Web UI；
- Phase 0–4 与 Phase 5 Core Slice 的当前授权实现；
- Deterministic、Codex CLI 和 Hermes Adapter；
- Runtime Supervisor、项目管理 UI、OpenAPI、Schema、fixtures 和本地验收基线。

目标是形成可发布的生产 profile，而不是把所有未来能力一次塞进一个服务：

```text
[已实现参考基线]
        │ merge / freeze / release manifest
        ▼
[Slice A 认证与安全]
        │ verified AuthContext、Secret boundary、audit、rate limit
        ▼
[Slice B Runtime 可靠性]
        │ durable dispatch、SSE/resume、unknown reconciliation
        ▼
[Slice C Store / Backup / Sync]
        │ remote repository、restore drill、conflict/anti-resurrection
        ▼
[Slice D Voice / Device / Integration]
        │ Adapter-only、capability、consent、failure semantics
        ▼
[Slice E Operations / Release]
        │ observability、deployment、load/chaos/security、release candidate
```

每个切片都必须单独拥有设计稿、ADR、Schema/fixtures（如有）、实现、测试、运行证据和
状态文档。PR #25 已将 A–E 的本地参考实现合并到 `main`；真实外部部署验收仍按各状态文档
列出的前置条件执行。

## 2. 不变量

1. 任何 work-bearing 输入仍经过 Admission；健康、静态资源和只读管理查询不创建 Root Run。
2. 所有长期写入仍经过 CommitAuthority/CAS；外部 Runtime、Provider、Resolver、Router 和
   Voice/Device Adapter 只能返回 Result、Observation 或 Proposal。
3. 生产身份来自经过验证的 `AuthContext`，不能信任浏览器直接提交的
   `X-Principal-Ref`/`X-Space-Id`；local-dev bootstrap 必须显式开启。
4. Secret 只以 opaque reference 进入 Canonical/Profile；原文不得进入数据库、日志、事件、
   Export、错误体或 Web UI。
5. Store 不可用、Provider unknown、备份未验证或恢复未完成时，系统不得声称成功。
6. Vendor 名称和私有协议只能存在于 `adapters/<vendor>`、对应测试和部署值；Core、Application、
   OpenAPI、Schema、Web UI 只依赖通用 Port。
7. 默认策略是 deny、least privilege、explicit consent；任何高风险现实副作用必须有
   capability、scope、approval、expiry、revocation 和 audit 证据。

## 3. 切片顺序与边界

### Slice A：Production Auth & Security

- Auth Adapter 将 OIDC/OAuth 或其他受信 issuer 的验证结果映射成通用 `AuthContext`；Kernel
  不导入具体 issuer SDK。
- 浏览器推荐 HttpOnly/Secure/SameSite session；API 客户端可用 bearer token；cookie 写操作
  必须有 CSRF 防护。
- Session 只保存 opaque subject、issuer、expiry、endpoint 和审计引用，不保存 ID token 原文。
- `principal_ref`、`endpoint_ref`、`space_id` 由服务端验证后的 context 派生；请求 Header 只
  作为 local-dev 兼容入口，生产模式拒绝未验证 Header。
- SecretResolver 是只读 Adapter Port；Secret material 不进入 Canonical Repository、Export、
  error body、日志或 profile JSON。
- 增加认证失败、授权拒绝、session revoke、Secret access 和管理操作的审计事件；不记录
  prompt、token、Cookie 或 Provider 私有 payload。
- 本 Slice 不实现 Voice、远程 Store、真实 Provider Tool Bridge 或密码找回 UI。

已实现的通用边界：

```text
GET  /v1/auth/session       → 当前已验证 AuthContext 的非敏感摘要
POST /v1/auth/logout        → session revoke / idempotent audit
POST /v1/auth/exchange      → Adapter 验证外部 credential，不返回 Secret 原文
```

### Slice B：Runtime / Provider Reliability

- Provider 调用前先持久化 Attempt/Outbox intent；crash recovery 不重复现实副作用。
- Hermes SSE、Codex execution reference、cursor、resume 和 normalized event 只通过 Adapter；
  不把私有 Session/Thread 当成 Shadow State。
- `unknown` 只能由 Provider query 或 evidence-backed reconciliation 收敛，禁止盲目 retry。
- Tool/Capability 请求重新进入 Action/Outbox/Admission；Runtime 不能直接写 Store。

### Slice C：Remote Store / Backup / Sync

- Canonical Repository Port 保持不变；推荐生产 profile 使用 PostgreSQL Adapter，SQLite 保留
  local-dev/reference profile。
- Portable Export、Tombstone、digest、identity mapping、all-or-nothing restore 和冲突语义
  必须先验证，再写入目标 Store。
- 备份必须有 encryption metadata、restore drill、integrity digest、retention 和 erase
  propagation 证据；不备份 Secret 原文、Provider 私有状态或可重建索引。
- 跨设备同步只同步 Canonical/portable records，不把事件总线或通用 Queue 引入 Core。

### Slice D：Voice / Device / Integration

- Voice、wake word、STT/TTS、设备协议和外部 Integration 全部通过 Adapter/Capability；不进入
  Kernel Profile 类型分支。
- 麦克风、设备控制、消息发送等现实副作用必须有 consent、data classification、scope、
  expiry、revocation、audit 和 unknown/reconciliation 语义。
- Integration Secret 只保存 `secret_ref`；health、OAuth、webhook 和 token rotation 由各自
  Adapter 负责。

### Slice E：Operations / Release

- 提供结构化日志、trace/correlation、metrics、health/readiness、审计检索和敏感字段 redaction。
- 提供 Docker/Windows 至少一种可重复部署 profile、配置校验、migration、rollback、backup/
  restore runbook 和升级兼容矩阵。
- Release candidate 必须通过全量测试、Ruff、OpenAPI/Schema drift、迁移 upgrade/downgrade、
  负载、故障注入、恢复演练、依赖扫描和安全审阅。

## 4. 需要维护者确认的外部选择

以下选择会改变实现边界，不能由代码默认猜测：

| 决策 | 推荐默认 | 影响 |
| --- | --- | --- |
| 生产认证 | OIDC-compatible issuer + 通用 Auth Adapter | 决定 session、issuer trust 和登录部署 |
| 生产 Store | PostgreSQL Adapter；SQLite 保留本地模式 | 决定并发、备份、连接池和迁移验证 |
| Secret 管理 | 外部 SecretResolver；开发环境只允许环境变量引用 | 决定 token rotation、审计和部署注入 |
| 部署形态 | Docker Compose/单机 first，后续再拆分 | 决定网络、进程、health 和 rollback 证据 |
| Runtime Provider | Hermes 或 Codex 二选一作为首个生产验证对象 | 决定真实 SSE、resume、tool 和凭据验收 |
| Voice/Device 首个目标 | 暂缓，先完成 Auth/Store/Runtime reliability | 避免在基础安全和恢复未稳定前扩展副作用面 |

推荐默认值已用于本地实现；OIDC issuer、远程 Store、Voice/Device 和真实 Provider 的具体
部署值与联调证据仍不写入 Core，必须在部署环境补充。

## 5. 总体退出条件

- 每个切片有 Accepted ADR、状态文档、实现范围和明确未实现范围；
- 生产模式不信任未验证身份 Header，Secret 不泄露；
- Provider/Store/Backup unknown 和 unavailable 语义可恢复且不伪造成功；
- SQLite local-dev 与生产 Store profile 的 migration/restore 证据可重复；
- Web UI、API、Adapter 和文档均通过 vendor-isolation/documentation-drift 检查；
- 有可复现启动、升级、回滚、备份、恢复、停机和故障处理 runbook；
- Release candidate 在隔离环境通过测试、负载、故障、安全和恢复验收。

本闸门现已接受，Slice A–E 的设计、实现、测试和状态文档已在 PR #25 合并到 `main`。
后续只补部署环境的真实连接、压力/故障/安全演练，不提前扩大 Core 或引入 Vendor 耦合。

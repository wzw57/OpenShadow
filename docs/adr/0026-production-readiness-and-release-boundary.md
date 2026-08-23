# ADR-0026：Production Readiness 与 Release Boundary

- 状态：**Accepted for Slices A–E / 本地发布基线已合并**
- 范围：生产化总体路线、认证安全、Runtime/Store/Backup、设备集成和发布验收
- 依赖：ADR-0021、ADR-0023、ADR-0024、ADR-0025，以及 `production-readiness-design-gate.md`

## Context

OpenShadow 已经是可运行的单机单用户参考项目，但 OIDC、生产 Session、Secret 管理、远程
Store、真实 Runtime reliability、Voice/Device 和运维发布仍不能从现有 local-dev headers、
SQLite 或 Adapter health 假设中自动推出。若一次性把这些能力写入 Core，会产生 Vendor 耦合、
身份伪造、Secret 泄露、未知副作用重试和无法恢复的迁移风险。

## Decisions

1. 生产化按 Slice A–E 顺序实施；每个 Slice 先有独立设计闸门、ADR、Contract/fixtures、
   实现和退出证据。
2. 认证通过通用 Auth Adapter 产生 `AuthContext`；Kernel/Application 不导入 OIDC issuer SDK。
3. 生产请求的 principal/endpoint/space 必须由验证后的 AuthContext 派生；local-dev Header
   兼容只能显式开启，不能作为生产认证。
4. Secret 只以 reference 形式经过 Profile/Adapter boundary；Secret material 不进入 Canonical、
   Export、日志、事件、错误体或 Web UI。
5. Canonical Repository Port 不因生产化改变；PostgreSQL 是推荐生产 Adapter，SQLite 继续作为
   local-dev/reference Adapter。
6. Runtime、Provider、Voice、Device 和 Integration 只能通过通用 Adapter/Capability 返回
   Result、Observation 或 Proposal；所有现实副作用继续经过 Shadow Authority。
7. `unknown`、Store unavailable、backup unverified 和 restore incomplete 都是显式状态，不能
   自动转换为 succeeded 或 completed。
8. Release 必须包含可重复的配置校验、migration/rollback、backup/restore、observability、
   load/failure/security 验收和运维 runbook。

## Rejected alternatives

- **一次性重写成微服务**：会扩大部署、事务和故障面，且没有当前测量证据支持。
- **在 Core 内直接实现某个 OIDC/Secret/Voice Vendor**：违反 Vendor isolation 和可替换边界。
- **把 local-dev headers 当成生产登录**：无法证明主体真实性、Session revoke 或审计完整性。
- **先实现 Voice/Device，再补 Auth/Store/Recovery**：会在安全和恢复未稳定时扩大现实副作用面。
- **让 Runtime/Provider 直接写 Canonical Store**：绕过 CommitAuthority、CAS、Owner/Space 和审计。

## Consequences

- 生产化会比当前参考项目多出部署和验收工作，但每个风险都有独立退出条件；
- 具体 OIDC issuer、生产 Store、Secret 管理、部署形态和首个 Runtime Provider 仍由部署环境提供；
- 当前 README、roadmap、documentation-sync 和状态文档必须在每个 Slice PR 同步更新；
- Slice A–E 已分别建立并接受设计闸门，基础实现已通过 PR #25 合并；外部部署验收不等同于
  本地代码验收，仍需按各 Slice 状态文档执行。

# ADR-0010: Phase 2 Integration Profile 注册边界

- Status: Accepted
- Date: 2026-08-22
- Owners: OpenShadow maintainers

## Context

Integration 是用户拥有的外部资产连接。Adapter 可替换、Provider 可失效、Secret 不能进入
普通记录，而 Integration 的用户身份和归属必须稳定。Stage 4 已提供 Adapter descriptor、
health observation、secret reference 和 capability contracts，但尚未定义 Integration
Canonical Profile 的最小写入边界。

## Decision

1. 使用 `shadow.profile.integration` + `IntegrationPayload`，以 `integration_id` 保持跨
   version 稳定；create/refresh 都由 Shadow CommitAuthority 管理。
2. Payload 保存 provider kind、外部非敏感标识、config/secret/adapter/health references、
   descriptor digest、status 和 lifecycle；secret 只允许 StableRecordRef，禁止原始凭据。
3. 注册命令必须带 principal/space、idempotency key；refresh 必须带 expected version，
   Owner/Space/CAS 失败时整次拒绝。
4. Service 只做离线 contract/reference/digest 校验和 Canonical Commit；不读取 secret、
   不访问 Provider、不执行 OAuth、webhook 或健康探测。
5. 同 key replay 返回相同 commit/result digest；不同请求、version、owner/space、Store
   unavailable 返回结构化错误且不产生部分记录。
6. 本 ADR 只交付 schema、Application Service、fixtures/tests 与 restart/故障证据；不新增
   HTTP、数据库、Proposal、Outbox、OperationJob、Binding 或外部副作用。

## Rationale

把连接治理事实与 Provider/Secret 生命周期分开，可以更换 Adapter 而不改变用户资产身份，
也不会把一个外部健康瞬间误当作长期 Canonical truth。引用而非复制凭据保持导出和日志的
安全边界。

## Alternatives considered

- 直接保存 token/password：违反 Secret 与普通资产分离，拒绝。
- 以 Adapter ID 作为 Integration 身份：更换实现会破坏用户配置，拒绝。
- 注册时自动探测 Provider：引入未授权网络副作用和不确定性，延后。
- 用新的 HTTP Integration API：当前阶段无 API 需求，保持 Application/Contract boundary。

## Consequences

- Integration 可审计、可恢复、可替换；Derived binding 和外部状态可重建。
- 健康状态需要独立 observation/adapter 证据，注册本身不保证远端可用。
- OAuth、导入、删除和多用户 ACL 仍需后续设计。

## Revisit triggers

- 需要 provider-specific secret rotation 或 OAuth lifecycle；
- health observation 无法表达真实 stale/unavailable 语义；
- 用户需要 Integration import/delete/ACL 超出本 profile；
- Adapter descriptor digest 需要签名或 trust chain。

# ADR-0028：Production Store、Backup 与 Portable Sync 边界

- Status: Accepted / implementation authorized
- Date: 2026-08-23
- Deciders: OpenShadow maintainers
- Related: ADR-0002、ADR-0011、ADR-0012、ADR-0019、ADR-0026

## Context

当前参考实现使用 SQLite，Portable Import/restore 和 Backup Metadata 已有独立能力，但
生产部署还缺少明确的 Store profile 选择、不可用语义和备份边界。直接把 PostgreSQL、
同步任务或云备份逻辑塞进 Kernel 会扩大核心并绕过 Canonical authority。

## Decision

保持 `CanonicalRepository` Port 不变，使用同一 SQLAlchemy/CAS Repository 支持 SQLite
和可选 PostgreSQL Profile；连接 URL 由组合根配置，未知或不可用 Store 直接失败，禁止
静默降级。跨 Store 只允许经过已验证的 Portable Export/restore；Backup 只保存加密元数据
和 opaque location/digest，不保存 Secret 或 Provider 私有状态。后台同步、复制和云备份
留在后续独立 Adapter 闸门。

## Consequences

- 本地开发无需数据库运维，生产可使用 PostgreSQL；
- migration/restore 证据可以复用同一 Contract；
- 生产部署必须显式安装 PostgreSQL 驱动并提供连接 URL；
- 真正的远程备份与同步仍需外部 Adapter 和独立故障演练。

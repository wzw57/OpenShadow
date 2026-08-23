# ADR-0030：Production Operations 与 Release Candidate Boundary

- Status: Accepted / implementation authorized
- Date: 2026-08-23
- Deciders: OpenShadow maintainers
- Related: ADR-0026、ADR-0027、ADR-0028、ADR-0029

## Context

OpenShadow 已有 health/readiness 和本地验收命令，但缺少统一的 correlation、敏感字段
redaction、低基数 metrics、生产配置快速失败和可重复启动说明。直接引入完整监控平台
会把部署依赖塞进核心。

## Decision

在 FastAPI 组合根提供轻量结构化 request telemetry、redacted logs、Prometheus text
metrics 和 health/readiness；业务状态仍由 Canonical Store 管理。生产配置显式校验，
Docker Compose 与 Windows 脚本作为参考部署，Release Candidate 由仓库内脚本执行静态
和本地验收闸门。外部 collector、压力/混沌平台和依赖扫描不在 Core。

## Consequences

- 本地和生产都能快速判断请求、Store、Runtime 与配置状态；
- telemetry 不携带 Secret/用户内容，后续可接入任何外部监控系统；
- 发布仍需部署环境完成 PostgreSQL、真实 Provider、压力和安全演练。

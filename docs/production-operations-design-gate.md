# Production Operations / Release 设计闸门

状态：**Accepted / 允许创建实现分支**  
分支：`production/operations-design-gate` → `production/operations-implementation`

本切片收口运行可见性、配置校验、重复部署和发布验收，不引入通用监控平台、后台
Worker 或新的业务状态模型。

## 固定决策

- 每个 HTTP 请求使用或生成 `X-Correlation-Id`；结构化日志只记录 route、method、status、
  latency、correlation 和非敏感 error code，不记录 credential、Cookie、prompt、Secret 或
  Provider 私有 payload。
- `/healthz` 表示进程可响应；`/readyz` 同时检查 Store、配置和 Runtime 基础状态；任何
  unavailable 都返回 503，不伪造 healthy。
- `/metrics` 仅输出低基数 Prometheus 文本指标：请求计数、错误计数、延迟总和、Store/Runtime
  readiness；不包含 principal、record id、prompt 或 token。
- 生产配置启动时显式校验 `SHADOW_AUTH_MODE`、session secret、database URL、runtime
  profile；校验失败快速失败，不回退 local-dev。
- 提供 Docker Compose 参考部署和 Windows 启动/停止脚本；migration upgrade/downgrade、
  backup/restore、health 和 rollback runbook 必须可重复执行。
- Release Candidate 闸门固定执行：pytest、Ruff、OpenAPI/Schema drift、Alembic upgrade/
  downgrade、git diff --check、配置 smoke test；真实压力/混沌/依赖扫描由部署环境补充。

## 明确不在本切片

- 引入 OpenTelemetry/Prometheus 服务端、日志 SaaS 或分布式 tracing collector；
- 自动扩缩容、Kubernetes Operator、通用 job/queue；
- 把日志、metrics 或 audit 当作 Canonical 业务记录；
- 在日志或 metrics 暴露认证主体、Session token、Secret、音频、prompt 或 Provider 内容。

## 退出条件

- correlation、redaction、metrics、health/readiness 有 API 测试；
- production 配置错误不会启动，local-dev 仍可显式运行；
- Docker/Windows 启动说明与 README/架构文档同步；
- release check 脚本在干净 SQLite 上通过，且文档列明远程 PostgreSQL/Provider 的外部前置条件。

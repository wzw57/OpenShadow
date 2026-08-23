# Production Store / Backup / Portable Sync 实现状态

更新时间：2026-08-23

| 能力 | 状态 |
| --- | --- |
| Store profile factory | 已实现：SQLite 与 PostgreSQL URL 显式选择；未知 backend 不回退 |
| PostgreSQL Adapter | 已实现 Adapter boundary：复用同一 SQLAlchemy/CAS Repository；需安装 `openshadow[postgres]` 并提供连接 |
| SQLite local-dev | 已实现并保留为默认参考 profile |
| Health/readiness unavailable | 已实现：Store 不可用返回 unavailable / 503 |
| Portable Export / restore | 已实现并通过 round-trip、digest、篡改、重复、冲突、Tombstone、Store outage 测试 |
| Backup Metadata | 已实现 Contract/metadata fixture；不保存 Secret、Provider 私有状态或索引 |
| 真实云备份 / 跨设备后台同步 | Contract-only，未实现 |

本切片不新增 SQL 表、不改变 `CanonicalRepository` Port、不提供同步后台任务。生产部署若
使用 PostgreSQL 必须显式配置 `SHADOW_DATABASE_URL=postgresql+psycopg://...` 并安装
`pip install -e ".[postgres]"`；连接或 migration 失败时启动失败，不能静默使用 SQLite。

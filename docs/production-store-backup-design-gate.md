# Production Store / Backup / Sync 设计闸门

状态：**Accepted / 允许创建实现分支**  
分支：`production/store-backup-design-gate` → `production/store-backup-implementation`

本切片把当前 SQLite 参考 Store 收口为可配置的生产 Store Profile，并冻结 Portable
Export/restore 与 Backup Metadata 的边界。它不改变 `CanonicalRepository` Port、不新增
同步数据库表、不把数据库连接细节泄漏到 Kernel，也不实现跨设备实时同步。

## 1. 固定决策

1. `CanonicalRepository` 是唯一写入 Port；SQLite 和 PostgreSQL 使用同一 SQLAlchemy
   Repository 实现与 CommitAuthority/CAS 语义。SQLite 继续用于 local-dev，生产配置可选择
   PostgreSQL；未配置 PostgreSQL 驱动时启动必须明确失败，不能静默回退 SQLite。
2. Store URL 只在组合根读取（`SHADOW_DATABASE_URL` 或 `create_app(database_url=...)`）。
   Kernel、Application Service、OpenAPI 和 Web UI 不判断数据库厂商。
3. Portable Export 是跨 Store 的标准边界：先校验 manifest、record digest、Tombstone、
   owner/space 映射和版本连续性，再通过一个 CommitPlan 写入目标 Store；任何冲突、篡改、
   不完整或 Store unavailable 都不得报告成功。
4. Backup 只持久化 `BackupMetadata`（加密、digest、retention、restore drill、erase
   propagation 状态和 opaque location ref），不把 Secret、Provider 私有状态或可重建索引
   写入 Canonical 或备份包。
5. Sync 仅定义显式 Portable snapshot 导入/导出；不实现后台同步、通用 Queue、事件总线、
   last-write-wins 或无证据的自动冲突解决。

## 2. 配置与失败语义

| 情形 | 语义 |
| --- | --- |
| `sqlite:///...` / `sqlite://` | local-dev/reference profile |
| `postgresql+psycopg://...` | production profile；连接或 migration 失败则启动/ready 失败 |
| 未知 scheme | 配置错误，结构化启动失败；不回退 |
| Store unavailable | health/readiness 报 unavailable；写入返回 503；不声称 commit/restore/backup 成功 |
| Export digest/tombstone 错误 | restore 在任何写入前拒绝 |
| restore 冲突 | all-or-nothing conflict；目标 Store 不产生部分版本 |
| backup 未加密或 restore drill 未完成 | metadata 仅为 rejected/pending，不可标为 verified |

## 3. 明确不在本切片

- 实际云备份、密钥托管、跨设备后台同步、复制协议；
- PostgreSQL 专用 schema/migration 分叉；
- Secret 原文、Provider 私有 session、向量索引或事件总线备份；
- 新的公共业务路由；已有 Portable Import/Export 与 Backup Metadata Contract 继续复用；
- 通过数据库级复制绕过 CommitAuthority/CAS。

## 4. 退出条件

- SQLite 与 PostgreSQL URL 通过同一 Repository Contract smoke test；
- production 配置不会静默回退到 SQLite，health/readiness 能反映 Store unavailable；
- Portable round-trip、篡改、重复、Tombstone、冲突和 Store outage 测试通过；
- Backup Metadata fixture 验证 encryption/digest/restore-drill/erase 状态；
- 文档、OpenAPI/Schema、roadmap 和状态文档无 drift。

实现状态：上述 profile、readiness 和已有 Portable restore Contract 已完成；真实
PostgreSQL 连接、云备份和跨设备同步仍需部署环境与独立 Adapter 验收。

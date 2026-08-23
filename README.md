# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 是一个可以长期存在、持续升级的个人 AI。**

OpenShadow 是一个本地优先、实现无关的个人 AI 资产与能力平台。用户始终在使用同一个 Shadow；Agent Runtime、模型、Memory Intelligence、Router、Runner、数据库、语音、设备与其他快速演进能力都通过可替换组件接入。

Shadow 不重新实现所有 AI 基础设施。它用一个小而稳定的主权内核，组合外部优秀项目，同时保证用户长期积累的身份、资料索引、记忆、任务、能力和治理记录不会随某个组件被替换而消失。

## 快速开始（Windows）

当前参考部署是单机、单用户、SQLite 和本地 Web UI。Python 要求 `>=3.12`；构建 Web UI
需要 Node.js/npm。Codex CLI 和 Hermes 都是可选的外部 Runtime，不是安装 OpenShadow 的前置条件。

```powershell
git clone https://github.com/wzw57/OpenShadow.git
Set-Location OpenShadow

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# 初始化/校验本地 SQLite 迁移
New-Item -ItemType Directory -Force .shadow | Out-Null
alembic upgrade head

# 构建 Web UI、启动 FastAPI，并打开项目管理页
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\start-shadow-management.ps1 -Build -OpenBrowser
```

启动后访问：

- Web UI：<http://127.0.0.1:8765/ui/>；
- FastAPI 文档：<http://127.0.0.1:8765/docs>；
- 存活检查：<http://127.0.0.1:8765/healthz>；
- 可服务检查：<http://127.0.0.1:8765/readyz>；
- OpenAPI：<http://127.0.0.1:8765/openapi.json>。

默认数据文件是 `.shadow/shadow.db`，属于本地运行产物，不提交到 Git。按 `Ctrl+C` 可停止
由启动脚本拉起的 Shadow 进程。

### 启动脚本参数

| 参数 | 作用 |
| --- | --- |
| `-Port 8765` | 修改 FastAPI 监听端口 |
| `-Build` | 执行 `npm install`（首次需要时）和 `npm run build` |
| `-OpenBrowser` | 服务就绪后打开 `/ui/` |
| `-RuntimeId codex` | 启动时选择指定 Runtime profile |
| `-AutoStartRuntime` | 与 `-RuntimeId` 一起使用，先启动该 Runtime |

例如，使用已安装的 Codex CLI：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\start-shadow-management.ps1 `
  -Build -RuntimeId codex -AutoStartRuntime -OpenBrowser
```

不使用管理脚本时，也可以在仓库根目录直接启动服务（Web UI 必须先构建）：

```powershell
python -m uvicorn shadow_server.app:app --host 127.0.0.1 --port 8765 --reload
```

如果 PowerShell 阻止虚拟环境脚本，只对当前进程放宽策略即可：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

## 当前已实现架构（代码事实）

OpenShadow 是模块化单体加进程外 Adapter，不是微服务集合。长期用户资产只写入
Canonical Store；外部智能和 Provider 只能通过通用 Port 返回结果或 Proposal，不能绕过
Admission、CommitAuthority、CAS 和版本生命周期。

```text
浏览器 / CLI
    │ REST
    ▼
FastAPI Shadow Server ───────────────► RuntimeSupervisor（本地控制面）
    │                                      │ profile lifecycle / select / health
    ▼                                      ▼
Application Services ───────────────► RuntimeAdapter Port
    │                                      ├─ Deterministic Adapter
    │                                      ├─ Codex CLI Adapter ──► codex exec --json
    │                                      └─ Hermes Adapter ─────► Hermes API Server
    │                                                                    │
    └─ Admission + CommitAuthority ──► SQLite Canonical Store              └─► Model Provider
       Run / Attempt / Message / Event
```

一次 Conversation turn 的主路径是：

```text
HTTP request
  → Admission
  → ConversationService
  → selected RuntimeAdapter
  → Run / Attempt / Message / Event
  → CommitAuthority + CAS
  → SQLite Canonical Store
```

管理页面的 Runtime 操作（start、stop、restart、health、probe、select）只改变后续请求的
Adapter binding。它不提供任意 prompt 或 shell 执行入口；正在执行的 Run/Attempt 会阻止
切换，实际工作仍走 Conversation/Admission/Run/Attempt 路径。

### 当前代码项目结构

下面这棵树对应当前仓库已经存在的目录和主要职责，不是未来模块的占位图：

```text
OpenShadow/
├─ packages/
│  ├─ shadow-kernel/src/shadow_kernel/       Kernel Port、Envelope、Commit、Admission、CAS
│  └─ shadow-application/src/shadow_application/
│                                             Conversation、Profiles、Identity、Supervisor
├─ adapters/
│  ├─ store-sqlite/src/shadow_store/         SQLite Canonical Repository
│  ├─ test-deterministic/src/shadow_adapters/  确定性 Runtime（默认开发基线）
│  ├─ hermes-agent/src/shadow_hermes/        Hermes HTTP Adapter（独立边界）
│  └─ codex-agent/src/shadow_codex/          Codex CLI JSONL Adapter（独立边界）
├─ apps/
│  ├─ shadow-server/shadow_server/            FastAPI 组合根、OpenAPI、静态 UI 托管
│  └─ shadow-web/src/                         React/Vite Conversation、Profile、Management UI
├─ config/runtime-profiles.json              本地 Runtime profile（非敏感配置）
├─ contracts/                                 OpenAPI、JSON Schema、fixtures、manifest
├─ migrations/                                Alembic 迁移
├─ scripts/start-shadow-management.ps1       Windows 启动/管理脚本
├─ tests/                                     Contract、Service、Repository、API、UI、故障测试
├─ docs/                                      设计闸门、ADR、架构和交付状态
├─ pyproject.toml                             Python 包、依赖和测试/lint 配置
└─ alembic.ini                                SQLite migration 默认配置
```

### 当前实现的分层图

```text
┌────────────────────────────────────────────────────────────────────┐
│ Web UI (React/Vite) │ curl/SDK │ FastAPI /docs / OpenAPI            │
└───────────────────────────────┬────────────────────────────────────┘
                                │ HTTP
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│ apps/shadow-server: 组合根、身份/Space context、路由、错误映射      │
└───────────────┬───────────────────────────────┬────────────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────────┐  ┌─────────────────────────────────┐
│ Application Services          │  │ RuntimeSupervisor               │
│ Conversation / Memory /      │  │ profile lifecycle、health、      │
│ State / Task / Action /      │  │ select；不承载业务数据           │
│ Identity / Outbox            │  └───────────────┬─────────────────┘
└───────────────┬──────────────┘                  │ 通用 Adapter Port
                ▼                                 ▼
┌──────────────────────────────┐  ┌─────────────────────────────────┐
│ shadow-kernel                 │  │ Deterministic │ Codex │ Hermes  │
│ Admission / CommitAuthority  │  │ Adapter       │ CLI   │ HTTP    │
│ Envelope / CAS / Policy       │  └─────────────────────────────────┘
└───────────────┬──────────────┘
                │ Canonical writes / reads
                ▼
┌────────────────────────────────────────────────────────────────────┐
│ adapters/store-sqlite: SQLAlchemy Repository → SQLite               │
│ canonical_records / idempotency receipts / run_events               │
└────────────────────────────────────────────────────────────────────┘
```

当前已经实现的是一套模块化单体：Runtime Adapter 可以是外部进程或 HTTP 服务，但 Kernel、
Application 和 Web UI 不导入 Hermes/Codex 私有类型，也不直接连接 Model Provider。

## 技术栈

| 层 | 技术 | 当前用途 |
| --- | --- | --- |
| 后端语言 | Python `>=3.12` | Kernel、Application、Adapter、FastAPI 组合根 |
| HTTP/API | FastAPI `>=0.115`、Uvicorn | REST、OpenAPI、健康检查、静态 Web UI |
| 数据模型 | Pydantic 2、Python typing | 请求校验、Profile payload、Runtime descriptor |
| 持久化 | SQLAlchemy 2 + SQLite | Canonical version rows、幂等 receipt、Run events |
| 数据库迁移 | Alembic | `upgrade head` / `downgrade base` |
| Contract | JSON Schema、`jsonschema`、OpenAPI YAML | Profile、fixtures、错误体和文档同步 |
| Web UI | React 19、TypeScript 5.7、Vite 6 | Conversation、Memory/State/Task/Action 查询、项目管理 |
| Python 测试 | pytest、pytest-asyncio、httpx | Contract、Service、Repository、API 和故障路径 |
| Python 质量 | Ruff | E/F/I/B/UP 规则集和导入排序 |
| Agent Runtime | Deterministic Adapter、Hermes Adapter、Codex CLI Adapter | 通过 `shadow.agent-runtime` Port 接入，不进入核心 |
| 外部 Agent/Provider | Hermes API、Codex CLI、可选 Model Provider | 由 Adapter 隔离；不是 OpenShadow 自研组件 |

Node.js/npm 只用于 Web UI 的依赖安装和构建；运行 FastAPI 不需要 Node 进程。默认不需要
Ollama、本地模型或 GPU。

## 设计总架构（长期目标）

下面是设计层面的完整目标，不等于所有模块都已经实现。`[已实现]` 表示当前代码已有闭环，
`[Contract]` 表示已有 Schema/ADR/接口边界但不保证完整运行，`[后续]` 表示尚未进入实现。

```text
                           User-owned Shadow
┌──────────────────────────────────────────────────────────────────────────┐
│ User Surfaces                                                             │
│ [已实现] Web / API / Conversation    [后续] Voice / Device / Connectors  │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ work-bearing input
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Sovereignty & Continuity Kernel [已实现]                                  │
│ Identity / Owner / Space · Canonical Envelope · Version/CAS              │
│ Proposal → Validate → Commit · Admission · Run/Attempt · Erasure Intent │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ typed Profile records / Proposals
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Official Profiles                                                        │
│ [已实现] Conversation · Memory · State · Task · Action · Outbox           │
│ [已实现] SkillAsset · Integration · Pulse · Router/Policy · Erasure meta │
│ [Contract/延后] Voice · OAuth/OIDC · remote sync · full multi-user        │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │ normalized Port / Adapter boundary
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Replaceable Intelligence & Execution                                     │
│ [已实现 Adapter] Deterministic · Hermes · Codex CLI                      │
│ [Contract/延后] Model Worker · Memory Recall/Index · Resolver · Router    │
│ [后续] Tool/Capability bridge · Provider execution · device/voice runtime │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ Store / Portability / Reliability                                         │
│ [已实现] SQLite Canonical Repository · migrations · integrity checks      │
│ [已实现] export/import contract · tombstone/erase boundary · outbox      │
│ [后续] remote Store · encrypted device backup · cross-device sync         │
└──────────────────────────────────────────────────────────────────────────┘
```

### 设计总架构的关键边界

- 外部 Runtime、Model、Memory Engine、Resolver、Router 和 Provider 只能返回结果、
  Observation 或 Proposal；最终写入始终回到 Shadow 的 Authority/CAS。
- Web UI 只依赖 vendor-neutral API；Hermes/Codex 名称只出现在 Adapter 和部署 profile。
- Canonical Store 保存用户长期资产，不保存 Provider Secret、Runtime 私有 Memory、缓存或
  可重建索引。
- Phase 0–4 和 Phase 5 Core Slice 已完成当前授权范围；OAuth/OIDC、Voice、远程 Store、
  跨设备同步和生产级多用户发行仍保持 Contract-only 或后续闸门。

### 设计总架构的产品视图

上面的设计总架构展示责任和数据流；下面补充用户看到的产品与资产分层：

~~~text
Shadow
├─ Tiny Kernel
│  ├─ Identity & Ownership
│  ├─ Canonical Record & Lifecycle
│  ├─ Proposal / Validate / Commit Authority
│  ├─ Work Admission & Minimal Continuity
│  ├─ Extension Contract & Binding
│  └─ Portability & Erasure Intent
│
├─ Official Profiles
│  ├─ Conversation / Memory / State
│  ├─ Durable Task / Action
│  ├─ Skill / Capability / Integration
│  └─ Profile-specific schemas and invariants
│
├─ Replaceable Components
│  ├─ Runtime / Model / Runner / Workflow / Router
│  ├─ Memory Intelligence / Retrieval / State Resolver
│  ├─ Store / Search / Scheduler / Policy Engine
│  ├─ Source / Provider / MCP / Skill Runtime
│  └─ Web / Voice / Device Interfaces
│
└─ User-owned Assets
   ├─ Conversations / Memories / Tasks / State
   ├─ Skills / Executables / Integrations
   ├─ External Asset Catalog / Artifacts
   └─ Bindings / Policies / Action History
~~~

Shadow 是完整产品。Tiny Kernel 只理解长期主权和连续性所必需的控制语义；Memory、World State、Task、Skill 等由版本化 Profile 定义，不被硬编码成不可演进的内核模块。

## 核心不变量

### 所有承载工作的输入经过 Shadow

Chat、Voice、Schedule、Event、API Command 和 Semantic Pulse Proposal 等工作入口都经过 Admission。一个被接受的工作 Request 创建一个 Root Run；准入失败只形成最小 Admission Record。

健康检查、静态资源、只读控制面查询、已有 Run 的事件订阅和内部恢复步骤不创建 Root Run，但仍受身份、权限和审计约束。

### 所有执行受 Shadow 治理，但不都经过 Agent Runtime

Execution Binding 使用可扩展、带命名空间的 `target_kind`。首批 well-known kinds 是：

- `shadow.agent-runtime`；
- `shadow.model-worker`；
- `shadow.deterministic-runner`；
- `shadow.workflow-target`；
- `shadow.capability-provider`。

它们不是永久封闭枚举。Core 根据 Capability、数据边界、副作用、预算和健康状态治理执行，不为每种 Target 硬编码业务分支。

### 外部智能只能提议，Shadow 才能提交

~~~text
External Intelligence / Execution
                ↓
          Typed Proposal
                ↓
   Schema + Authority + Policy Validation
                ↓
        Canonical Commit
                ↓
  Versioned Canonical Record / Profile
~~~

Memory Engine 不能直接改 Memory，Router 不能直接改 Binding，Runtime 不能直接完成 Durable Task，State Resolver 不能直接改当前状态，Provider 不能绕过 Action Authority 产生现实副作用。

### Canonical Record 统一治理，但不退化成万能 JSON

所有长期记录共享最小治理信封：

~~~text
CanonicalEnvelope
├─ record_id / record_type / schema_ref
├─ owner_ref / space_id / created_by
├─ classification / provenance
├─ version / lifecycle / retention
└─ typed_payload
~~~

Envelope 负责身份、归属、版本、来源和生命周期。各 Profile 继续定义必要的类型化 Schema、合法状态转换和迁移规则；仅更换 JSON Schema 不能替代语义迁移。

## Memory 与 World State

Canonical Memory 是 `memory` Profile 的用户资产，必须在更换 Memory Intelligence 后继续存在。外部组件负责提取、整理、召回、去重、Embedding、Graph 和排序；Shadow 只治理 Candidate、版本、来源、纠正、删除和提交。

World State 是官方 `state` Profile，不是 Tiny Kernel 内建知识图谱。Kernel 只提供通用身份、来源、证据、时间有效性和提交机制；State Profile 定义 state key、Observation、fresh / stale / unknown 与迁移语义；采集、融合、预测、本体和领域查询全部外置。

~~~text
Source Adapter / State Resolver
             ↓
       State Proposal
             ↓
     Shadow validates
             ↓
Versioned State Profile Record
~~~

Accepted State 可恢复和迁移，但允许过期。Shadow 不要求实时访问所有外部知识库或设备，只在需要时调用并诚实表达 stale / unknown。

## Skill 与能力资产

Shadow 不自创 Skill 内容格式。官方 Profile 原生兼容 [Agent Skills 规范](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx)：保留标准 `SKILL.md` 以及可选的 `scripts/`、`references/`、`assets/`。

Shadow 的 `SkillAsset` 只保存治理信息：稳定 ID、Owner / Space、来源、固定版本或 revision、digest、信任、权限策略、数据等级、安装状态和 Runtime Projection。标准 Skill Bundle 不因 Shadow 元数据而被修改；Provider Skill ID 只是外部引用。

具体 Skill 发现、加载、Prompt 投影、脚本执行和 Provider 上传由 Adapter 完成。Shadow 独立执行权限和信任边界，不能把实验性的 `allowed-tools` 当作最终授权。

外部资料也遵循同一原则：Notion、Obsidian、Drive、Email 和文件系统中的原始内容继续由外部来源持有；Shadow 的 Asset Catalog 默认只记录“存在什么、在哪里、如何访问”，需要时再读取。

## Adapter 与基础设施边界

通用 `AdapterDescriptor` 保持最小：

~~~text
adapter_id
adapter_family
contract_versions
capabilities
config_schema_ref
implementation_ref
health
~~~

权限、Secret、迁移、Checkpoint、数据边界和 Reconciliation 是按 Adapter Family 声明的可选能力，不进入一个万能 Manifest。

Runtime 基础 Port 只要求 `describe`、`execute` 和 `events`；cancel、checkpoint、native resume、semantic handoff、progress、usage 与 reconciliation 通过 Capability Negotiation 声明。Adapter 不得伪造不支持的能力。

Shadow 也不抽象整套数据库。Store Family 分成 Canonical Repository、Migration、Portable Export / Import、Backup、Outbox 和 Integrity Capability。只有 Canonical 语义和标准可移植导出需要跨 Store 一致；物理 Schema、复制、备份和队列实现属于外部基础设施。

### Runtime 配置与替换

本地 Runtime profile 位于 [`config/runtime-profiles.json`](config/runtime-profiles.json)。当前
默认值是：

| Runtime | 默认状态 | 说明 |
| --- | --- | --- |
| `deterministic` | active / auto-start | 无外部模型、无副作用，用于稳定开发和验收 |
| `codex` | enabled / 按需启动 | 通过已安装的 `codex exec --json` CLI 调用；Provider/登录由 Codex 自己管理 |
| `hermes` | disabled | 需填写实际 `launch.command`、health URL 和 Hermes 侧 Provider 配置 |

Runtime Management 只读取经过 Schema 校验的 profile，不保存 API key、Secret 原文、Hermes
私有 Session 或 Codex 内部 State。也可以使用兼容旧部署的环境变量注入单个 Adapter：

```powershell
$env:SHADOW_RUNTIME_ADAPTER_FACTORY = "shadow_hermes:create_runtime_adapter"
$env:SHADOW_RUNTIME_KIND = "hermes"
python -m uvicorn shadow_server.app:app --host 127.0.0.1 --port 8765
```

在配置 Hermes 前不要猜测其启动命令；将真实安装方式写入本地 profile，并保持 Hermes
工具默认关闭。DeepSeek `deepseek-v4-flash` 是 Hermes 下游的 Model Provider，不是
Shadow 的直连 Runtime，也不会被 Web UI 直接调用。

### 公开 API 入口

API 的完整契约以 [`contracts/openapi/openapi.yaml`](contracts/openapi/openapi.yaml) 和运行时
`/openapi.json` 为准。常用入口如下：

| 类别 | 入口 |
| --- | --- |
| 状态 | `GET /healthz`、`GET /readyz`、`GET /v1/runtime` |
| 运维指标 | `GET /metrics`（低基数 Prometheus 文本，不含主体、Token、Secret 或 prompt） |
| Conversation | `GET/POST /v1/conversations`、`POST /v1/conversations/{id}/turns` |
| Run | `GET /v1/runs/{id}`、`GET /v1/runs/{id}/events`、`POST /v1/runs/{id}/retry` |
| Profile 查询 | `GET /v1/memories`、`GET /v1/states`、`GET /v1/tasks`、`GET /v1/actions` |
| Proposal | `POST /v1/proposals`、`POST /v1/proposals/{id}/accept` |
| Runtime 管理 | `GET /v1/management/overview`、`GET /v1/runtime/instances` |
| Runtime 生命周期 | `POST /v1/runtime/instances/{id}/start`, `.../stop`, `.../restart`, `.../select`；`GET .../{id}/health`；`POST .../{id}/probe` |

Runtime 的 start/stop/restart/select 写操作要求 `Idempotency-Key`。需要身份或 Space
边界的写入使用 `X-Principal-Ref`、`X-Space-Id` 等契约 Header；当前默认是单用户本地上下文，
生产模式可使用 OIDC-compatible verifier 或 signed-session 验证；local-dev header 兼容仅在
显式 `SHADOW_AUTH_MODE=local-dev` 下开启，多用户完整发行仍是后续能力。

## 本地开发与验收

代码、Schema、fixtures、API 和文档必须在同一变更中保持同步。常用检查命令：

```powershell
# Python 依赖（已安装可跳过）
python -m pip install -e ".[dev]"

# 后端质量与全量测试
ruff check packages/shadow-kernel/src packages/shadow-application/src `
  adapters/test-deterministic/src adapters/store-sqlite/src `
  adapters/hermes-agent/src adapters/codex-agent/src `
  apps/shadow-server migrations tests
pytest -q

# SQLite 迁移回滚（隔离数据库）
New-Item -ItemType Directory -Force .shadow | Out-Null
$env:SHADOW_DATABASE_URL = "sqlite://"
alembic upgrade head
alembic downgrade base
Remove-Item Env:SHADOW_DATABASE_URL

# Web UI 类型检查与生产构建
Push-Location apps/shadow-web
npm install
npm run build
Pop-Location

git diff --check
```

当前基线验收包括 Contract/Repository/API、幂等重放、Store unavailable、重启恢复、Runtime
生命周期、Web UI Chromium smoke 和 Alembic upgrade/downgrade。测试用 SQLite 内存库或隔离
文件库；真实 Hermes Provider 和 Codex 模型请求属于部署联调，不是默认测试前置条件。

### 生产参考启动

SQLite 仍是 local-dev 默认；生产必须显式选择 Store，不会从错误 URL 静默回退：

```powershell
$env:SHADOW_DATABASE_URL = "postgresql+psycopg://shadow:<password>@localhost:5432/shadow"
$env:SHADOW_AUTH_MODE = "oidc"
$env:SHADOW_AUTH_SESSION_SECRET = "<deployment-secret>"
python -m pip install -e ".[dev,postgres]"
python -m uvicorn shadow_server.app:app --host 0.0.0.0 --port 8080
```

也可使用仓库中的 `docker compose up --build`（需要先设置 `POSTGRES_PASSWORD`）。发布前
运行 `./scripts/release-check.ps1`，它会执行全量测试、Ruff、SQLite migration upgrade/
downgrade 和 `git diff --check`。生产部署仍需在目标环境完成真实 PostgreSQL、OIDC、
Runtime Provider、备份恢复和压力/安全演练。

## 代码目录

```text
packages/shadow-kernel/        稳定 Kernel Port、Envelope、Commit、Admission、CAS
packages/shadow-application/   Conversation、Profile、Task、Action、Identity、Supervisor
adapters/store-sqlite/         SQLite Canonical Repository 与 migration boundary
adapters/test-deterministic/   无外部依赖的确定性 Runtime Adapter
adapters/hermes-agent/         Hermes HTTP/OpenAI-compatible Adapter（独立隔离）
adapters/codex-agent/          Codex CLI JSONL Adapter（独立隔离）
apps/shadow-server/             FastAPI 组合根、OpenAPI、静态 Web UI 托管
apps/shadow-web/                React/Vite Conversation、Profile、Management UI
contracts/                      JSON Schema、fixtures、OpenAPI 和 manifest
migrations/                     Alembic migration
scripts/                        本地启动和管理脚本
docs/                           设计闸门、ADR、架构、状态与验收证据
tests/                          Contract、Service、Repository、API、UI 和故障路径测试
```

## 治理与长期升级

- 每个 Canonical Record 从第一版具有明确 Owner 和 Space；
- 近期只实现单用户、默认 Personal Space 和隐式 Home Space；
- Core 只执行少量确定性 Policy：数据等级、Capability、Approval、Budget、副作用、有效期和撤销；
- 复杂 Policy 计算可以外置，但 Core 保留最终检查；
- 用户拥有纠正、逻辑删除、最终物理清除、导出和迁移权；
- 标准导出不依赖 Secret、缓存、索引或具体组件私有格式；
- Store 故障时暂停 Canonical Commit，默认禁止未记录现实副作用；
- Domain Event 只是通知信封，不采用强制 Event Sourcing；
- Outbox 只解决跨边界副作用可靠提交；
- OperationJob 只用于迁移、导出、备份和 Erasure 等长操作。

## 当前明确不自研

OpenShadow 不自研数据库引擎、通用 Agent Loop、基础模型、智能 Router 算法、Memory Intelligence、向量数据库、知识图谱、Workflow Engine、脚本运行时与沙箱、语音引擎、浏览器 Agent、Coding Agent、设备协议栈或领域数字孪生。

OpenShadow 自行实现的范围收紧为：

- Stable ID、Owner、Space、Version 与 Canonical Envelope；
- Proposal / Validate / Commit 主权边界；
- Admission、Run / Attempt 与最小 Task Continuity；
- 类型 Profile 注册、Schema 兼容与迁移控制；
- 最小 Adapter Registry、Binding 与 Capability 校验；
- 确定性数据、授权、预算和副作用执行点；
- 标准导出、完整性校验与 Erasure Intent；
- 用户查看、纠正、撤销、删除和导出 API。

## 文档

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [Core / External 责任矩阵](docs/responsibility-matrix.md)
- [关键用例](docs/use-cases/README.md)
- [领域模型](docs/domain-model.md)
- [状态机基线](docs/state-machines.md)
- [完整技术架构](docs/technical-architecture.md)
- [分阶段实现计划](docs/implementation-stages.md)
- [参考实现 Profile](docs/implementation-profile.md)
- [开发路线](docs/roadmap.md)
- [Phase 0–1 实现状态](docs/phase0-1-status.md)
- [Stage 4 Contract 基线](docs/contract-baseline.md)
- [架构决策记录](docs/adr/README.md)
- [Web UI 设计闸门](docs/web-ui-design-gate.md)
- [Web UI 实现状态](docs/web-ui-status.md)
- [Runtime 集成状态](docs/runtime-integration-status.md)
- [Runtime Management 实现状态](docs/runtime-management-status.md)
- [Phase 5 Core Slice 状态](docs/phase5-status.md)
- [Production Readiness 设计闸门](docs/production-readiness-design-gate.md)
- [ADR-0026 Production Readiness](docs/adr/0026-production-readiness-and-release-boundary.md)
- [Production Auth 设计闸门](docs/production-auth-design-gate.md)
- [ADR-0027 Production Auth](docs/adr/0027-production-auth-and-security.md)

## 当前状态

Stage 0–3 已形成需求、责任、用例和领域基线，Stage 4 的 Action 等能力也已按切片完成设计与实现。当前仓库已具备 Phase 0–4 的核心基线和 Phase 5 Core Slice，以及可选的外部 Agent Runtime Adapter：默认配置使用确定性 Adapter，Codex CLI profile 可由项目管理页启停和切换，Hermes profile 默认关闭并需按本机部署配置启用。FastAPI、Application、Kernel 和 Web UI 不包含任何厂商分支。首版 Web UI 已完成，可通过 FastAPI `/ui/` 使用；Shadow 没有自研 Agent Loop，也不直接连接模型 Provider。Hermes + DeepSeek `deepseek-v4-flash` 仍是已验证的可选联调路径；细粒度 Runtime SSE/Session resume 和受治理的工具桥接仍未完成。

# Web UI 设计闸门

状态：**Accepted / 首版 Conversation UI 已冻结**  
分支：`web-ui/design-gate` → `web-ui/implementation`

## 1. 目标与边界

首版 Web UI 是 Shadow API 的单用户参考客户端，不重新实现 Kernel、Conversation
Service 或 Agent Runtime。它只通过公开 HTTP/SSE 边界读取和提交数据。

首版只覆盖：

- 本地单用户身份与 personal space；
- Conversation 列表、新建、选择和消息查看；
- 文本 Turn 提交；
- pending / running / succeeded / failed 的 Run 状态；
- Run 事件查看和 Retry；
- Shadow Server ready 状态与当前 Runtime 类型提示。

首版不覆盖：

- 多用户登录、注册、ACL 或远程暴露；
- Memory、State、Task、Action 管理页面；
- Hermes 工具调用、Secret、Session resume；
- token 级流式渲染；
- 浏览器直连 Hermes 或任何 Model Provider；
- 浏览器持久化 Provider API Key。

## 2. 参考部署

开发环境使用 Vite dev server，通过 proxy 将 `/healthz`、`/readyz` 和 `/v1/*`
转发到 Shadow FastAPI；生产构建产物由同一 Shadow 进程在 `/ui` 提供，避免浏览器
跨源访问和 CORS 配置漂移。

```text
Browser
  │ same-origin /ui (production) or Vite proxy (development)
  ▼
Shadow FastAPI
  ├── /healthz /readyz
  ├── /v1/conversations
  ├── /v1/conversations/{id}/messages
  ├── /v1/conversations/{id}/turns
  ├── /v1/runs/{id}
  ├── /v1/runs/{id}/events
  └── /v1/runs/{id}/retry
        │
        ▼
  ConversationService → Hermes Adapter or Deterministic Adapter
```

Web UI 不拥有数据库连接、CommitAuthority、Hermes 凭据或 Canonical record。

### 2.1 Runtime vendor neutrality

Web UI 只理解 `/v1/runtime` 的通用 `status`、`target_kind` 和 opaque `descriptor`。
它不得根据 `target_kind`、`descriptor_id` 或环境变量推断任何具体 Vendor。Vendor
显示名、配置和健康语义属于具体 Adapter 与部署配置；Server 只解析通用工厂引用，
替换 Runtime 不应修改 `apps/shadow-web`。

## 3. 单用户身份

当前 profile 固定使用：

```text
principal_ref = principal-local
space_id      = space-personal
endpoint_ref  = endpoint-local-web
```

这些值是本地单用户开发 profile，不是未来的认证协议。浏览器可以发送
`X-Principal-Ref` 和 `X-Space-Id`，但生产多用户模式必须由服务端认证上下文覆盖，
不能信任浏览器自行声明的身份。

## 4. API 契约

### 4.1 Conversation

- `GET /v1/conversations` 返回 `{ "records": [...] }`；
- `GET /v1/runtime` 返回不含 Secret 的 Runtime descriptor、target kind 和可选 health；
- `POST /v1/conversations` 返回 `201` 和 `{ "record": ... }`；
- `GET /v1/conversations/{id}/messages` 返回 `{ "records": [...] }`；
- `POST /v1/conversations/{id}/turns` 要求 `Idempotency-Key`，成功首次提交返回
  `202`，重放返回 `200`，响应包含 `root_run_ref`、`message_ref`、`replayed` 和
  `durable`。

### 4.2 Run

- `GET /v1/runs/{id}` 返回当前 Run record；
- `GET /v1/runs/{id}/events` 是有限 SSE 响应，包含已经持久化的事件，连接结束后
  UI 通过 Run 查询和消息查询得到最终状态；
- `POST /v1/runs/{id}/retry` 创建下一次受治理重试，首版只在失败 Run 上展示。

当前 Hermes Adapter 是非流式文本切片，UI 不把有限 SSE 误表示成 token streaming。

### 4.3 错误

领域错误使用 `application/problem+json`，UI 至少显示 `message`，并保留 `code`、
`category` 和 `retryable` 供重试和诊断使用。网络失败、503 和 Runtime unavailable
必须显示为可恢复错误，不得伪造成功消息。

## 5. 状态与交互不变量

- 发送按钮在请求完成前禁用，避免无意重复提交；
- 每次 Turn 生成稳定的客户端 `submission_id` 和 `Idempotency-Key`；
- `202` 后先显示 Run pending/running，再刷新消息和 Run；
- SSE 断开不代表失败，UI 必须回查 Run；
- `replayed=true` 时不得追加重复消息；
- 页面刷新后通过 Conversation 和 Message API 恢复状态；
- API Key、Hermes Session secret 和数据库内容不写入 localStorage。

## 6. 设计闸门验收

- [x] 首版范围只包含单用户 Conversation UI；
- [x] 同源生产部署与 Vite 开发 proxy 已冻结；
- [x] API 状态码、错误体和 SSE 语义已冻结；
- [x] Provider secret 不进入浏览器；
- [x] UI 不包含任何具体 Runtime/Model Vendor 分支；
- [x] 不提前实现 Memory、Action、Task、Tool bridge 或多用户认证；
- [x] 前端构建、API 集成和真实浏览器验收在实现分支完成。

## 7. Conversation UI 可靠性切片

本切片只增强现有 Conversation 客户端的状态收敛，不扩大公开 API 或 Profile 范围：

- `pending` / `running` Run 使用现有 `GET /v1/runs/{id}` 定时回查，直到 terminal state；
- 每次回查同时读取现有有限 `/events`，事件只作为诊断展示，不伪装成 token streaming；
- Runtime 与 Shadow readiness 支持手动刷新，不能把浏览器缓存当作权威状态；
- 网络错误保留 `code`、`category`、`retryable`，可恢复错误提供重试入口；
- 事件详情只渲染通用 `sequence`、`event_type`、opaque payload，不解释 Provider 私有字段；
- 页面刷新仍以 Conversation、Message、Run API 为权威，不写入 localStorage；
- 不新增后端路由、数据库字段、Runtime Adapter 分支或 Memory/State/Task/Action 页面。

验收：前端构建通过；发送后非 terminal Run 会自动收敛；事件面板可展开且不重复；
ready/runtime 手动刷新可见；失败和网络错误可以重新加载；Vendor-neutrality 与现有
全量 API 测试保持通过。

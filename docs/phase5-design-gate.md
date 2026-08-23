# Phase 5 Multi-endpoint & Multi-user 设计闸门

状态：**Accepted / Phase 5 Core Slice 获准实现**  
范围：Endpoint identity、Space membership、邀请、读 ACL 与 Web context

## 1. 目标

Phase 5 在不改变 `owner_ref` / `space_id`、Proposal/Commit、Admission 和 Canonical
Envelope 的前提下，把当前可信 headers 的单用户边界升级为可验证的 Endpoint 与 Space
访问上下文。首个实现只使用现有 Canonical record version rows，不新增数据库表、通用
认证平台或远程消息总线。

## 2. 冻结的 Profile

| Profile | Record type | 作用 |
| --- | --- | --- |
| Endpoint | `shadow.profile.endpoint` | 设备/浏览器端点、pairing 状态、trust、能力摘要 |
| Space | `shadow.profile.space` | Space 元数据与 owner |
| Membership | `shadow.profile.space-membership` | principal 在 Space 的 `owner/editor/viewer` 角色 |
| Invitation | `shadow.profile.space-invitation` | 一次性、过期、可撤销的邀请状态 |

这些 Profile 都是普通 Canonical records；所有变更经过 `CommitAuthority` 和 CAS。邀请
只保存不可逆 digest，不保存明文 token；Endpoint secret/token 不写入 Canonical payload。

## 3. 身份与访问上下文

- 本切片不实现 OAuth/OIDC 或 session verifier。当前实现只接受显式的
  `X-Principal-Ref` / `X-Space-Id` / `X-Endpoint-Ref` local-dev context；生产部署必须在
  外层接入受验证的 session adapter，并在 adapter 边界转换为同一 `AccessContext`，不得把
  Bearer 解析逻辑临时塞入业务服务。
- Context 包含 `principal_ref`、`endpoint_ref`、`space_id`、membership role 和 endpoint
  trust 状态；缺失或 revoked endpoint 拒绝 work-bearing 请求。
- `owner_ref` 仍是资产创建者/拥有者；共享资产通过 `space_id` 暴露，不把个人资产自动
  转成共享资产。
- Endpoint pairing 是显式命令，生成一次性短期 token 的 digest；重复 pairing 使用同一
  idempotency key 返回稳定 Endpoint 引用。

## 4. 角色与权限

| 操作 | owner | editor | viewer |
| --- | --- | --- | --- |
| 读取 Space 内 active heads | ✓ | ✓ | ✓ |
| 创建 Conversation/Memory/State/Task/Action Proposal | ✓ | ✓ | - |
| 修改/逻辑删除他人资产 | ✓ | 仅受 Profile policy 允许 | - |
| 邀请、撤销成员、修改角色 | ✓ | - | - |
| Pair/revoke 自己的 Endpoint | ✓ | ✓ | ✓ |

首片不实现任意 ACL expression；默认 deny，只有当前 Space 的有效 Membership 赋予访问。
Owner 的 personal Space 保持兼容：没有 Membership record 时，`principal_ref == owner_ref`
仍视为 owner。

## 5. HTTP Contract

- `POST /v1/endpoints/pair`：创建或重放 Endpoint pairing，返回 endpoint ref 和一次性
  opaque token（只在响应中出现一次）。
- `POST /v1/endpoints/{endpoint_id}/revoke`：CAS 撤销 Endpoint。
- `GET /v1/spaces`、`GET /v1/spaces/{space_id}`：返回当前主体可见 Space。
- `POST /v1/spaces`：创建 Space 与 owner membership 原子提交。
- `GET /v1/spaces/{space_id}/members`：列出脱敏 membership。
- `POST /v1/spaces/{space_id}/invitations`、`POST /v1/invitations/{id}/accept`：邀请/接受。
- `DELETE /v1/spaces/{space_id}/members/{principal_ref}`：owner 撤销成员。
- 既有 Profile 查询改为按 context 的 Space ACL 过滤；既有写入保留原路由和
  `Expected-Version` / `Idempotency-Key`。

所有 mutation 要求 `Idempotency-Key`；目标更新要求 `Expected-Version`。不新增临时 merge
路由，不把 Endpoint 或 Membership 写入 Proposal 审批表。

## 6. 错误、重放与安全不变量

统一结构化错误至少包括：

- `shadow.identity.unauthorized`
- `shadow.identity.endpoint-revoked`
- `shadow.identity.pairing-expired`
- `shadow.space.not-found`
- `shadow.space.membership-denied`
- `shadow.space.invitation-invalid`
- `shadow.space.role-escalation-denied`
- `shadow.repository.expected-version-conflict`
- `shadow.repository.idempotency-mismatch`
- `shadow.repository.unavailable`

Pair、邀请接受、成员撤销和角色变更必须原子；重复命令只返回稳定引用，不产生额外
Membership/Endpoint/Invitation 版本。过期、撤销和删除后的旧 token、旧 context、旧
invitation 不得复活访问。

## 7. 边界

本闸门实现：本地单体中的多主体/多 Space/多 Endpoint 核心与 Web context。以下只冻结
Contract，不在本切片实现：真实 OAuth/OIDC、密码找回、Voice/STT/TTS/wake-word、远程
Store 同步、分布式音频和跨设备冲突合并。它们必须通过独立 Adapter/Capability 闸门接入，
不得进入 Kernel 或 Web UI vendor 分支。

## 8. 退出条件

- 两个 principal 可以在同一 Space 中以不同角色读写，viewer 写入被拒绝；
- Endpoint pairing/revoke 与重启恢复可验证；
- 邀请一次性、过期、撤销和重复接受语义可验证；
- 旧单用户 headers 仍可在明确 local-dev 模式运行；
- 全部 ACL 查询使用 Space membership，不泄露其他 Space 的 Canonical records；
- export/import、restart、Store unavailable、idempotency 和文档同步测试通过。

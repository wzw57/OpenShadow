# Phase 2 第八切片设计闸门：Physical erase 与 Tombstone

状态：**Accepted / Phase 2 第八切片获准实现**

本闸门把前序切片中仅 Contract-only 的 Physical erase 收口为一个受治理、可测试的单记录
擦除操作。它不是跨组件 Erasure orchestrator，也不提供公开 HTTP；只定义 Canonical
Memory/Asset record 的 Adapter 边界、不可逆顺序、Tombstone 和失败语义。

## 已决定内容

### 输入与权限边界

`PhysicalEraseService.erase` 必须接收：

- `principal_ref`、`space_id`、`record_id`、`expected_version`；
- `erasure_ref`、可选 non-sensitive `relation_refs`；
- `idempotency_key` 和 `request_id`。

Service 验证当前 head 存在、Owner/Space 匹配、record_state 为 active 或 logically_deleted，
并拒绝已经 erased 的 head。完整读 ACL 仍延后 Phase 5。

### 不可逆顺序与 Adapter Contract

本切片提供 `ErasureAdapter` 三个窄方法，Adapter 只能操作其声明的 Derived/External 资源：

1. `quiesce`：阻止新的 Recall/Index/Cache/Graph 投影读取；失败则不改 Canonical；
2. `erase`：清除 Adapter 自己的敏感副本、引用和缓存；调用必须幂等，失败返回 unavailable，
   不报告完成；
3. Service 通过现有 `CommitAuthority` 提交 `record_state=erased` 的最小 Tombstone；
4. Canonical Store 成功后物理删除该 record 的旧 version rows，只保留 Tombstone version；
5. `finalize`：Adapter 确认其边界已清除。finalize 或 history purge 失败时返回结构化
   `shadow.erasure.finalize-failed`，不得把操作报告为 completed；同一 idempotency key 可重试。

Deterministic Adapter 只记录调用顺序，不连接 Provider、Secret、Backup 或外部网络。真实
跨组件 Erasure、Backup 清除和异步编排仍是后续 Capability。

### Tombstone 与 anti-resurrection

Tombstone payload 只允许：

```json
{
  "erased": true,
  "erasure_ref": {"record_id": "..."},
  "non_sensitive_relation_refs": []
}
```

旧 typed content、secret、脚本输出、Provider token 和敏感原文不进入 Tombstone；旧 Canonical
version rows 在提交成功后删除。旧 Candidate 的 expected-version、旧 Export、旧 Index、
旧 source event 和 Portable Import 的 active record 都不得重新创建该 stable record。

### Authority、原子性与重放

- Tombstone Commit 使用现有 `CommitAuthority` + `CommitPlan`，operation=`erase`、CAS
  expected-version、target schema=`TombstonePayload`；不新增表、Proposal、Outbox、Job、HTTP。
- 相同 scope/key/request digest replay 返回相同 Tombstone ref、commit/result digest，不重复
  Adapter 副作用；Store unavailable 或 Adapter unavailable 不声称成功。
- 同 key 不同请求返回 `shadow.erasure.replay-conflict`；Owner/Space、not-found、already
  erased、version conflict 和 adapter/finalize failure 均结构化。
- commit 失败时 Adapter 的 erase 结果必须可重试，Canonical 仍不是 erased；commit 成功但
  finalize 失败时 Canonical 已是 Tombstone，结果为 failure，不回滚已完成的擦除。

## 验收证据

- valid/invalid Tombstone schema、敏感字段拒绝和 relation ref 去重；
- Adapter 调用顺序 quiesce → erase → commit → purge → finalize；任一步失败语义；
- active/logically_deleted 成功、already erased/not-found/owner/version conflict；
- replay/replay-conflict 不重复版本或副作用；Store/Adapter unavailable 不伪造成功；
- 旧版本、旧 Candidate、旧 Export/Index 和 Portable active bundle anti-resurrection；
- restart 后只保留 Tombstone head，敏感旧 rows 不可读；
- Documentation Drift 确认无公开 API、数据库表、Backup 清除或跨组件 orchestrator。

## 明确不在本切片

- 跨多个 record 的 Erasure Job、OperationJob、Outbox 和后台队列；
- Provider/Secret vault/Backup/Index/Graph 的真实连接器实现；
- Portable Import full-history、跨设备同步、完整 ACL 和 UI；
- 任何 Tombstone 以外的可逆恢复操作。

## 闸门结论

本闸门已接受，允许创建 `phase2/physical-erase-implementation` 分支。实现、全量验收和
main 合并后，Phase 2 达到当前冻结范围的退出条件。

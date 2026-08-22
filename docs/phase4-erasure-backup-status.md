# Phase 4 跨组件 Erasure / Backup 状态

状态：**设计闸门 Proposed，尚未实现**

当前只提交设计、ADR-0019、Schema 和 fixtures。维护者接受前禁止创建跨组件 Erasure Service、
Backup Service、真实 Adapter、迁移或公开路由。

已冻结：ErasureRequest 的 scope、quiesce 顺序、逐组件状态、失败/恢复/幂等、Tombstone
anti-resurrection；Backup 只保存加密导出 metadata、digest、manifest、opaque key ref、
retention 和 erase schedule，不保存 Secret、Provider 私有状态或可重建索引。

明确不在本切片：真实跨组件删除、加密设备备份内容、密钥托管、Backup restore execution、
通用 Job/Queue、Semantic Pulse、Phase 5 多用户同步。

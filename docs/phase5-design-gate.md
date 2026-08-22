# Phase 5 Multi-endpoint & Multi-user 总体设计闸门

状态：**Proposed / 首个 Endpoint pairing 切片等待接受**

Phase 5 的目标是让同一个 Shadow 安全地被多个 Endpoint 和多个用户继续使用。它不是重写
Tiny Kernel，也不改变现有 `owner_ref`、`space_id`、Proposal/Commit、Admission 或 data
boundary。Phase 5 按独立切片推进，首片只实现 Endpoint pairing / device trust；Space
membership/ACL、Home Space shared state、Remote Store/sync、Voice 和 distributed audio
必须另建设计闸门。

## 总体冻结约束

- Endpoint 是可撤销、可审计的 typed Profile；每个 Endpoint 仍经过 Admission，不能直写 Store
  或绕过 Principal/Space policy。
- 个人资产不因 Endpoint 增加或用户加入而自动变成共享资产；共享 State 必须明确归属于目标
  Space，不能通过 endpoint session 推断所有权。
- Pairing proof、device public key 和 remote Store credentials 只保存 opaque reference，
  不把 Secret、私钥、token 或原始音频写入 Canonical 普通记录。
- 单用户本地部署必须保持简单；远程同步、语音协议和设备协调由可替换 Adapter/Capability
  承担，不进入 Tiny Kernel。

## Phase 5 切片顺序

1. Endpoint pairing / device trust：稳定 Endpoint Profile、撤销、Admission context；
2. Space membership / role / invitation：显式 membership 和 ACL，个人资产默认不共享；
3. Home Space shared state：共享 State 的归属、版本、冲突和删除边界；
4. Remote Store / synchronization profile：可暂停、可恢复、冲突可审计的设备同步；
5. Voice endpoint：STT/TTS/wake-word Adapter，音频内容和协议外置；
6. 只有有真实需求时才评估 distributed audio。

## Phase 5 退出条件

- 同一 Shadow 可从多个 trusted Endpoint 继续，撤销 Endpoint 后不能继续 Admission；
- 共享 State 归正确 Space，不能把个人 Memory 自动升级为共享资产；
- 用户资产仍可导出、迁移和恢复，远程 Store 不成为唯一权威；
- 单用户本地部署不依赖远程服务、语音服务或同步后台。

Phase 5 首片只提交 Endpoint pairing 设计工件；接受前禁止实现业务代码。

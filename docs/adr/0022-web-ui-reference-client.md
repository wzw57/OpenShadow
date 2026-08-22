# ADR-0022：Web UI 作为 Shadow API 参考客户端

- Status: Accepted (initial Conversation slice)
- Date: 2026-08-22
- Deciders: OpenShadow maintainers
- Related: ADR-0001、ADR-0002、ADR-0021

## Context

Shadow 已有可运行的 FastAPI、Conversation、Run/Event 和可替换 Runtime 边界，
但没有用户操作界面。需要一个可以真实运行的单用户 Web UI，同时避免把前端做成
第二套 Application Service、认证系统或 Agent Runtime。

## Decision

建立 `apps/shadow-web` 作为 React + TypeScript + Vite 参考客户端。开发时使用
Vite proxy 连接 Shadow API；生产构建后由 Shadow FastAPI 在 `/ui` 同源提供。
首个切片只实现 Conversation UI 和 Run 状态，不扩展后端领域模型。

浏览器只持有本地 UI 配置和短期页面状态，不持有 Hermes、DeepSeek 或其他 Provider
secret。单用户身份使用服务端约定的 `principal-local` / `space-personal` profile；
多用户认证另立 ADR。

## Consequences

- Web UI 可以切换 Deterministic Adapter 与 Hermes Adapter，而不改变前端契约；
- 同源生产部署降低 CORS、Cookie 和 Secret 泄露风险；
- 首版不显示 token 级流式，直到 Runtime SSE 契约单独完成；
- UI 必须通过 Run/Message API 恢复状态，不能依赖内存状态；
- 后续 Memory、Action、Task 页面仍需各自的契约和设计闸门。

## Rejected alternatives

1. **浏览器直连 Hermes/DeepSeek**：会泄露 Provider 凭据并绕过 Shadow Admission。
2. **前端自建本地数据库和 Agent Loop**：会复制 Canonical Authority 和 Runtime 责任。
3. **首版直接支持多用户认证**：扩大安全和 ACL 范围，不属于当前单用户运行目标。

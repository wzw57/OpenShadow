# Architecture Decision Records

OpenShadow 计划长期运行，而 Runtime、Memory Intelligence、数据库、模型、Provider 和交互技术会持续变化。任何改变 Shadow Core 与可替换组件边界的决定，都必须记录其原因、后果和重新评估条件。

## ADR 格式

文件命名：

~~~text
NNNN-short-title.md
~~~

模板：

~~~md
# ADR-NNNN: Title

- Status: Proposed | Accepted | Superseded | Deprecated
- Date: YYYY-MM-DD
- Owners: ...

## Context

什么问题迫使我们作出这个决定？

## Decision

决定采用什么边界或行为？

## Rationale

为什么采用这个方案？

## Alternatives considered

考虑过哪些方案，为什么没有采用？

## Consequences

正面和负面后果是什么？

## Revisit triggers

什么证据或技术变化会触发重新评估？
~~~

## 已确认、需要正式记录的决策

后续应为以下共识创建独立 ADR：

1. **Shadow 是完整 Agent，Runtime 是 Shadow 内部可替换组件。**
2. **所有请求经过 Shadow，并至少产生最小 Run 记录。**
3. **Shadow Core 只持有 Domain Contract、Authority、Continuity、Extension Control 和 Portability。**
4. **Runtime 持有执行分解，Shadow 持有 Durable Task。**
5. **Runtime Handoff 使用 Semantic Checkpoint，不迁移隐藏推理状态。**
6. **Canonical Memory 属于 Shadow，Memory Intelligence 可以替换。**
7. **数据库引擎通过 Durable Store Port 接入，不定义 Shadow Domain Semantics。**
8. **派生索引、Embedding、Graph、Projection 和 Engine State 可以删除重建。**
9. **外部信息资产默认只登记和按需访问，Shadow 不负责复制和长期存储其原始内容。**
10. **Skill、Extension、Integration 和 MCP Connection 是用户长期能力资产。**
11. **External Component 只能提出 Proposal 或返回 Result，不能绕过 Shadow 提交权威状态。**
12. **具体基础技术优先复用外部项目，通过 Adapter 组合。**
13. **近期实现单用户场景，但稳定 Contract 不封死未来多用户可能。**

## 何时必须新增 ADR

以下变化必须新增或更新 ADR：

- 把某项能力移入或移出 Shadow Core；
- 改变 Canonical Asset 的事实所有权；
- 改变所有请求经过 Shadow 的原则；
- 改变 Runtime、Memory 或 Store 的替换边界；
- 引入不可重建的外部私有状态；
- 改变 Adapter Contract 的兼容性策略；
- 改变用户资产导出和迁移承诺；
- 引入新的权威状态提交者。

## 核心原则

> **Shadow owns the user relationship, assets, continuity and authority.**

> **Replaceable components own intelligence, storage implementation and execution.**

# OpenShadow

**中文版** | [English](README_EN.md)

> **Shadow 是一个可以长期存在、持续升级的个人 AI。**

OpenShadow 是一个本地优先、Runtime 无关的个人 AI 资产与能力平台。用户始终在使用同一个 Shadow；Runtime、Memory Intelligence、数据库、搜索、Skill System、Provider、语音和其他能力都是 Shadow 内部可替换的组成部分。

Shadow 的目标不是重新实现所有 AI 基础设施，而是用尽可能小且稳定的 Core，将外部优秀项目组合成一个能够长期积累和复用用户资产的完整 Agent。

## 产品组成

~~~text
Shadow
├─ Shadow Core
│  ├─ Domain Contracts
│  ├─ Authority & State Transition
│  ├─ Task Continuity
│  ├─ Extension / Integration Registry
│  └─ Portability & Upgrade
│
├─ Replaceable Components
│  ├─ Runtime
│  ├─ Memory Intelligence
│  ├─ Durable Store
│  ├─ Search / Index
│  ├─ Skill System
│  ├─ Capability Providers
│  └─ Voice / User Interfaces
│
└─ User-owned Assets
   ├─ Tasks / Runs / Checkpoints
   ├─ Canonical Memories
   ├─ Skills
   ├─ Extensions / Integrations
   ├─ Asset Catalog
   ├─ Artifacts
   └─ Policies / Action History
~~~

Shadow 是完整产品；Shadow Core 只是其中必须长期稳定的最小内核。

## 核心原则

> **所有请求都经过 Shadow。**

每个请求至少形成一个最小 Run 记录。完整输入、输出和工具过程是否长期保存，由用户策略和产生的长期价值决定。需要跨 Session、Runtime 或时间继续存在的工作才成为 Durable Task。

> **Shadow owns assets, continuity and authority.**

属于用户的长期资产、任务连续性和最终状态不能被某个 Runtime、Memory Engine、数据库私有格式或 Provider 独占。

> **Replaceable components own intelligence and execution.**

推理、规划、Memory 提取与整理、检索、Embedding、Graph、语音、设备协议和具体外部执行优先复用可替换组件。

> **Adapter 是稳定架构的一部分。**

Shadow 自己定义 Port Contract、Adapter SDK、Extension Manifest、权限、版本协商和 Contract Test；具体 Adapter 与外部实现可以持续替换。

## Memory 边界

用户在长期使用中形成的 Canonical Memory 属于 Shadow，必须在更换 Memory Intelligence 后继续存在。

~~~text
Conversation / Task / External Source
                 ↓
       Replaceable Memory Intelligence
                 ↓
          Memory Candidate
                 ↓
       Shadow validates and commits
                 ↓
      Primary Durable Store Adapter
                 ↓
       Replaceable Database Engine
~~~

Shadow Core 持有 Memory 的稳定身份、来源、Scope、版本和提交语义；外部组件负责 Extraction、Consolidation、Retrieval、Reranking、Embedding、Graph 和其他快速演进的智能能力。

数据库引擎也不是 Shadow 自研能力。Shadow 定义 Durable Store Port、Canonical Record、迁移和导出语义，具体数据库通过 Adapter 接入。

## 外部信息资产

Shadow 不负责复制和长期保存用户所有外部资料。

对于 Notion、Obsidian、Drive、Email、文件系统等外部来源，Shadow 默认只在 Asset Catalog 中知道：

- 有什么资产；
- 位于哪里；
- 通过哪个 Integration 访问；
- 当前是否可用；
- 它与哪些 Shadow 资产存在来源关系。

Shadow 在 Task、Recall 或后台 Memory 整理需要时，通过 Connector 按需读取外部内容。外部来源仍负责原始数据的存储和生命周期；由此形成的 Canonical Memory 则由 Shadow 负责长期保存。

## 能力资产

用户长期积累的不只是数据，还包括能力：

~~~text
Capability Assets
├─ Skills
├─ Extensions
├─ Integrations
├─ MCP connections
├─ Provider bindings
├─ Runtime profiles
└─ Configuration / permission metadata
~~~

这些资产应具有稳定身份、版本、来源、配置、权限、兼容性和迁移信息，使用户切换 Runtime 或设备后仍能复用已有能力。

## 当前边界

OpenShadow 不自研数据库、通用 Agent Loop、Memory Intelligence、向量数据库、知识图谱、基础模型、语音引擎、浏览器 Agent、Coding Agent 或设备协议栈。

OpenShadow 必须自行定义和实现：

- Shadow Domain Contracts；
- 权威状态提交边界；
- Task / Run 连续性；
- Adapter SDK 与 Extension Registry；
- Integration / Capability Binding；
- 权限执行点；
- 可移植数据格式；
- 兼容性、迁移和完整性验证；
- 用户控制 API。

近期实现以单用户场景为主，但核心 Contract 不封死未来多用户和多设备可能性。

## 文档

- [需求基线](docs/requirements.md)
- [概要设计](docs/architecture.md)
- [开发路线](docs/roadmap.md)
- [架构决策记录](docs/adr/README.md)

## 当前状态

**需求收紧与 Core / External 责任边界设计阶段。**

当前重点是先冻结完整需求和不可或缺的 Core，再选择具体外部组件和实现技术。

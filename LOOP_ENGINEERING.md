# MyAIDB Loop Engineering 准则

本文档定义 MyAIDB 的 loop engineering 工作方式。它回答“如何循环推进、验证、复盘和沉淀”，不替代 `PRINCIPLES.md` 和 `DEVELOPMENT_PLAN.md`。

## 核心定义

MyAIDB 的一个 loop 以 feature 为单位。每个 feature loop 必须从明确目标开始，以测试通过和学习沉淀结束。

标准 loop 结构：

1. Goal：说明本轮要完成的最小 feature。
2. Scope：说明本轮包含什么、不包含什么。
3. Design：写出最小设计和关键取舍。
4. Implement：实现 feature 内必要代码。
5. Verify：运行测试、示例或检查命令。
6. Diagnose：分类失败原因并修复。
7. Stabilize：确认没有扩大 scope，接口和行为稳定。
8. Persist：把可复用学习沉淀到 `.zero-memory`。

## Loop 粒度

- 默认按 feature 一轮。
- 一个 feature 必须小到可以被测试独立验证。
- 一个 feature 可以跨多个提交，但不能混入无关目标。
- 如果实现中发现 feature 过大，必须拆分为更小 loop，而不是继续膨胀。

合适的 feature 示例：

- 实现 `Value` 和极小类型系统。
- 实现 `CREATE TABLE` 的 parser 和 AST。
- 实现顺序扫描执行器。
- 实现 `vector` 维度校验。
- 实现 fake embedder 任务入队。
- 实现 autoEmbed 状态系统表。

不合适的 feature 示例：

- 一次性完成 SQL 引擎。
- 一次性完成 autoEmbed 全链路。
- 在 parser loop 里顺手实现服务端接口。
- 在 vector loop 里顺手接入 BGE-M3。

## Agent 自主度

在单个 feature loop 内，agent 可以连续实现到测试通过。

允许 agent 自主完成：

- 阅读相关代码和文档。
- 设计本轮最小实现。
- 修改本轮 scope 内文件。
- 添加或调整测试。
- 运行格式化、测试和检查命令。
- 根据失败结果继续修复，直到测试通过或遇到明确 blocker。
- 更新 `.zero-memory` 中的任务上下文和可复用学习。

必须停下来询问用户：

- 需要改变 `PRINCIPLES.md` 的原初准则。
- 需要改变 `DEVELOPMENT_PLAN.md` 的阶段顺序或技术路线。
- 需要引入新的核心依赖、运行时或外部服务。
- 需要扩大 feature scope。
- 需要删除或重写大量已有设计。
- 测试通过但行为语义存在多个合理选择。
- 遇到权限、凭证、网络或外部账户问题。

## 验证标准

每个 feature loop 都必须有验证动作。验证可以是自动测试、命令行示例、静态检查或手工可复现实验，但必须能被下一个 agent 重放。

默认验证顺序：

1. 新增或更新最小测试。
2. 运行与 feature 相关的测试。
3. 运行项目级快速检查。
4. 记录失败和修复。
5. 测试通过后再总结。

测试优先级：

- 语义测试优先于实现细节测试。
- 回归测试优先于临时验证。
- fake embedder 测试优先于真实模型测试。
- 本地确定性测试优先于网络、GPU 或外部服务测试。

当测试无法运行时，必须记录：

- 未运行的命令。
- 未运行原因。
- 已完成的替代验证。
- 下次恢复时的第一步。

## 失败分类

每次失败都必须归类，避免只写“修好了”。

失败类型：

- Spec Gap：原则、计划或 feature 目标不够明确。
- Design Gap：模块边界或数据流设计错误。
- Implementation Bug：代码实现错误。
- Test Gap：测试缺失、测试错误或断言不完整。
- Tooling Gap：工具链、依赖、权限、环境问题。
- Model Gap：embedding 模型、维度、预处理或 provider 行为问题。
- Performance Gap：性能明显阻塞下一轮，但尚不追求极致优化。

失败处理原则：

- Spec Gap 先对齐再实现。
- Design Gap 先收窄设计再改代码。
- Implementation Bug 可以在本 loop 内连续修复。
- Test Gap 必须补测试或修正测试。
- Tooling Gap 必须记录可复现环境信息。
- Model Gap 不得污染数据库内核语义。

## 学习沉淀

学习沉淀写入 `.zero-memory`，不额外维护 `EXPERIMENTS.md`。

每个 feature loop 至少更新：

- `.zero-memory/context/<task>/context.md`：记录本轮目标、当前状态、关键决定、验证结果、下一步。

当出现可复用学习时，追加到：

- `.zero-memory/daily/learning.YYYY-MM-DD.md`

可复用学习包括：

- 会影响后续 feature 的设计取舍。
- 重复出现的失败模式。
- 调试方法。
- 查询语义边界。
- autoEmbed 状态机经验。
- Rust 类型或模块边界经验。
- 模型 provider 集成注意事项。

不需要沉淀的内容：

- 一次性命令输出。
- 临时日志。
- 明显拼写修复。
- 不会影响后续工作的局部实现细节。

## Done Definition

一个 feature loop 只有同时满足以下条件，才算完成：

- 本轮目标已经实现。
- scope 没有悄悄扩大。
- 相关测试或替代验证已经完成。
- 失败原因已分类并解决，或 blocker 已清楚记录。
- 用户可理解本轮完成了什么。
- `.zero-memory` 已记录可恢复上下文。
- 如有可复用学习，已写入 `.zero-memory/daily/`。

## MyAIDB 特别规则

- 任何 loop 都必须服从 `PRINCIPLES.md`。
- 任何实现顺序都必须默认服从 `DEVELOPMENT_PLAN.md`。
- 在 autoEmbed 相关 loop 中，表数据和 embedding 派生状态的边界必须显式验证。
- 在查询相关 loop 中，SQL 精确语义和语义检索体验的冲突必须显式说明。
- 真实模型接入不得阻塞 fake embedder 驱动的内核测试。
- 不得为了让测试通过而隐藏 `pending`、`ready`、`stale`、`error` 状态。

## Loop 模板

每次开始 feature loop 时，使用以下模板思考和记录：

```text
Feature:
Goal:
Scope:
Out of Scope:
Design:
Verification:
Expected Artifacts:
Done Definition:
```

每次结束 feature loop 时，使用以下模板沉淀：

```text
Feature:
Completed:
Tests:
Failures:
Fixes:
Reusable Learning:
Next Loop:
```

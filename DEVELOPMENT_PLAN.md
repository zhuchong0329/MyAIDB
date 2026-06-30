# MyAIDB 开发计划

本文档记录 MyAIDB 第一阶段的实现计划。它必须服从 `PRINCIPLES.md` 中的原初准则：教学内核优先、本地服务优先、内存优先、autoEmbed 作为声明式异步派生索引。

## 总体建议

- 编程语言：Rust。
- 第一阶段运行形态：Rust 本地服务，配合简单 CLI 或 HTTP/JSON 接口。
- 第一阶段 embedding 策略：先使用 deterministic fake embedder 验证数据库语义，再接入 BGE-M3 作为真实本地参考模型。
- 第一阶段向量检索：先使用 brute-force 扫描，不做 HNSW、IVF、DiskANN 等近似向量索引。
- 模型运行边界：真实模型不嵌入数据库内核进程，而是通过本地 provider 接口调用。

## 分层开发顺序

1. 内核基础层
   - 实现 `Value`、`Row`、`Schema`、`Table`、`Catalog`。
   - 只支持内存表和极小类型集：`integer`、`real`、`text`、`blob`、`null`、`vector`。
   - 暂不引入 embedding、模型、语义索引。

2. SQL 前端层
   - 实现 tokenizer、parser、AST、binder。
   - 支持最小 SQL 子集：`CREATE TABLE`、`INSERT`、`SELECT`、`WHERE`、`ORDER BY`、`LIMIT`。
   - 以 SQLite 子集作为心智基线，但不承诺完整 SQLite 兼容。

3. 执行器层
   - 实现顺序扫描、过滤、投影、排序、限制行数。
   - 先不做复杂优化器。
   - 可保留透明的 logical plan，便于教学和调试。

4. 本地服务层
   - 暴露一个朴素 SQL 执行入口。
   - 优先选择 HTTP/JSON 或 CLI。
   - 不设计复杂 wire protocol。

5. Vector 基础层
   - 增加 `vector` 类型。
   - 实现维度校验。
   - 实现 cosine、dot、l2 距离函数。
   - 第一版使用全表扫描完成向量检索，保证语义清楚。

6. 模型登记层
   - 建立 model registry。
   - 只记录模型元数据：模型名、版本、维度、归一化策略、预处理规则、provider 类型。
   - 数据库不负责下载、升级、托管模型文件。

7. autoEmbed 任务层
   - 支持声明式 autoEmbed 索引。
   - 表数据写入后生成异步 embedding 任务。
   - 系统表或系统视图必须暴露 `pending`、`ready`、`stale`、`error` 状态。
   - 失败原因、模型版本、重建进度必须可观察。

8. 语义查询层
   - 增加 `SEMANTIC_MATCH(...)` 或等价的一等 SQL 表达式。
   - 语义查询接入 SQL 主干，而不是独立搜索 DSL。
   - 查询默认只使用 `ready` 的 embedding。
   - 缺失、过期、失败状态必须显式暴露。

9. 真实本地模型适配层
   - 在数据库核心稳定后，再接入真实 embedding provider。
   - 第一真实参考模型选择 BGE-M3。
   - 默认使用 dense-only 模式、小 batch、受控 `max_length`。

## 编程语言选择

Rust 是第一阶段推荐语言。

选择 Rust 的原因：

- 适合表达数据库内核中的 AST、类型系统、执行计划和错误处理。
- 所有权模型有助于保持内存数据结构边界清晰。
- 并发任务队列和异步服务生态成熟。
- 比 C++ 更适合教学项目保持结构可读。
- 比 Python 更适合长期演进为数据库内核。

模型推理不应一开始塞进 Rust 内核。推荐架构是 Rust 数据库核心加本地 embedding provider 接口；真实模型可先由 Python、ONNX Runtime 或独立本地服务承载。

## 模型选择

第一阶段应区分测试模型和真实参考模型。

测试模型：

- 使用 deterministic fake embedder。
- 同一文本永远生成同一向量。
- 不依赖网络、GPU、Python 环境或真实模型文件。
- 用于验证事务边界、任务队列、索引状态、SQL 语义和测试稳定性。

真实参考模型：

- 推荐 BGE-M3。
- BGE-M3 适合中文和多语言场景。
- BGE-M3 输出 1024 维向量，支持长文本和多种检索形态。
- BGE-M3 模型权重约 2.27GB，参数量约 568M。

备选模型：

- `all-MiniLM-L6-v2`：体积小，384 维，适合 smoke test，但中文默认性较弱。
- `nomic-embed-text-v1.5`：768 维，支持长文本和降维，英文和长文本体验较好，但中文默认性不如 BGE-M3 明确。

## BGE-M3 本地运行边界

BGE-M3 可以在 16GB 内存的 Mac 笔记本上运行，但不算轻量。

建议约束：

- 适合本地开发、单条或小 batch embedding。
- 默认将 `max_length` 控制在 512 或 1024。
- 不建议第一阶段启用 8192 token 长文本和大 batch。
- 不建议将 BGE-M3 直接嵌入数据库内核进程。
- 推荐通过本地 HTTP、IPC 或等价 provider 接口调用。

粗略资源估算：

- FP32 模型权重约 2.3GB。
- FP16 或量化后可能降到约 1GB 或更低，取决于运行方式。
- Python、PyTorch、Transformers 等运行时通常还会额外占用数 GB 内存。
- 1024 维 `f32` 向量每条约 4KB；100 万条向量约 4GB，不含行数据和索引开销。

## 第一阶段验收目标

- 能用 Rust 启动本地 MyAIDB 服务或 CLI。
- 能创建内存表、插入数据、执行基础 SQL 查询。
- 能使用极小类型系统并对错误类型显式失败。
- 能存储和计算 `vector` 值。
- 能登记模型元数据。
- 能声明 autoEmbed 索引。
- 写入文本数据后能产生异步 embedding 任务。
- 系统表或系统视图能观察 autoEmbed 状态。
- fake embedder 能稳定驱动语义查询测试。
- BGE-M3 作为外部本地 provider 的接入点明确，但不阻塞核心内核开发。

## 非目标

- 不实现分布式、复制、分片或高可用。
- 不追求完整 SQLite 或 PostgreSQL 兼容。
- 不实现生产级持久化、WAL、checkpoint 或崩溃恢复。
- 不在第一阶段实现 HNSW 等近似向量索引。
- 不让真实模型推理复杂度污染数据库核心结构。

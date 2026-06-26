# QuantLab Research OS 全面升级设计（Spec）

> **项目代号**：Research OS Upgrade（研究操作系统升级）
> **创建日期**：2026-06-26
> **状态**：📋 设计已确认（待 writing-plans 生成实施计划）
> **依据文档**：`docs/alpha体系升级.md`（7140 行）
> **核心理念**：从"Feature 列表"升级为"Research Graph"；ResearchNode 成为整个 QuantLab 唯一的数据计算语言

---

## 〇、背景与现状诊断

### 0.1 文档升级目标

`docs/alpha体系升级.md` 提出将 ML Lab 从"时序模型训练平台"升级为"AI-driven Quant Research Platform"，核心变化是**从"Feature 列表"升级到"Research Graph"**，涉及 10+ 子系统：

1. ResearchNode 抽象（统一计算单元）
2. Research Graph（DAG）
3. Research Executor（拓扑排序/缓存检查/执行）
4. ResearchFrame（(datetime,symbol) MultiIndex 统一数据标准）
5. Node Manifest / Node Registry
6. 5 级 Cache（Memory/Parquet/FeatureStore/Artifact/Redis）+ Dependency Invalidation + Cache Planner
7. Incremental Framework（ChangeSet/Delta Analyzer/Planner/State Store）
8. Dataset 升级（calendar/adjustment/dataset_type）+ Universe/Calendar Registry
9. Materializer + TrainingDatasetBuilder
10. 上层全迁移（training/feature_analysis/diagnostics/label/api/frontend）
11. 前端 Research Graph Studio（Visual Quant Research IDE）
12. DB Schema 变更 + 回滚机制

### 0.2 现有体系现状（实地核查）

| 模块 | 路径 | 现状 | 与文档目标差距 |
|------|------|------|---------------|
| ML Feature | `quantlab/ml/feature/` | `Feature.compute(df)->pd.Series`，单标的时序模式；`FeatureRegistry`+`FeatureSetRegistry` | 正是文档要升级的"Feature 列表"模式，需替换为 ResearchNode |
| Factor | `quantlab/factor/` | `FactorInfo.fn(ctx)->pd.DataFrame`（date×symbol 面板）；`FactorRegistry` 单例 | 另一套并行体系，与 ML Feature 接口不统一，需统一为 ResearchNode |
| Dataset | `quantlab/ml/dataset/dataset.py` | 已有 scope_type/universe_id/symbols/frequency/asset_type/storage_format | 缺 calendar/adjustment/dataset_type；Universe/Calendar Registry 未独立 |
| Training | `quantlab/ml/training/job.py` | `TrainingJob` 直接吃 dataset_id+feature_set_id+label_set_id，调用 FeatureRegistry/LabelRegistry 计算 | 无 Materializer 中间层，未走 Graph |
| Storage | `quantlab/ml/storage.py` | SQLite 表：datasets/feature_sets/label_sets/training_jobs/models | 需新增 research_* 表 + ALTER 现有表 |
| Label | `quantlab/ml/label/` | `LabelRegistry`+`LabelSetRegistry` | 需迁移为 LabelNode |
| Feature Analysis | `quantlab/ml/feature_analysis/` | 基于 FeatureSet | 需改读 Graph 产物 |
| Diagnostics | `quantlab/ml/diagnostics/` | feature/label 诊断 | 需用 Node 元数据 |
| API | `quantlab/api/ml.py`, `api/factors.py` | 暴露旧接口 | 需暴露 Graph/Materializer 接口 |
| Frontend | `frontend/src/views/ml_lab/`, `views/factors/` | FeatureLab/FeatureSets/FactorStudio | 需新增 Research Graph Studio，旧页面 deprecated |

**关键发现**：`ml/feature/Feature` 与 `factor/FactorInfo` 是两套并行体系，接口不统一（compute(df)->Series vs fn(ctx)->DataFrame），正是文档要解决的核心问题之一。

### 0.3 升级目标

1. 建立 ResearchNode 统一抽象，替代 Feature + FactorInfo 两套体系
2. 构建 Research Graph (DAG) + Executor，实现"Feature 列表 → DAG"范式转变
3. 统一数据标准 ResearchFrame ((datetime,symbol) MultiIndex)
4. 实现 5 级 Cache + Dependency Invalidation + Cache Planner
5. 实现 Incremental Framework，增量成为默认执行模式
6. Dataset 升级 + Universe/Calendar Registry + Materializer
7. 上层全迁移（training/feature_analysis/diagnostics/label/api/frontend）
8. 前端 Research Graph Studio
9. DB Schema 变更 + 完善回滚机制 + 充分测试

---

## 一、关键决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| MVP 边界 | **全量**（含 Incremental + 前端 Studio） | 用户明确要求全面升级 |
| 兼容策略 | **全新替换**（旧 Feature/FactorInfo 废弃） | 最干净，避免永久分裂 |
| 替换作用域 | **底层 + 上层全迁移** | 一次性消除旧接口 |
| 交付方案 | **方案 B**（一次性全量） | 用户选择；通过回滚机制+测试对冲风险 |
| DB 处理 | **直接修改 DB 结构**（非代码迁移） | 符合用户偏好，新增表 + ALTER 现有表 |
| 数据标准 | **ResearchFrame: (datetime,symbol) MultiIndex**，Panel 为默认 | 文档建议，可退化为时序/横截面 |
| Node 接口 | **能力接口（capability interface）**，非继承树 | 文档第二十三节明确建议 |
| 回滚 | Git 分支 + DB 备份 + Feature Flag + 兼容层 | 用户明确要求"完善回滚机制" |

---

## 二、架构总览（第 1 节）

### 2.1 目标架构（分层）

```
QuantLab Research OS
├── 1. Research Assets (研究资产层)
│   ├── Node Registry        ← 替代 FeatureRegistry + FactorRegistry
│   ├── Dataset Registry     ← 升级: +calendar/adjustment/dataset_type
│   ├── Universe Registry    ← 新增
│   ├── Calendar Registry    ← 新增
│   └── Benchmark Registry
├── 2. Research Graph (研究图层 — 内核)
│   ├── ResearchNode         ← 统一计算单元 (替代 Feature/FactorInfo)
│   ├── ResearchFrame        ← (datetime,symbol) MultiIndex 统一数据标准
│   ├── ResearchGraph (DAG)
│   └── ResearchExecutor     ← 拓扑排序/缓存检查/执行
├── 3. Cache Manager (5 级)
│   └── Memory → Parquet → FeatureStore(ResearchAsset) → Artifact → Redis
│   + Dependency Invalidation + Cache Planner
├── 4. Incremental Framework
│   └── ChangeSet → Delta Analyzer → Planner → State Store
├── 5. Training Center (改造)
│   └── Materializer + TrainingDatasetBuilder + TrainingJob(改吃Graph) + Validation
├── 6. Frontend
│   └── Research Graph Studio (Node Palette/Canvas/Inspector/Execution/Cache View)
└── 7. Storage (DB schema 变更 + 回滚)
```

### 2.2 新增模块文件结构

统一在 `quantlab/research/` 下，旧 `ml/feature`、`factor/` 全部迁入并废弃：

```
quantlab/research/
├── node/
│   ├── base.py            # ResearchNode 基类 (能力接口)
│   ├── ports.py           # Port (输入输出声明)
│   ├── manifest.py        # NodeManifest (id/version/inputs/outputs/params)
│   ├── registry.py        # NodeRegistry (替代 FeatureRegistry+FactorRegistry)
│   └── builtin/
│       ├── data.py        # DataNode (Close/High/Low/Open/Volume/VWAP)
│       ├── transform.py   # TransformNode (Return/ZScore/Log/Diff/Normalize)
│       ├── indicator.py   # IndicatorNode (RSI/ATR/MACD/EMA/SMA)
│       ├── alpha.py       # AlphaNode (Alpha001-101, Alpha001-191)
│       ├── aggregation.py # AggregationNode (RollingMean/Std/Max/Min)
│       ├── ranking.py     # RankingNode (CrossSectionRank/Percentile/TopN)
│       ├── selection.py    # SelectionNode (UniverseFilter/LiquidityFilter)
│       ├── label.py       # LabelNode (FutureReturn/TripleBarrier/Direction)
│       └── custom.py
├── frame.py               # ResearchFrame ((datetime,symbol) MultiIndex)
├── graph.py               # ResearchGraph (DAG)
├── executor.py            # ResearchExecutor (编译/拓扑/缓存/执行)
├── cache/
│   ├── manager.py         # CacheManager (L1-L5)
│   ├── memory.py / parquet.py / feature_store.py / artifact.py / redis.py
│   ├── invalidator.py     # 依赖失效传播
│   └── planner.py         # Cache Planner
├── incremental/
│   ├── changeset.py / delta_analyzer.py / planner.py / state_store.py
├── materializer.py        # TrainingDatasetBuilder + Materializer
├── universe.py / calendar.py
└── storage.py             # Research Store (新 DB 表)
```

### 2.3 关键设计原则

- ResearchNode 采用**能力接口**（capability interface），非复杂继承树
- ResearchFrame 是 Node 间唯一数据契约（输入输出都是 ResearchFrame）
- 旧 `ml/feature/Feature.compute(df)->Series` 与 `factor/FactorInfo.fn(ctx)->DataFrame` 全部重写为 `ResearchNode.compute(context)->ResearchFrame`
- DB 旧表（feature_sets/label_sets）保留并标记 `_deprecated`，新增 research_* 表，回滚时可切回

---

## 三、ResearchNode 抽象与 ResearchFrame（第 2 节）

### 3.1 ResearchNode 基类（能力接口）

```python
class ResearchNode:
    """所有研究节点的统一抽象 — Atomic Research Unit"""

    # 身份
    id: str                          # "rsi14", "alpha017"
    version: str                     # "1.0.0"
    category: NodeCategory           # data/transform/indicator/alpha/label/ranking/...

    # 输入输出声明 (Port)
    inputs: list[Port]               # [{"name":"close","type":"series","required":True}]
    outputs: list[Port]              # [{"name":"rsi","type":"series"}]

    # 参数与元信息
    parameters: dict                 # {"window":14}
    metadata: NodeMetadata           # cost/description/author/deprecated

    # 生命周期方法
    def validate(self, schema) -> bool: ...      # 校验输入 schema
    def fingerprint(self) -> str: ...             # 内容哈希 (用于缓存)
    def estimate_cost(self) -> CostEstimate: ...  # ★★★☆☆ + 时间复杂度
    def describe(self) -> NodeDescription: ...    # 人可读描述

    # 核心计算
    def compute(self, ctx: ExecutionContext) -> ResearchFrame: ...

    # 能力声明 (可选能力，非必填)
    def supports_incremental(self) -> bool: ...   # 是否支持增量
    def supports_parallel(self) -> bool: ...      # 是否可并行
    def supports_gpu(self) -> bool: ...           # 是否可用GPU
    def cache_policy(self) -> CachePolicy: ...    # 缓存策略

    # 增量能力 (supports_incremental=True 时实现)
    def update(self, ctx, changeset) -> ResearchFrame: ...
    def save_state(self, store) -> None: ...
    def load_state(self, store) -> None: ...
    def invalidate(self, dirty_range) -> None: ...
    def estimate_delta(self, changeset) -> Delta: ...
```

### 3.2 Port（输入输出声明）

```python
@dataclass
class Port:
    name: str                    # "close" / "rsi"
    type: PortType               # series / frame / scalar / panel
    required: bool = True
    description: str = ""
```

### 3.3 ResearchFrame（统一数据标准）

```python
@dataclass
class ResearchFrame:
    """
    统一数据契约 — Panel 为默认，可退化为时序/横截面

    index: MultiIndex (datetime, symbol)
    columns: close, high, low, open, volume, rsi, alpha017, ...
    """
    data: pd.DataFrame            # MultiIndex (datetime, symbol)
    columns_meta: dict            # 每列的 role/dtype/unit

    # 退化模式
    def as_time_series(self, symbol: str) -> pd.DataFrame: ...  # 单标的
    def as_cross_section(self, dt) -> pd.DataFrame: ...         # 单日横截面

    @classmethod
    def from_ohlcv(cls, df: pd.DataFrame) -> "ResearchFrame": ...
    @classmethod
    def from_single_symbol(cls, df: pd.DataFrame, symbol: str) -> "ResearchFrame": ...
```

### 3.4 Node 分类（统一 Registry，替代两套体系）

| 类别 | 职责 | 现有映射 | 示例 |
|------|------|---------|------|
| DataNode | 读取原始数据 | (新增) | Close/High/Low/Open/Volume/VWAP |
| TransformNode | 数据变换 | factor/operators | Return/ZScore/Log/Diff/Normalize |
| IndicatorNode | 技术指标 | ml/feature/builtin RSI/ATR | RSI/ATR/MACD/EMA/SMA |
| AlphaNode | Alpha 因子 | factor/alpha191, alpha101 | Alpha001-191, Alpha001-101 |
| AggregationNode | 聚合 | factor/operators | RollingMean/Std/Max/Min |
| RankingNode | 截面排名 | (新增) | CrossSectionRank/Percentile/TopN |
| SelectionNode | 标的筛选 | (新增) | UniverseFilter/LiquidityFilter |
| LabelNode | 标签 | ml/label/builtin | FutureReturn/TripleBarrier/Direction |
| CustomNode | 自定义 | (新增) | 用户扩展 |

### 3.5 Node 生命周期

Created → Validated → Compiled → Executed → Cached → Expired

（Training 不在其中，Training 是 Graph 的事）

### 3.6 迁移映射（全新替换具体落地）

- `ml/feature/builtin.py:RSI14` → `research/node/builtin/indicator.py:RSINode(window=14)`
- `factor/alpha191/alpha_014.py:alpha_014(ctx)` → `research/node/builtin/alpha.py:Alpha014Node()`
- `factor/operators/ts.py:delay/delta/corr` → `research/node/builtin/transform.py` 算子 Node + 保留纯函数供 Node 内部调用
- `ml/label/builtin.py:FutureReturn` → `research/node/builtin/label.py:FutureReturnNode(horizon=5)`

---

## 四、ResearchGraph (DAG) + Executor（第 3 节）

### 4.1 ResearchGraph

```python
class ResearchGraph:
    """
    研究图 — Node 的有向无环连接

    构建: graph.add_node(node).add_edge(src_node, dst_node, port_map)
    编译: compiled = graph.compile()   # 校验无环、端口匹配、类型推断
    执行: result = executor.execute(compiled, dataset_ctx)
    """
    nodes: dict[str, ResearchNode]
    edges: list[Edge]
    name: str
    version: str

    def add_node(self, node) -> "ResearchGraph": ...
    def add_edge(self, src, src_port, dst, dst_port) -> "ResearchGraph": ...
    def compile(self) -> "CompiledGraph": ...
    def to_dag_view(self) -> dict: ...
    def fingerprint(self) -> str: ...
```

### 4.2 Edge

```python
@dataclass
class Edge:
    src_node: str; src_port: str
    dst_node: str; dst_port: str
```

### 4.3 CompiledGraph

```python
@dataclass
class CompiledGraph:
    topo_order: list[str]           # 拓扑序 node_id 列表
    nodes: dict[str, ResearchNode]
    execution_plan: ExecutionPlan   # 并行分组 (同层无依赖可并行)
    cache_plan: CachePlan           # 由 Cache Planner 生成
    fingerprint: str
```

### 4.4 ResearchExecutor

```python
class ResearchExecutor:
    """
    流程: 接收 CompiledGraph
          → 遍历 topo_order
          → 每个 Node: Cache Check (fingerprint) → Hit? 跳过 : compute() → Write Cache
          → 传递 ResearchFrame 给下游
          → 支持并行执行 (execution_plan)
          → 支持增量模式 (与 Incremental Framework 衔接)
    """
    def execute(
        self,
        graph: CompiledGraph,
        dataset_ctx: DatasetContext,
        mode: str = "full",        # full / incremental
        changeset: ChangeSet | None = None,
    ) -> dict[str, ResearchFrame]: ...
```

### 4.5 ExecutionContext

```python
@dataclass
class ExecutionContext:
    dataset_ctx: DatasetContext     # 提供原始数据访问 (close/high/...)
    cache: CacheManager              # 节点可主动读写缓存
    frame_store: FrameStore          # 上游 Node 产出的 ResearchFrame
    config: dict
    logger: logging.Logger
```

Node 的 `compute(ctx)` 通过 `ctx.frame_store.get(upstream_port)` 拿上游输出，通过 `ctx.dataset_ctx.get_column("close")` 拿原始数据。

### 4.6 示例：Alpha017 Graph

```
DataNode(close) ─┬─→ TransformNode(return) ─→ AggregationNode(rolling_std,20)
                  │                                    │
                  └─→ TransformNode(delay,1)            ▼
                              │              RankingNode(cross_section_rank)
                              ▼                        │
                      AggregationNode(ts_corr,5)       │
                                       │                ▼
                                       └──→ Alpha017Node ◄─┘
                                                    │
                                                    ▼
                                          [输出: alpha017 ResearchFrame]
```

Executor 按拓扑序执行，`return`/`delay` 只算一次，Alpha017 自动复用缓存。

### 4.7 与 Incremental Framework 衔接

Executor 接收 `mode="incremental"` + `changeset` 时，委托给 Incremental Planner 生成 dirty subgraph，只重算脏节点（详见第六节）。

---

## 五、Node Manifest/Registry + 5 级 Cache + 失效传播（第 4 节）

### 5.1 NodeManifest

```python
@dataclass
class NodeManifest:
    id: str                      # "rsi14"
    version: str                 # "1.0.0"
    category: NodeCategory
    inputs: list[Port]
    outputs: list[Port]
    params: dict
    metadata: NodeMetadata       # cost/description/author/deprecated
    fingerprint_basis: str
    deprecated: bool = False
```

每个 Node 实例生成 manifest，可持久化、可对比版本。RSI@1.0.0 与 RSI@2.0.0 可并存。

### 5.2 NodeRegistry（统一注册表，替代 FeatureRegistry + FactorRegistry）

```python
class NodeRegistry:
    """线程安全，按 id+version 注册 Node 工厂"""
    def register(self, manifest: NodeManifest, factory: Callable) -> str: ...
    def get(self, node_id: str, version: str = "latest") -> tuple[NodeManifest, Callable]: ...
    def list(self, category=None, tag=None) -> list[NodeManifest]: ...
    def list_categories(self) -> list[str]: ...
    def load_from_store(self) -> int: ...
```

启动时自动注册所有 builtin 节点。旧 `get_feature_registry()` 和 `get_registry()`(Factor) 废弃，提供兼容入口指向 NodeRegistry。

### 5.3 5 级 Cache 架构

```
CacheManager
├── L1 Execution Cache (内存)      ← 一次 Graph 执行内避免重复计算 (Return 只算一次)
│   ├── MemoryCache (dict)
│   └── WindowCache (滚动窗口)
├── L2 Persistent Cache (磁盘)
│   ├── ParquetCache
│   ├── ArrowCache / FeatherCache
├── L3 Research Asset Store (长期) ← 研究成果沉淀，跨 Graph/ML/Strategy/Backtest 共享
│   ├── FeatureStore
│   ├── FactorStore
│   └── MaterializedFeature
├── L4 Object Store (产物)
│   ├── Artifacts (SHAP/Importance/Distribution/Statistics)
│   ├── Snapshots / Packages
└── L5 Remote Cache
    └── Redis
```

### 5.4 两种 Cache 的本质区分

- **Execution Cache (L1)**：生命周期=一次 Graph 执行，目的=避免重复计算
- **Research Asset Cache (L3)**：生命周期=长期，目的=研究成果沉淀。Alpha101 算好后自动升级为 Research Asset，ML/Strategy/Observe/Backtest 全部共享读取，不再重算

### 5.5 Cache Manifest

```python
@dataclass
class CacheManifest:
    cache_id: str
    node_id: str
    dataset_id: str
    range: tuple[str, str]
    version: str
    dependencies: list[str]
    created_at: str
    size: int
    ttl: str                     # "never" / "1d"
    level: CacheLevel            # L1/L2/L3/L4/L5
```

### 5.6 Dependency Invalidation（事件驱动失效传播）

```
Dataset Updated (Close 变了)
    ↓ Invalidate Event
    Close Node
    ↓ 依赖传播
    Return → EMA → MACD
    ↓
    Alpha017
（ATR 若不用 Close，不失效）
```

`Invalidator` 维护 Node 依赖图的反向索引，收到 Dataset/Universe/版本变更事件时，只失效受影响子图。

### 5.7 Cache Planner

CompiledGraph 编译后，Cache Planner 根据每个 Node 的 `cache_policy()` + `estimate_cost()` 自动决定：
- 哪些进 L1 Memory（廉价、频繁复用）
- 哪些进 L2 Parquet（昂贵、跨执行复用）
- 哪些进 L3 Research Asset（高价值、长期沉淀）

Executor 只管执行，缓存决策由 Planner 静态生成。

---

## 六、Dataset 升级 + Universe/Calendar + Materializer + 训练闭环（第 5 节）

### 6.1 Dataset 升级（新增字段）

```python
@dataclass
class Dataset:
    # 现有字段保留
    dataset_id, name, symbols, start_date, end_date, frequency, ...

    # 新增
    dataset_type: str = "panel"      # time_series / cross_section / panel (默认 panel)
    universe_id: str = ""            # 引用 Universe (与 symbols 二选一)
    calendar_id: str = ""             # 引用 Calendar (crypto/a_share/us_stock)
    adjustment: str = "none"         # none / forward / backward (复权)
    storage: str = "parquet"         # parquet / arrow / memory
```

`dataset_type=panel` 为默认，可退化为时序/横截面。

### 6.2 Universe Registry

```python
class UniverseRegistry:
    """标的池定义，决定训练哪些标的"""
    def register(self, universe_id, definition: UniverseDefinition) -> None: ...
    def resolve(self, universe_id, at_date=None) -> list[str]: ...
    def list_all(self) -> list[UniverseDefinition]: ...

@dataclass
class UniverseDefinition:
    universe_id: str
    members: list[str] | None        # 静态成员
    rule: dict | None                 # 动态规则 (如 top_n_by_volume)
    rebalance: str                    # daily/monthly/quarterly
```

### 6.3 Calendar Registry

```python
class CalendarRegistry:
    """交易日历 — Crypto(7x24) / A股交易日 / NYSE"""
    def register(self, calendar_id, sessions: pd.DatetimeIndex) -> None: ...
    def get_sessions(self, calendar_id, start, end) -> pd.DatetimeIndex: ...
    def is_trading_day(self, calendar_id, dt) -> bool: ...
```

内置：`crypto`(7x24)、`a_share`(A股交易日)、`nyse`(美股)。

### 6.4 Materializer（核心新增 — 训练不再直接吃 Dataset）

文档第八层：`Dataset → Research Graph → Feature Graph → Materializer → Training Dataset`

```python
class Materializer:
    """
    数据实体化 — 真正生成 X, y

    职责: Join / Align / Normalize / Filter / Window / Split
    输入: CompiledGraph + Dataset + LabelNode + split_config
    输出: TrainingDataset (X_train, y_train, X_test, y_test)
    """
    def materialize(
        self,
        graph: CompiledGraph,
        dataset: Dataset,
        label_node: ResearchNode,
        split: SplitConfig,
        normalize: NormalizeConfig | None = None,
        window: int | None = None,
    ) -> TrainingDataset: ...

@dataclass
class TrainingDataset:
    X_train: pd.DataFrame; y_train: pd.Series
    X_test: pd.DataFrame; y_test: pd.Series
    feature_names: list[str]
    split_meta: dict
```

### 6.5 训练流程改造对比

```
旧: TrainingJob → Dataset → FeatureRegistry.compute → X,y → Model
新: TrainingJob → Materializer.execute(CompiledGraph, Dataset, LabelNode) → TrainingDataset → Model
```

TrainingJob 字段变更：
- 删除：`feature_set_id` / `label_set_id` / `feature_ids` / `label_id`
- 新增：`research_graph_id` / `label_node_id` / `materialize_config`

### 6.6 训练闭环迁移范围（本次全量迁移）

- `ml/training/job.py` TrainingJob → 改用 Materializer
- `ml/feature_analysis/` → 改读 Graph 产物 + MaterializedFeature
- `ml/diagnostics/` (feature/label) → 改用 Node 元数据
- `ml/label/` → LabelNode 注册到 NodeRegistry
- `api/ml.py` → 暴露 Graph/Materializer 接口
- `api/factors.py` → 改为 NodeRegistry 查询

### 6.7 兼容层（回滚用，标记 deprecated）

保留 `get_feature_registry()`/`get_feature_set_registry()`/`get_registry()`(Factor) 旧入口，内部转发到 NodeRegistry，下次发版删除。

---

## 七、Incremental Framework（第 6 节）

文档核心主张：**Incremental 不应是性能优化，而应成为 Research Graph 的默认执行模式**。

### 7.1 ChangeSet（变更集 — 系统唯一输入）

```python
@dataclass
class ChangeSet:
    """系统接收的输入永远是 ChangeSet，不是新 DataFrame"""
    dataset_id: str
    changes: list[Change]

@dataclass
class Change:
    op: ChangeOp           # APPEND / UPDATE / DELETE
    symbol: str
    datetime: str
    payload: dict | None
```

### 7.2 Delta Analyzer

```python
class DeltaAnalyzer:
    """ChangeSet → DirtyRange → DirtyPartition → DirtyNode"""
    def analyze(self, changeset: ChangeSet, graph: CompiledGraph) -> DirtyGraph: ...

@dataclass
class DirtyGraph:
    dirty_ranges: dict[str, list[TimeRange]]    # node_id → 脏时间区间
    dirty_nodes: list[str]
    dirty_partitions: dict[str, list[str]]
```

### 7.3 Incremental Planner（增量策略选择）

```python
class IncrementalPlanner:
    """为每个脏 Node 选择最优增量策略"""
    def plan(self, dirty: DirtyGraph, nodes: dict[str, ResearchNode]) -> IncrementalPlan: ...

class IncrementalStrategy(Enum):
    APPEND_ONLY         = "append_only"
    ROLLING_WINDOW      = "rolling_window"
    PARTITION_RECOMPUTE = "partition_recompute"
    DEPENDENCY_RECOMPUTE= "dependency_recompute"
    STATEFUL            = "stateful"
    FULL_RECOMPUTE      = "full_recompute"
```

Planner 根据 Node 的 `supports_incremental()` + 变更类型自动选择：
- 追加 1 根 K 线 → APPEND_ONLY
- 历史数据修正 → ROLLING_WINDOW / PARTITION_RECOMPUTE
- Node 不支持增量 / 版本失效 / 结构性变化 → FULL_RECOMPUTE（自动退化）

### 7.4 State Store

```python
class StateStore:
    """保存有状态 Node (EMA/Kalman/Rolling) 的计算状态"""
    def save(self, node_id, state: NodeState) -> None: ...
    def load(self, node_id) -> NodeState | None: ...
    def checkpoint(self, graph_id, at_datetime) -> str: ...

@dataclass
class NodeState:
    node_id: str
    state: dict              # EMA 的 last_value, Kalman 的协方差矩阵等
    checkpoint_at: str
    fingerprint: str
```

### 7.5 ResearchNode 增量能力升级

```python
class ResearchNode:
    def compute(self, ctx) -> ResearchFrame: ...      # 全量
    def update(self, ctx, changeset) -> ResearchFrame: ...  # 增量
    def save_state(self, store) -> None: ...
    def load_state(self, store) -> None: ...
    def invalidate(self, dirty_range) -> None: ...
    def estimate_delta(self, changeset) -> Delta: ...
```

Node 从"一次性计算单元"升级为"有生命周期和状态管理能力的计算单元"。

### 7.6 默认执行模式

```python
# Executor 默认走增量，仅在以下情况退化全量:
# 1. Node 不支持增量
# 2. Universe/特征定义/Label 定义结构性变化
# 3. 版本升级导致指纹失效
executor.execute(graph, dataset_ctx, mode="incremental", changeset=cs)
```

### 7.7 收益

每天自动更新几千个 Alpha 只重算变化部分；实时更新策略特征；支持分钟/秒/Tick 级计算。

---

## 八、前端 Research Graph Studio（第 7 节）

### 8.1 定位

不是流程图编辑器（Node-RED/Draw.io），而是整个 QuantLab 的研究工作台（Visual Quant Research IDE）。Research Studio / ML Lab / Strategy Studio 共用。

### 8.2 路由与文件结构

```
frontend/src/views/research_graph/
├── ResearchGraphStudio.vue        # 主容器 (IDE 布局)
├── panels/
│   ├── GraphCanvas.vue            # 中心画布 (DAG 可视化, 基于 Vue Flow)
│   ├── NodePalette.vue            # 左侧 Node Library (按 category 分组, 搜索/收藏)
│   ├── Inspector.vue              # 右侧节点属性/端口/参数
│   ├── PropertyPanel.vue          # 图级属性
│   ├── MiniMap.vue                # 小地图
│   ├── DependencyView.vue         # 依赖树
│   ├── ExecutionView.vue          # 执行进度/拓扑序
│   ├── CacheView.vue              # 缓存命中/失效
│   ├── ValidationView.vue         # 校验结果
│   └── ConsolePanel.vue           # 底部控制台
├── api/researchGraph.ts           # API 封装
└── stores/researchGraph.ts        # Pinia store
```

### 8.3 IDE 布局（VSCode 风格）

```
┌─────────────────────────────────────────────────────────────┐
│ Toolbar (新建/保存/编译/执行/增量/回滚)                         │
├──────────┬──────────────────────────────┬───────────────────┤
│ Node     │                              │ Inspector         │
│ Library  │       Graph Canvas           │ (节点属性/端口/参数) │
│ (分类搜索)│   (DAG 自动布局, 拖拽连线)    │                   │
│          │                              ├───────────────────┤
│          │                              │ Property (图级)    │
├──────────┼──────────────────────────────┼───────────────────┤
│ Console  │ Execution / Cache / Validation│ (Tab 切换)         │
└──────────┴──────────────────────────────┴───────────────────┘
```

### 8.4 各面板职责

- **Node Library（左侧）**：从 NodeRegistry 拉取全部 manifest，按 category 分组（Data/Indicator/Transform/Alpha/Aggregation/Ranking/Selection/Label/Custom），支持搜索、收藏、最近使用
- **Graph Canvas（中心）**：基于 Vue Flow（轻量、Vue3 原生、支持 DAG）；节点显示 id + 状态(已编译/已缓存/脏/执行中) + cost 星级；拖拽连线（port 对 port，类型校验）；自动布局（dagre）；选中节点高亮上下游依赖链
- **Inspector（右侧）**：选中节点后显示 manifest（inputs/outputs/params/version/fingerprint/cost）、参数可编辑、实时校验
- **底部 Tab**：Execution（拓扑序、每节点耗时、并行分组）/ Cache（L1-L5 命中率、缓存大小、失效事件流）/ Validation（编译错误、端口类型不匹配、循环依赖）
- **Toolbar 操作**：新建图 / 保存(持久化到 research_graphs 表) / 编译(调 compile API) / 全量执行 / 增量执行(传 ChangeSet) / 回滚(切历史版本)

### 8.5 与现有前端集成

- 新增路由 `/research-graph` 挂载 ResearchGraphStudio.vue
- 现有 `views/ml_lab/panels/FeatureLab.vue` / `FeatureSets.vue` 标记 deprecated，引导到 Research Graph Studio
- 现有 `views/factors/FactorStudio.vue` 同样引导到新 Studio

---

## 九、DB Schema 变更 + 回滚机制 + 测试策略（第 8 节）

### 9.1 现有 DB 表

`ml_lab.db`：`datasets` / `feature_sets` / `label_sets` / `training_jobs` / `models`

### 9.2 新增表（Research Store）

```sql
-- 节点清单
CREATE TABLE research_nodes (
    node_id        TEXT,
    name           TEXT NOT NULL,
    version        TEXT NOT NULL,
    category       TEXT NOT NULL,
    manifest_json  TEXT NOT NULL,
    fingerprint    TEXT NOT NULL,
    deprecated     INTEGER DEFAULT 0,
    created_at     TEXT,
    PRIMARY KEY (node_id, version)
);

-- 研究图定义
CREATE TABLE research_graphs (
    graph_id       TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    version        TEXT NOT NULL,
    nodes_json     TEXT NOT NULL,
    edges_json     TEXT NOT NULL,
    fingerprint    TEXT NOT NULL,
    description    TEXT,
    created_at     TEXT
);

-- 缓存清单
CREATE TABLE cache_manifests (
    cache_id       TEXT PRIMARY KEY,
    node_id        TEXT,
    dataset_id     TEXT,
    range_start    TEXT,
    range_end      TEXT,
    version        TEXT,
    dependencies_json TEXT,
    level          TEXT,
    size           INTEGER,
    ttl            TEXT,
    created_at     TEXT
);

-- 研究资产 (L3 Research Asset Store)
CREATE TABLE research_assets (
    asset_id       TEXT PRIMARY KEY,
    node_id        TEXT,
    dataset_id     TEXT,
    range_start    TEXT,
    range_end      TEXT,
    storage_path   TEXT,
    fingerprint    TEXT,
    promoted_at    TEXT,
    UNIQUE(node_id, dataset_id, range_start, range_end)
);

-- 实体化训练数据集
CREATE TABLE materialized_datasets (
    md_id          TEXT PRIMARY KEY,
    graph_id       TEXT,
    dataset_id     TEXT,
    label_node_id  TEXT,
    split_json     TEXT,
    storage_path   TEXT,
    n_train        INTEGER,
    n_test         INTEGER,
    created_at     TEXT
);

-- 增量状态
CREATE TABLE incremental_states (
    state_id       TEXT PRIMARY KEY,
    node_id        TEXT,
    graph_id       TEXT,
    state_json     TEXT,
    checkpoint_at  TEXT,
    fingerprint    TEXT
);

-- Universe / Calendar
CREATE TABLE universes (
    universe_id    TEXT PRIMARY KEY,
    definition_json TEXT,
    created_at     TEXT
);
CREATE TABLE calendars (
    calendar_id    TEXT PRIMARY KEY,
    sessions_json  TEXT,
    created_at     TEXT
);
```

### 9.3 现有表变更（增量 ALTER，不破坏旧数据）

```sql
-- datasets 表新增字段
ALTER TABLE datasets ADD COLUMN dataset_type TEXT DEFAULT 'panel';
ALTER TABLE datasets ADD COLUMN calendar_id  TEXT DEFAULT '';
ALTER TABLE datasets ADD COLUMN adjustment   TEXT DEFAULT 'none';

-- training_jobs 表新增字段
ALTER TABLE training_jobs ADD COLUMN research_graph_id TEXT DEFAULT '';
ALTER TABLE training_jobs ADD COLUMN label_node_id    TEXT DEFAULT '';
ALTER TABLE training_jobs ADD COLUMN materialize_config_json TEXT DEFAULT '{}';
ALTER TABLE training_jobs ADD COLUMN materialized_dataset_id TEXT DEFAULT '';
```

### 9.4 旧表处理（规则5：DB结构与新结构一致）

- `feature_sets` / `label_sets` 表**保留并重命名**为 `feature_sets_deprecated` / `label_sets_deprecated`（标记废弃，回滚时还原）
- 旧 `datasets` / `training_jobs` 表**就地 ALTER**（新增字段，旧字段保留），保证向前兼容
- 新数据全部写入新表，旧表只读不写
- DB 迁移脚本一次性执行（符合"直接修改DB结构而非代码迁移逻辑"偏好），执行前自动备份 `ml_lab.db` → `ml_lab.db.backup_<timestamp>`

### 9.5 回滚机制（5 重保障）

1. **Git 分支策略**：升级在独立分支 `feature/research-os-upgrade`，主干保持稳定，合并前完整测试
2. **DB 备份**：迁移脚本执行前 `cp ml_lab.db ml_lab.db.backup_<timestamp>`；回滚脚本 `restore_backup.py` 一键还原
3. **Feature Flag**：`config/research.yaml` 增加 `use_research_graph: true/false`，运行时切换新旧体系；旧入口保留一个发版周期
4. **兼容层**：`get_feature_registry()`/`get_feature_set_registry()`/`get_registry()`(Factor) 内部转发到 NodeRegistry，回滚时切回旧实现
5. **数据双写过渡期**（可选）：关键表迁移期间新旧双写，验证一致后切单写

### 9.6 测试策略（规则2：每个功能做好最小单元测试）

| 层级 | 范围 | 工具 | 路径 |
|------|------|------|------|
| 单元测试 | 每个 Node（RSI/ATR/Alpha017/FutureReturn）compute 正确性、fingerprint 稳定性、Manifest 序列化、Cache hit/miss、Invalidator 传播 | pytest | `tests/research/unit/` |
| 单元测试 | Graph 编译（无环校验/端口类型/拓扑序）、Executor 执行顺序、Materializer 切分对齐 | pytest | `tests/research/unit/` |
| 集成测试 | 端到端：Dataset → Graph → Executor → Materializer → TrainingJob → Model，用 BTC/ETH/SOL 真实短历史数据 | pytest | `tests/research/integration/` |
| 集成测试 | 增量：ChangeSet 追加1根K线 → 脏节点只重算变化部分 → 结果与全量一致 | pytest | `tests/research/integration/` |
| 集成测试 | Cache：同图二次执行 L1 命中、跨执行 L2/L3 命中、Dataset 更新触发失效 | pytest | `tests/research/integration/` |
| 性能测试 | Alpha101 全量计算耗时、增量 vs 全量加速比、Cache 命中率 | pytest-benchmark | `tests/research/perf/` |
| 回归测试 | 旧 FeatureRegistry 接口经兼容层与 NodeRegistry 输出一致性 | pytest | `tests/research/regression/` |

### 9.7 首次回测验证（项目规则2）

用较短历史数据（如 BTCUSDT 2024-01-01~2024-06-01）跑通完整训练闭环，确认 MVP 可用后再扩展。

---

## 十、实施顺序（方案 B 内部依赖序）

虽为方案 B（一次性全量 spec），实施时仍按依赖顺序推进，确保每步可独立测试：

1. **基础层**：ResearchFrame + ResearchNode 基类 + Port + Manifest
2. **节点层**：9 类 builtin Node（Data/Transform/Indicator/Alpha/Aggregation/Ranking/Selection/Label/Custom）+ 旧 Feature/Factor 迁移
3. **图层**：ResearchGraph + Edge + CompiledGraph + ResearchExecutor + ExecutionContext
4. **缓存层**：CacheManager + L1-L5 + CacheManifest + Invalidator + CachePlanner
5. **注册层**：NodeRegistry + UniverseRegistry + CalendarRegistry（替代旧 Registry）
6. **数据层**：Dataset 升级（新字段）+ Materializer + TrainingDataset
7. **增量层**：ChangeSet + DeltaAnalyzer + IncrementalPlanner + StateStore + Node 增量能力
8. **训练层**：TrainingJob 改造（吃 Graph）+ feature_analysis/diagnostics/label 迁移
9. **API 层**：api/ml.py + api/factors.py 改造 + 兼容层
10. **DB 层**：迁移脚本 + 新表 + ALTER + 备份 + 回滚脚本
11. **前端层**：Research Graph Studio + 路由 + 旧页面 deprecated
12. **测试层**：单元 + 集成 + 性能 + 回归，贯穿全过程

---

## 十一、验收标准

### 11.1 功能验收

- [ ] 9 类 builtin Node 全部实现，每个有单元测试
- [ ] ResearchGraph 可构建/编译/执行，支持 Alpha017 示例图端到端
- [ ] CacheManager 5 级可用，Execution Cache 与 Research Asset 区分清晰
- [ ] Dependency Invalidation 事件驱动传播正确
- [ ] Materializer 产出 TrainingDataset，TrainingJob 改用 Graph 产物
- [ ] Incremental Framework：ChangeSet 追加 K 线，脏节点重算，结果与全量一致
- [ ] 旧 FeatureRegistry/FactorRegistry 经兼容层输出与 NodeRegistry 一致
- [ ] 前端 Research Graph Studio 可视化建图/编译/执行/查看缓存
- [ ] DB 迁移脚本可执行，回滚脚本可还原

### 11.2 性能验收

- [ ] Alpha101 全量计算在 BTC+ETH+SOL 1 年数据上 < 60s
- [ ] 增量执行（追加 1 根 K 线）比全量快 10x 以上
- [ ] Cache 命中率二次执行 > 90%

### 11.3 兼容性验收

- [ ] 旧入口 `get_feature_registry()` 等可用且输出一致
- [ ] Feature Flag 切回旧体系可运行
- [ ] DB 回滚后旧体系可运行

### 11.4 文档验收

- [ ] 升级报告说明实现功能、解决问题、与文档要求符合程度
- [ ] 系统运行验证结果

---

## 十二、风险与对策

| 风险 | 对策 |
|------|------|
| 方案 B 一次性全量，回归风险高 | 5 重回滚机制 + 充分测试 + Feature Flag |
| 旧 Feature/FactorInfo 全量迁移工作量大 | 兼容层转发，迁移可分批；每迁移一个 Node 即测试 |
| DB schema 变更影响线上数据 | 迁移前自动备份 + ALTER 增量不破坏旧字段 + 旧表重命名保留 |
| 增量计算正确性难保证 | 增量结果与全量结果一致性集成测试（必过） |
| 前端 Vue Flow DAG 复杂度 | 复用 Vue Flow 成熟方案 + 自动布局 dagre |
| Alpha101/Alpha191 节点数量大 | 复用现有 factor/alpha191, factor/alpha101 实现，封装为 Node |

---

## 十三、与文档要求符合性对照

| 文档要求 | 本设计落实 | 章节 |
|---------|-----------|------|
| ResearchNode 统一抽象（能力接口） | 第三节 3.1 | ✓ |
| ResearchFrame (datetime,symbol) MultiIndex | 第三节 3.3 | ✓ |
| 9 类 Node 分类 | 第三节 3.4 | ✓ |
| ResearchGraph DAG + Executor | 第四节 | ✓ |
| Node Manifest + Registry | 第五节 5.1-5.2 | ✓ |
| 5 级 Cache + Execution/Research Asset 区分 | 第五节 5.3-5.4 | ✓ |
| Dependency Invalidation | 第五节 5.6 | ✓ |
| Cache Planner | 第五节 5.7 | ✓ |
| Dataset 升级（calendar/adjustment/dataset_type） | 第六节 6.1 | ✓ |
| Universe/Calendar Registry | 第六节 6.2-6.3 | ✓ |
| Materializer | 第六节 6.4 | ✓ |
| 训练不再直接吃 Dataset | 第六节 6.5 | ✓ |
| Incremental Framework + 默认增量 | 第七节 | ✓ |
| ChangeSet 系统唯一输入 | 第七节 7.1 | ✓ |
| Node 增量能力升级 | 第七节 7.5 | ✓ |
| 前端 Research Graph Studio（IDE） | 第八节 | ✓ |
| DB schema 变更 + 回滚 | 第九节 | ✓ |
| 充分测试 | 第九节 9.6 | ✓ |

---

**本 Spec 已通过 8 节设计逐节确认，待 writing-plans skill 生成详细实施计划。**

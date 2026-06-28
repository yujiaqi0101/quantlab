# Signal Engine 详细设计

> 基于 `docs/signal engine.md` 的设计文档
> 日期：2026-06-28
> 状态：待审查

## 一、架构总览

### 1.1 在 ML Lab 中的位置

```
ML Lab Pipeline
├── Stage 1: Dataset Registry
├── Stage 2: Feature Registry
├── Stage 3: Label Registry
├── Stage 4: Training Center
├── Stage 5: Validation Center
├── Stage 6: Model Registry
├── Stage 7: ★ Signal Engine ← 新增
└── Stage 8: Strategy Builder
```

### 1.2 数据流

```
Model Prediction
      │
      ▼
[1. Prediction Adapter]   ← 统一各模型输出格式
      │
      ▼
[2. Calibrator]           ← 概率校准
      │
      ▼
[3. Generator]            ← Prediction → Signal (有 direction)
      │
      ▼
[4. Filter]               ← 流动性/停牌/黑名单过滤
      │
      ▼
[5. Ranker]               ← TopK / BottomK 排序
      │
      ▼
[6. Scorer]               ← 统一评分 [-100, 100]
      │
      ▼
[7. Position Allocator]   ← Kelly / VolScaling 建议权重
      │
      ▼
   SignalSet              ← 最终输出
      │
      ├─→ [8. Validator]  ← Hit Rate / IC / Win Rate 验证
      │
      ├─→ [9. Registry]   ← SQLite 持久化 + 版本管理
      │
      └─→ [11. Explainability] ← 溯源解释

[10. Templates]           ← 预配置 pipeline 参数 (TopK/Momentum/...)
```

### 1.3 目录结构

```
quantlab/ml/signal_engine/
├── __init__.py              # 公开 API
├── signal.py                # Signal + SignalSet + Prediction 对象
├── prediction_adapter.py    # 模块1
├── calibrator.py            # 模块2
├── generator.py             # 模块3 (核心)
├── filter.py                # 模块4
├── ranker.py                # 模块5
├── scorer.py                # 模块6
├── position_allocator.py    # 模块7
├── signal_validator.py      # 模块8
├── signal_registry.py       # 模块9
├── templates.py             # 模块10
├── explainability.py        # 模块11
├── pipeline.py              # 编排 9 步流水线
└── storage.py               # SQLite 存储层

quantlab/api/
└── signal_engine.py         # FastAPI 路由

frontend/src/
├── api/signalEngine.ts
└── views/ml_lab/panels/
    ├── SignalEngine.vue
    ├── SignalRegistry.vue
    └── SignalExplainability.vue

tests/test_signal_engine/    # 单元测试
├── test_signal.py
├── test_prediction_adapter.py
├── test_calibrator.py
├── test_generator.py
├── test_filter.py
├── test_ranker.py
├── test_scorer.py
├── test_position_allocator.py
├── test_signal_validator.py
├── test_signal_registry.py
├── test_templates.py
├── test_explainability.py
└── test_pipeline.py
```

---

## 二、核心数据对象

### 2.1 Prediction（统一模型输出）

```python
# quantlab/ml/signal_engine/signal.py
@dataclass
class Prediction:
    """统一预测对象 — 所有模型输出经 PredictionAdapter 后转为此格式"""
    symbol: str
    datetime: str              # ISO 格式
    value: float               # 原始预测值 (回归: 收益率; 分类: 类别标签)
    probability: float = 0.0   # 概率/置信度 [0, 1]
    model_type: str = ""       # lightgbm / xgboost / linear / transformer / rl
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### 2.2 Signal（统一信号对象）

严格遵循 `docs/signal engine.md` 第 628-653 行定义：

```python
@dataclass
class Signal:
    """统一信号对象 — 整个 QuantLab 通用"""
    signal_id: str             # UUID
    symbol: str
    datetime: str              # ISO 格式
    direction: SignalDirection # LONG / SHORT / NEUTRAL
    score: float               # 统一评分 [-100, 100]
    confidence: float          # 校准后置信度 [0, 1]
    expected_return: float     # 期望收益
    suggested_weight: float    # 建议权重 [0, 1]
    holding_period: int        # 建议持仓天数
    source_model: str          # 来源模型版本
    generator: str             # 生成器名称 (threshold/quantile/...)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # metadata 含: prediction_value, raw_probability, filter_passed,
    #              rank_position, scorer_method, allocator_method,
    #              explain_trace (溯源链)
```

### 2.3 SignalSet（最终输出）

```python
@dataclass
class SignalSet:
    """Signal Engine 最终输出 — Strategy Builder 直接读取"""
    set_id: str                # UUID
    generated_at: str
    signals: List[Signal]
    pipeline_config: Dict      # 使用的 pipeline 配置快照
    summary: Dict[str, Any]    # 统计: n_long, n_short, avg_score, ...

    def by_symbol(self, symbol: str) -> Optional[Signal]: ...
    def longs(self) -> List[Signal]: ...
    def shorts(self) -> List[Signal]: ...
    def to_dict(self) -> Dict: ...
```

### 2.4 枚举

```python
class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"
```

---

## 三、11 个模块详细设计

### 模块 1: Prediction Adapter

**职责**：统一所有模型输出为 `Prediction` 对象。

```python
# quantlab/ml/signal_engine/prediction_adapter.py

class PredictionAdapter:
    """模型输出 → 统一 Prediction"""

    def adapt_regression(self, symbol, datetime, y_pred, model_type) -> Prediction:
        """回归模型: y_pred 是收益率"""

    def adapt_classifier(self, symbol, datetime, y_pred, y_proba, model_type) -> Prediction:
        """分类模型: y_pred 是类别 (0/1/2), y_proba 是概率向量"""

    def adapt_proba(self, symbol, datetime, proba, model_type) -> Prediction:
        """概率输出: proba 是 [0,1] 标量"""

    def adapt_sequence(self, symbol, datetime, sequence, model_type) -> Prediction:
        """序列模型 (Transformer): 取最后一项"""

    def adapt_action(self, symbol, datetime, action, model_type) -> Prediction:
        """RL 模型: action (0/1/2) → 类似分类"""

    def adapt_batch(self, predictions: List[Prediction]) -> List[Prediction]:
        """批量适配"""
```

**关键决策**：分类模型的类别映射固定为 `0=Down, 1=Neutral, 2=Up`（与现有 `ml/strategy/signal_generator.py` 一致）。

### 模块 2: Prediction Calibrator

**职责**：校准概率，使 confidence 更可靠。

```python
# quantlab/ml/signal_engine/calibrator.py

class Calibrator(ABC):
    """校准器抽象基类"""
    @abstractmethod
    def calibrate(self, prediction: Prediction) -> Prediction: ...

class TemperatureScaling(Calibrator):
    """Temperature Scaling — 单参数 T 缩放 logits"""
    def __init__(self, temperature: float = 1.0): ...
    def fit(self, y_true: np.ndarray, y_pred: np.ndarray) -> None: ...

class PlattScaling(Calibrator):
    """Platt Scaling — logistic 回归校准"""

class IsotonicRegression(Calibrator):
    """Isotonic Regression — 非参数单调校准"""

class NoCalibration(Calibrator):
    """透传 — 不校准"""

# 工厂
def get_calibrator(method: str) -> Calibrator:
    methods = {"temperature": TemperatureScaling,
               "platt": PlattScaling,
               "isotonic": IsotonicRegression,
               "none": NoCalibration}
    return methods.get(method, NoCalibration)()
```

**关键决策**：校准器可选，默认 `NoCalibration`（透传）。校准器的 `fit` 需要历史数据，在 pipeline 运行前可调用 `fit`，否则用默认参数。

### 模块 3: Signal Generator（核心）

**职责**：把 Prediction 转成有 direction 的 Signal。

```python
# quantlab/ml/signal_engine/generator.py

class Generator(ABC):
    """信号生成器抽象基类"""
    @abstractmethod
    def generate(self, prediction: Prediction) -> Signal: ...

class ThresholdGenerator(Generator):
    """阈值生成器 — 回归模型"""
    def __init__(self, long_threshold: float = 0.02,
                 short_threshold: float = -0.02,
                 use_short: bool = False): ...

class QuantileGenerator(Generator):
    """分位数生成器 — 截面分位"""

class RankingGenerator(Generator):
    """排序生成器 — 截面排名"""

class ProbabilityGenerator(Generator):
    """概率生成器 — 分类模型"""

class ClassificationGenerator(Generator):
    """分类生成器 — 类别直转"""

class RegressionGenerator(Generator):
    """回归生成器 — 连续值符号化"""

# 工厂
def get_generator(method: str, **params) -> Generator: ...
```

**关键决策**：
- 输出的 Signal 此时 `score=0`, `confidence=prediction.probability`, `suggested_weight=0`, `holding_period=0`（这些由后续模块填充）
- `expected_return` 在 ThresholdGenerator 中 = `prediction.value`

### 模块 4: Signal Filter

**职责**：过滤不可交易信号。

```python
# quantlab/ml/signal_engine/filter.py

class SignalFilter(ABC):
    @abstractmethod
    def filter(self, signal_set: SignalSet) -> SignalSet: ...

class LiquidityFilter(SignalFilter):
    """流动性过滤 — 最小成交额/成交量"""
    def __init__(self, min_volume: float = 0,
                 min_amount: float = 0,
                 market_data_provider: Optional[Callable] = None): ...

class SuspensionFilter(SignalFilter):
    """停牌过滤 — 需行情数据"""

class PriceLimitFilter(SignalFilter):
    """涨跌停过滤"""

class ListingAgeFilter(SignalFilter):
    """上市时间过滤 — 新股过滤"""

class BlacklistFilter(SignalFilter):
    """黑名单过滤"""
    def __init__(self, blacklist: Set[str]): ...

class CompositeFilter(SignalFilter):
    """组合过滤器"""
    def __init__(self, filters: List[SignalFilter]): ...
```

**关键决策**：
- 需要行情数据的过滤器接受一个 `market_data_provider` 回调（避免直接耦合数据源）
- 过滤掉的信号保留在 `SignalSet.metadata["filtered_out"]` 里以便溯源
- 默认无行情数据时，只有 `BlacklistFilter` 可用，其他透传

### 模块 5: Signal Ranker

**职责**：截面排序，保留 TopK / BottomK。

```python
# quantlab/ml/signal_engine/ranker.py

class Ranker(ABC):
    @abstractmethod
    def rank(self, signal_set: SignalSet) -> SignalSet: ...

class TopKRanker(Ranker):
    """取 score 最高的 K 个 LONG"""
    def __init__(self, k: int = 50): ...

class BottomKRanker(Ranker):
    """取 score 最低的 K 个 SHORT"""

class TopBottomKRanker(Ranker):
    """同时取 TopK 多 + BottomK 空"""
    def __init__(self, k_long: int = 50, k_short: int = 50): ...

class NoRanker(Ranker):
    """不排序 — 透传"""
```

**关键决策**：Ranker 按 `confidence` 排序（此时 score 还未计算），排序后写入 `signal.metadata["rank_position"]`。

### 模块 6: Signal Scorer

**职责**：统一评分到 `[-100, 100]`。

```python
# quantlab/ml/signal_engine/scorer.py

class Scorer(ABC):
    @abstractmethod
    def score(self, signal_set: SignalSet) -> SignalSet: ...

class TanhScorer(Scorer):
    """tanh 映射到 [-100, 100]"""

class QuantileScorer(Scorer):
    """截面分位映射"""

class ZScoreScorer(Scorer):
    """Z-Score 标准化后映射"""

class RankScorer(Scorer):
    """排名映射 — rank/(n-1)*200-100"""
```

**关键决策**：评分基于 `confidence` 和 `expected_return` 组合，方向决定正负号。`score` 字段统一写回 `Signal.score`。

### 模块 7: Position Allocator

**职责**：建议权重（不是最终 portfolio）。

```python
# quantlab/ml/signal_engine/position_allocator.py

class PositionAllocator(ABC):
    @abstractmethod
    def allocate(self, signal_set: SignalSet) -> SignalSet: ...

class EqualWeightAllocator(PositionAllocator):
    """等权"""

class KellyAllocator(PositionAllocator):
    """Kelly 公式"""

class VolatilityScalingAllocator(PositionAllocator):
    """波动率倒数加权"""
    def __init__(self, target_volatility: float = 0.15): ...

class RiskParityAllocator(PositionAllocator):
    """风险平价"""

class ConfidenceWeightAllocator(PositionAllocator):
    """按 confidence 加权"""
```

**关键决策**：
- 权重归一化到 `[0, 1]`，且所有 LONG 权重之和 + 所有 SHORT 权重之和 ≤ 1.0
- 只输出 `suggested_weight`，最终 portfolio 由 Strategy Builder 的 Position 包决定
- `holding_period` 在此模块一并设定（默认 5 天，可配置）

### 模块 8: Signal Validator

**职责**：验证 Signal（不是验证模型）。

```python
# quantlab/ml/signal_engine/signal_validator.py

@dataclass
class ValidationReport:
    """信号验证报告"""
    hit_rate: float            # 方向命中率
    precision: float           # 多头 Precision
    recall: float
    avg_return: float          # 平均收益
    turnover: float            # 换手率
    avg_holding_days: float
    ic: float                  # IC
    rank_ic: float             # Rank IC
    win_rate: float            # 胜率
    n_signals: int
    period: str
    details: Dict[str, Any]

class SignalValidator:
    """信号验证器"""
    def __init__(self, forward_periods: List[int] = [1, 5, 10, 20]): ...

    def validate(self, signals: List[Signal],
                 returns: pd.DataFrame,  # symbol × datetime 收益矩阵
                 benchmark: Optional[pd.Series] = None) -> ValidationReport: ...

    def validate_signal_set(self, signal_set: SignalSet,
                            returns: pd.DataFrame) -> ValidationReport: ...
```

**关键决策**：
- 输入是历史 Signal 列表 + 收益矩阵
- IC 用截面 IC（多标的）或时序 IC（单标的），与 `quantlab/api/factors.py` 的 IC 实现保持一致风格
- 输出 `ValidationReport`，同时存入 Registry 的 `validation_summary` 字段

### 模块 9: Signal Registry

**职责**：SQLite 持久化 + 版本管理。

```python
# quantlab/ml/signal_engine/signal_registry.py

@dataclass
class SignalVersion:
    """信号版本记录"""
    version_id: str
    signal_id: str
    version: int
    generator_config: Dict     # 生成器配置快照
    model_version: str
    dataset_id: str
    validation_summary: Dict
    created_at: str

class SignalRegistry:
    """信号仓库 — SQLite 持久化"""
    def __init__(self, db_path: str = "data/datasets.db"): ...

    def register_signal(self, signal: Signal, version_info: SignalVersion) -> None: ...
    def get_signal(self, signal_id: str) -> Optional[Signal]: ...
    def list_signals(self, symbol: str = "", direction: str = "",
                     limit: int = 100) -> List[Signal]: ...
    def list_versions(self, signal_id: str) -> List[SignalVersion]: ...
    def latest_version(self, signal_id: str) -> Optional[SignalVersion]: ...
    def search(self, **kwargs) -> List[Signal]: ...
```

### 模块 10: Signal Templates

**职责**：预配置 pipeline，用户直接套用。

```python
# quantlab/ml/signal_engine/templates.py

@dataclass
class SignalTemplate:
    """信号模板"""
    name: str                  # topk / long_short / momentum / ...
    description: str
    pipeline_config: Dict      # 完整 pipeline 配置
    required_model_type: str   # regression / classification / any

TEMPLATES: Dict[str, SignalTemplate] = {
    "topk": SignalTemplate(
        name="topk",
        description="TopK 截面多头",
        pipeline_config={
            "generator": {"method": "regression"},
            "ranker": {"method": "topk", "k": 50},
            "scorer": {"method": "rank"},
            "allocator": {"method": "equal_weight"},
        },
        required_model_type="regression",
    ),
    "long_short": ...,
    "probability": ...,
    "mean_reversion": ...,
    "momentum": ...,
    "breakout": ...,
    "triple_barrier": ...,
    "meta_labeling": ...,
}

def get_template(name: str) -> Optional[SignalTemplate]: ...
def list_templates() -> List[SignalTemplate]: ...
```

### 模块 11: Signal Explainability

**职责**：信号溯源解释。

```python
# quantlab/ml/signal_engine/explainability.py

@dataclass
class ExplainTrace:
    """信号溯源链"""
    prediction: Dict           # 原始预测
    after_calibration: Dict    # 校准后
    after_generator: Dict      # 生成后 (direction)
    after_filter: Dict         # 过滤后 (是否被过滤)
    after_ranker: Dict         # 排名
    after_scorer: Dict         # 评分
    after_allocator: Dict      # 建议权重
    final_signal: Dict

class ExplainabilityEngine:
    """信号解释引擎"""
    def explain(self, signal: Signal) -> ExplainTrace:
        """从 signal.metadata["explain_trace"] 重建溯源链"""

    def explain_pipeline(self, pipeline_trace: List[Dict]) -> ExplainTrace: ...
```

**关键决策**：Pipeline 在每一步都把中间状态写入 `signal.metadata["explain_trace"]`，Explainer 只是聚合展示，不重新计算。

---

## 四、Pipeline 编排

```python
# quantlab/ml/signal_engine/pipeline.py

@dataclass
class PipelineConfig:
    """Pipeline 配置 — 可来自 Template 或自定义"""
    generator: Dict = field(default_factory=lambda: {"method": "threshold",
                                                      "long_threshold": 0.02,
                                                      "short_threshold": -0.02,
                                                      "use_short": False})
    calibrator: Dict = field(default_factory=lambda: {"method": "none"})
    filters: List[Dict] = field(default_factory=list)
    ranker: Dict = field(default_factory=lambda: {"method": "none"})
    scorer: Dict = field(default_factory=lambda: {"method": "tanh"})
    allocator: Dict = field(default_factory=lambda: {"method": "equal_weight"})
    holding_period: int = 5
    save_to_registry: bool = True

class SignalPipeline:
    """Signal Engine 主流水线"""

    def __init__(self, config: PipelineConfig): ...

    def run(self,
            predictions: List[Prediction],
            market_data_provider: Optional[Callable] = None) -> SignalSet:
        """
        执行 7 步核心流水线 (Adapter 已在外部完成):
        1. Calibrator.calibrate
        2. Generator.generate → Signal (有 direction)
        3. Filter.filter
        4. Ranker.rank
        5. Scorer.score
        6. PositionAllocator.allocate + 设 holding_period
        7. 构造 SignalSet

        后处理 (可选):
        - Registry.register_signal (save_to_registry=True 时)
        - Validator.validate_signal_set (需提供 returns 数据)
        """
```

**关键决策**：
- Prediction Adapter 不在 pipeline 内（因为不同模型适配方式不同，由调用方主动调 `adapt_xxx`）
- Pipeline 内每步都把中间状态写入 `signal.metadata["explain_trace"]`
- 任何一步失败不中断整体，记入 `SignalSet.metadata["errors"]`

---

## 五、SQLite Schema

使用现有 `data/datasets.db`（与 DatasetManager 一致），新增两张表：

```sql
-- signals 表：单个信号实例
CREATE TABLE IF NOT EXISTS signals (
    signal_id        TEXT PRIMARY KEY,
    symbol           TEXT NOT NULL,
    datetime         TEXT NOT NULL,
    direction        TEXT NOT NULL,        -- LONG / SHORT / NEUTRAL
    score            REAL NOT NULL,
    confidence       REAL NOT NULL,
    expected_return  REAL,
    suggested_weight REAL,
    holding_period   INTEGER,
    source_model     TEXT,
    generator        TEXT,
    metadata         TEXT,                 -- JSON
    version_id       TEXT,                 -- FK → signal_versions
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol);
CREATE INDEX IF NOT EXISTS idx_signals_datetime ON signals(datetime);
CREATE INDEX IF NOT EXISTS idx_signals_direction ON signals(direction);

-- signal_versions 表：版本管理
CREATE TABLE IF NOT EXISTS signal_versions (
    version_id          TEXT PRIMARY KEY,
    signal_id           TEXT NOT NULL,
    version             INTEGER NOT NULL,
    generator_config    TEXT,              -- JSON
    model_version       TEXT,
    dataset_id          TEXT,
    validation_summary  TEXT,              -- JSON
    pipeline_config     TEXT,              -- JSON
    created_at          TEXT NOT NULL,
    FOREIGN KEY (signal_id) REFERENCES signals(signal_id)
);
```

**关键决策**：
- 复用 `data/datasets.db`，不新建库
- `metadata` 用 JSON 字符串存储（SQLite 无原生 JSON 类型）
- 不写模拟数据（遵循项目规则）

---

## 六、API 端点

新建 `quantlab/api/signal_engine.py`，注册到 `quantlab/api/app.py`。

```
前缀: /api/v1/signal-engine

# Pipeline 运行
POST /generate
  body: { predictions: [...], config: PipelineConfig, market_data?: {...} }
  resp: SignalSet

# 模板
GET  /templates
  resp: { templates: [...], total: N }
GET  /templates/{name}
  resp: SignalTemplate

# 信号查询
GET  /signals?symbol=&direction=&limit=
  resp: { signals: [...], total: N }
GET  /signals/{signal_id}
  resp: Signal

# 版本管理
GET  /registry/versions?signal_id=
  resp: { versions: [...], total: N }
GET  /registry/versions/{version_id}
  resp: SignalVersion

# 验证
POST /validate
  body: { signal_ids: [...], returns_data: {...} }
  resp: ValidationReport

# 解释
GET  /explain/{signal_id}
  resp: ExplainTrace

# 适配（手动调 Adapter，调试用）
POST /adapt
  body: { model_type: "regression", outputs: [...] }
  resp: { predictions: [...] }
```

注册：在 `app.py` 加 `from .signal_engine import router as signal_engine_router` 和 `app.include_router(signal_engine_router, prefix="/api/v1/signal-engine")`。

---

## 七、前端面板

### 7.1 ML Lab Pipeline 调整

`frontend/src/views/ml_lab/MLLab.vue` 在 Stage 6 (Model Registry) 和 Stage 7 (Strategy Builder) 之间插入 Stage 7 "Signal Engine"（原 Strategy Builder 顺延为 Stage 8）。

### 7.2 三个新面板

**SignalEngine.vue**（主面板）
- 顶部：模板选择下拉 + "运行 Pipeline" 按钮
- 表单区：可折叠的 Pipeline 配置（Generator/Calibrator/Filter/Ranker/Scorer/Allocator 各一节）
- 输入区：选择 Model Version + Dataset（自动调 model.predict 生成 predictions）或手动粘贴 predictions JSON
- 结果区：信号表格（symbol/direction/score/confidence/expected_return/suggested_weight/holding_period）+ 统计卡片（n_long/n_short/avg_score）

**SignalRegistry.vue**（信号仓库）
- 信号列表表格 + 筛选（symbol/direction/日期范围）
- 版本历史查看（点击信号展开版本树）
- 验证报告查看（弹窗）

**SignalExplainability.vue**（解释面板）
- 选择一个 signal_id
- 展示溯源链：Prediction → Calibration → Generator → Filter → Ranker → Scorer → Allocator → Final
- 每步显示输入/输出 diff

### 7.3 前端 API

```typescript
// frontend/src/api/signalEngine.ts
export async function runPipeline(data: {
  predictions: Prediction[]
  config: PipelineConfig
}): Promise<SignalSet>
export async function getTemplates(): Promise<{ templates: SignalTemplate[] }>
export async function getTemplate(name: string): Promise<SignalTemplate>
export async function getSignals(params?): Promise<{ signals: Signal[]; total: number }>
export async function getSignal(id: string): Promise<Signal>
export async function getVersions(signalId: string): Promise<{ versions: SignalVersion[] }>
export async function validateSignals(data): Promise<ValidationReport>
export async function explainSignal(id: string): Promise<ExplainTrace>
```

---

## 八、与现有系统的迁移

### 8.1 替换 `ml/strategy/signal_generator.py`

- 在文件顶部加 `# DEPRECATED: 请使用 quantlab.ml.signal_engine` 注释
- 保留旧 `Signal` 类（避免破坏现有 import），但内部转发到新 engine
- `ml/strategy/ml_strategy.py` 等调用方逐步迁移

### 8.2 不动 `asset_package` 的 SignalPackage

- `SignalPackage` 是 Strategy Builder 的装配组件（ThresholdSignal/ProbabilitySignal/TrendSignal/RankingSignal）
- 新 Signal Engine 输出的 `SignalSet` 是上游产物
- 后续可加一个适配器把 `SignalSet` 转成 `SignalPackage`，但本次不做

### 8.3 不动前端 Signal Research

- 前端 `SignalWorkspace.vue` 是独立的"信号构建器"（基于 Factor 的阈值/交叉信号），与 ML Lab 的 Signal Engine（基于 Model Prediction）概念不同
- 本次只做 ML Lab 内的 Signal Engine，不碰 Signal Research

---

## 九、测试策略

遵循 AGENTS.md "每个完成的功能都要做好最小单元测试"：

1. **每个模块独立单测**：`tests/test_signal_engine/test_*.py`，覆盖每个类的核心方法
2. **Pipeline 集成测试**：`test_pipeline.py`，端到端跑一遍 mock predictions
3. **Registry 存储测试**：用临时 SQLite 文件，验证 CRUD
4. **API 端点测试**：用 FastAPI TestClient
5. **遵循项目规则**：测试脚本放 `tests/test_signal_engine/`，不污染根目录；不写模拟数据到正式 DB

**关键测试用例**：
- ThresholdGenerator: pred=0.05, threshold=0.02 → LONG
- TopKRanker: 100 个信号 → 保留 50 个
- TanhScorer: confidence=0.9 → score≈72
- VolatilityScalingAllocator: 高波动标的权重低
- SignalValidator: mock 收益数据 → IC 计算
- Pipeline: 10 个 predictions → 7 步后输出 SignalSet

---

## 十、实施顺序（依赖驱动）

```
Phase 1: 基础对象 + 存储
  1. signal.py (Signal/SignalSet/Prediction)
  2. storage.py (SQLite schema + CRUD)
  3. signal_registry.py

Phase 2: 核心生成链
  4. prediction_adapter.py
  5. calibrator.py
  6. generator.py (核心)
  7. filter.py
  8. ranker.py
  9. scorer.py
  10. position_allocator.py

Phase 3: 编排 + 验证
  11. pipeline.py
  12. signal_validator.py
  13. templates.py
  14. explainability.py

Phase 4: API + 前端
  15. quantlab/api/signal_engine.py + 注册
  16. frontend/src/api/signalEngine.ts
  17. SignalEngine.vue
  18. SignalRegistry.vue
  19. SignalExplainability.vue
  20. MLLab.vue 插入 Stage 7

Phase 5: 迁移 + 测试
  21. 标记旧 signal_generator.py deprecated
  22. 全套单元测试
```

---

## 十一、关键设计决策汇总

| 决策点 | 选择 | 理由 |
|---|---|---|
| 目录结构 | 扁平 `quantlab/ml/signal_engine/` | 文档对应、个人版足够 |
| Signal 对象字段 | 严格按文档 628-653 行 | 统一全系统 |
| 插件化方式 | 策略模式（抽象基类 + 工厂） | 不过度工程化 |
| 持久化 | SQLite 复用 `data/datasets.db` | 与现有体系一致 |
| Pipeline 编排 | 7 步内部 + Adapter 外部 | Adapter 需调用方主动适配 |
| 校准器默认 | `NoCalibration` 透传 | 无历史数据时不阻塞 |
| Filter 行情数据 | 回调注入 `market_data_provider` | 解耦数据源 |
| Explainability | 复用 pipeline 中间 trace | 不重新计算 |
| 旧 signal_generator.py | 标记 deprecated，不立即删 | 避免破坏现有调用 |
| 前端 Signal Research | 不动 | 概念不同（Factor-based vs Model-based） |

---

## 十二、检查清单 (Checklist)

### 实现前
- [ ] 设计文档已审查通过
- [ ] 数据库结构变更已确认（新增 2 张表，不动现有表）

### 实现中
- [ ] 每个模块完成后立即写单元测试
- [ ] 不向数据库写入模拟数据
- [ ] 旧 `signal_generator.py` 调用方迁移完成

### 实现后
- [ ] Pipeline 端到端跑通
- [ ] API 端点全部可访问（无 404）
- [ ] 前端三个面板可正常渲染
- [ ] ML Lab Stage 7 顺序正确
- [ ] 单元测试全部通过

# Strategy Studio 重构项目计划

> **项目代号**：Strategy Studio（策略工作室）
> **创建日期**：2026-06-24
> **完成日期**：2026-06-25
> **状态**：✅ 已完成（P1-P6 全部实现 + 旧端点废弃）
> **核心理念**：从"代码驱动"重构为"配置驱动 + 资产装配"

---

## 一、项目背景与目标

### 1.1 问题现状

当前 `ml/strategy/` 模块存在以下问题：

1. **硬编码类**：Signal/Position/Risk 是写死的 Python 类，无法复用、无法版本管理
2. **Strategy = Model + if pred > 0**：过于简化，缺少 Signal/Position/Risk/Execution/Observe 等独立组件
3. **Builder 是 Generator**：`StrategyBuilder` 重新训练模型而非装配已有资产
4. **无 Package 化**：Signal/Position/Risk 没有独立的包格式，无法注册到 Asset Registry
5. **前端半成品**：`StrategyBuilder.vue` 只有静态展示，无装配流程

### 1.2 目标架构

```
                    Asset Registry（资产注册中心）
================================================================
Dataset  Feature  Label  Model  Signal  Position  Risk  Execution  Observe
================================================================
                    ★ Strategy Studio ★
        Dependency Resolver → Composer → Validation
                          ↓
                Strategy Package (.qlstrategy)
                          ↓
                    Strategy Registry
                          ↓
              Paper / Backtest / Live
```

### 1.3 核心设计原则

1. **Strategy 是 Asset Composition（资产组合）**，不是 Model + if
2. **Builder 是 Assembler（装配器）**，不是 Generator（生成器）
3. **配置驱动**：Builder 输出 `.qlstrategy` 包，Runtime 解释 manifest 运行
4. **全是 ref 引用**：manifest 里全是 `ref://name@version`，不复制数据
5. **强版本引用**：`name@version` 格式，确保可复现

---

## 二、关键决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 实施范围 | 全部一次性做完 P1-P6 | 用户要求 |
| Package 存储 | 文件系统目录 | 与 .qlmodel 一致，可 diff、可版本控制 |
| ref 引用 | 强版本 `name@version` | 可复现、可追溯 |
| 现有代码处理 | 重写替换 | 架构干净，避免两层包装 |
| 前端组件 | 重构为 StrategyStudio.vue | 体现装配器定位 |

---

## 三、子项目分解

### P1：Asset Package 标准化（基础层）

**目标**：定义统一 Package 格式，升级现有空壳 Asset 类

**依赖**：无

**交付物**：
- `asset_package/base.py`：Package 基类 + manifest schema
- `asset_package/storage.py`：文件系统存储
- `asset_package/registry.py`：Package Registry
- 升级 `asset/base.py` 的 AssetType 枚举

### P2：Signal/Position/Risk/Execution/Observe Package 系统（组件层）

**目标**：把硬编码类升级为可注册 Package，新增多种实现

**依赖**：P1

**交付物**：
- `asset_package/types/signal.py`：SignalPackage + 5 种实现
- `asset_package/types/position.py`：PositionPackage + 5 种实现
- `asset_package/types/risk.py`：RiskPackage + 5 种实现
- `asset_package/types/execution.py`：ExecutionProfile + 4 种实现
- `asset_package/types/observe.py`：ObserveProfile + 2 种实现

### P3：.qlstrategy 包格式 + Manifest（策略层）

**目标**：定义 .qlstrategy 结构，全是 ref 引用

**依赖**：P1, P2

**交付物**：
- `asset_package/types/strategy.py`：StrategyPackage
- manifest.yaml schema 定义

### P4：Strategy Studio 后端（装配器）

**目标**：Compose API + Dependency Resolver + Strategy Validation

**依赖**：P3

**交付物**：
- `strategy_studio/composer.py`：装配器
- `strategy_studio/resolver.py`：依赖解析器
- `strategy_studio/validator.py`：Smoke Test 验证
- `api/strategy_studio.py`：REST API

### P5：Strategy Studio 前端

**目标**：StrategyStudio.vue 装配流程 UI

**依赖**：P4

**交付物**：
- `StrategyStudio.vue`：装配流程界面
- `api/strategy_studio.ts`：前端 API 封装

### P6：Strategy Runtime 解释器

**目标**：解释 manifest，加载各组件，对接 Execution Core

**依赖**：P3, P4

**交付物**：
- `strategy_studio/runtime.py`：Runtime 解释器

---

## 四、详细设计

### 4.1 统一 Package 格式（P1）

#### 4.1.1 目录结构

```
storage/asset_packages/<type>/<name>@<version>/
  manifest.yaml    # 元数据 + ref 引用
  artifacts/        # 实际文件（model.pkl, config.json 等）
```

#### 4.1.2 manifest.yaml 通用 schema

```yaml
# 通用字段（所有 Package 都有）
id: <name>@<version>          # 唯一标识
name: <name>                   # 名称
version: "<version>"           # 语义化版本
type: <MODEL|SIGNAL|POSITION|RISK|EXECUTION|OBSERVE|STRATEGY>
description: "<描述>"
created_at: "2026-06-24T12:00:00Z"
created_by: "system"
hash: "<auto-computed>"
status: "<DRAFT|ACTIVE|ARCHIVED|DEPRECATED>"

# 类型特定字段（各 Package 自己定义）
config:
  ...
```

#### 4.1.3 Package 基类

```python
# asset_package/base.py
class AssetPackage(ABC):
    """统一 Package 基类"""
    type: PackageType
    name: str
    version: str
    config: Dict[str, Any]

    def to_manifest(self) -> Dict[str, Any]: ...
    def from_manifest(self, manifest: Dict) -> "AssetPackage": ...
    def compute_hash(self) -> str: ...
    def save(self, storage: PackageStorage) -> str: ...
    @classmethod
    def load(cls, storage: PackageStorage, name: str, version: str) -> "AssetPackage": ...
```

#### 4.1.4 ref 引用格式

```
ref://<name>@<version>
```

示例：
- `ref://Momentum_LGBM@1.2.0`
- `ref://ProbabilitySignal@1.0`
- `ref://VolatilitySizing@2.0`

### 4.2 Signal Package 系统（P2）

#### 4.2.1 SignalPackage 基类

```python
# asset_package/types/signal.py
class SignalPackage(AssetPackage):
    """信号包基类"""
    type = PackageType.SIGNAL

    @abstractmethod
    def generate(self, predictions: pd.Series, metadata: Dict) -> List[Signal]:
        """根据模型预测值生成信号"""
        ...
```

#### 4.2.2 五种 Signal 实现

| 实现名 | 说明 | 关键参数 |
|--------|------|---------|
| `ThresholdSignal` | 阈值信号（pred > long_threshold → BUY） | long_threshold, short_threshold, use_short |
| `ProbabilitySignal` | 概率信号（分类模型专用） | buy_threshold, sell_threshold |
| `TrendSignal` | 趋势信号（MA 交叉） | fast_window, slow_window |
| `RankingSignal` | 排序信号（多品种横截面排序） | top_pct, bottom_pct |
| `EnsembleSignal` | 集成信号（多模型投票） | models: List[ref], vote_threshold |

#### 4.2.3 manifest 示例

```yaml
# storage/asset_packages/signal/ThresholdSignal@1.0/manifest.yaml
id: ThresholdSignal@1.0
name: ThresholdSignal
version: "1.0"
type: SIGNAL
description: "阈值信号：pred > long_threshold → BUY"
config:
  long_threshold: 0.02
  short_threshold: -0.02
  use_short: true
created_at: "2026-06-24T12:00:00Z"
hash: "<auto>"
```

### 4.3 Position Package 系统（P2）

#### 4.3.1 PositionPackage 基类

```python
# asset_package/types/position.py
class PositionPackage(AssetPackage):
    """仓位包基类"""
    type = PackageType.POSITION

    @abstractmethod
    def size(self, signals: List[Signal], capital: float, market_data: pd.DataFrame) -> Dict[str, float]:
        """根据信号计算仓位"""
        ...
```

#### 4.3.2 五种 Position 实现

| 实现名 | 说明 | 关键参数 |
|--------|------|---------|
| `FixedSizing` | 固定仓位 | base_size |
| `ConfidenceSizing` | 置信度映射 | confidence_scale, max_size |
| `VolatilitySizing` | 波动率调整 | target_volatility, vol_lookback |
| `KellySizing` | 凯利公式 | kelly_fraction, win_rate, win_loss_ratio |
| `RiskParitySizing` | 风险平价 | target_risk_contribution |

### 4.4 Risk Package 系统（P2）

#### 4.4.1 RiskPackage 基类

```python
# asset_package/types/risk.py
class RiskPackage(AssetPackage):
    """风控包基类"""
    type = PackageType.RISK

    @abstractmethod
    def apply(self, positions: Dict[str, float], portfolio_state: Dict) -> Dict[str, float]:
        """应用风控规则，返回调整后的仓位"""
        ...
```

#### 4.4.2 五种 Risk 实现

| 实现名 | 说明 | 关键参数 |
|--------|------|---------|
| `MaxPositionRisk` | 单品种仓位上限 | max_position, max_portfolio |
| `StopLossRisk` | 止损 | stop_loss_pct, trailing |
| `TakeProfitRisk` | 止盈 | take_profit_pct |
| `MaxDrawdownRisk` | 最大回撤保护 | max_drawdown, drawdown_cutoff |
| `ExposureLimitRisk` | 敞口限制 | max_gross, max_net |

### 4.5 Execution Profile 系统（P2）

#### 4.5.1 ExecutionProfile 基类

```python
# asset_package/types/execution.py
class ExecutionProfile(AssetPackage):
    """执行配置包基类"""
    type = PackageType.EXECUTION

    @abstractmethod
    def create_broker(self, config: Dict) -> "Broker":
        """创建对应的 Broker 实例"""
        ...
```

#### 4.5.2 四种 Execution 实现

| 实现名 | 说明 | 对接 |
|--------|------|------|
| `PaperExecution` | 模拟交易 | execution/paper/ |
| `BinanceExecution` | 币安实盘 | execution/broker/binance.py |
| `ReplayExecution` | 回放模式 | execution/fidelity/replay.py |
| `BacktestExecution` | 回测模式 | execution/fidelity/ |

### 4.6 Observe Profile 系统（P2）

#### 4.6.1 ObserveProfile 基类

```python
# asset_package/types/observe.py
class ObserveProfile(AssetPackage):
    """观察配置包基类"""
    type = PackageType.OBSERVE

    @abstractmethod
    def get_metrics(self) -> List[str]:
        """返回需要监控的指标列表"""
        ...
```

#### 4.6.2 两种 Observe 实现

| 实现名 | 说明 | 监控指标 |
|--------|------|---------|
| `StandardObserve` | 标准观察（低频） | Daily Return, Factor Exposure, Drawdown |
| `HFObserve` | 高频观察 | Order Timeline, Latency, Fill Rate, Slippage |

### 4.7 Strategy Package（.qlstrategy）（P3）

#### 4.7.1 目录结构

```
storage/asset_packages/strategy/Momentum_LGBM_v2@2.0/
  manifest.yaml      # 全是 ref 引用
  artifacts/
    dependency_graph.json   # 依赖图快照
    validation_report.json  # 验证报告
```

#### 4.7.2 manifest.yaml schema

```yaml
# Momentum_LGBM_v2@2.0/manifest.yaml
id: Momentum_LGBM_v2@2.0
name: Momentum_LGBM_v2
version: "2.0"
type: STRATEGY
description: "动量+LGBM策略v2"
family: Momentum
status: candidate          # candidate → validated → deployed
validation: PASS           # PASS / FAIL / PENDING

# 全是 ref 引用，不复制数据
model: ref://Momentum_LGBM@1.2.0
signal: ref://ProbabilitySignal@1.0
position: ref://VolatilitySizing@2.0
risk: ref://CryptoBasicRisk@1.1
execution: ref://PaperExecution@1.0
observe: ref://StandardObserve@1.0

# 构建元信息
created_at: "2026-06-24T12:00:00Z"
created_by: "system"
hash: "<auto-computed>"
```

#### 4.7.3 StrategyPackage 类

```python
# asset_package/types/strategy.py
class StrategyPackage(AssetPackage):
    """策略包"""
    type = PackageType.STRATEGY
    family: str
    status: str  # candidate / validated / deployed
    validation: str  # PASS / FAIL / PENDING

    # ref 引用
    model_ref: str       # ref://Momentum_LGBM@1.2.0
    signal_ref: str
    position_ref: str
    risk_ref: str
    execution_ref: str
    observe_ref: str
```

### 4.8 Strategy Studio 后端（P4）

#### 4.8.1 Dependency Resolver（依赖解析器）

```python
# strategy_studio/resolver.py
class DependencyResolver:
    """依赖解析器"""

    def resolve(self, strategy_manifest: Dict) -> DependencyGraph:
        """
        解析策略的所有依赖，形成依赖图

        Strategy → Model → FeatureSet → Dataset
                 → Signal
                 → Position
                 → Risk
                 → Execution
                 → Observe
        """
        ...

    def validate(self, graph: DependencyGraph) -> ValidationResult:
        """验证所有依赖是否存在、版本是否匹配"""
        ...
```

#### 4.8.2 Composer（装配器）

```python
# strategy_studio/composer.py
class StrategyComposer:
    """策略装配器"""

    def compose(self, request: ComposeRequest) -> StrategyPackage:
        """
        装配流程：
        1. 解析所有 ref 引用
        2. 构建依赖图
        3. 验证依赖完整性
        4. 生成 StrategyPackage
        5. 保存到 storage
        """
        ...
```

#### 4.8.3 Validator（验证器）

```python
# strategy_studio/validator.py
class StrategyValidator:
    """策略验证器"""

    def validate(self, strategy: StrategyPackage) -> ValidationReport:
        """
        验证流程：
        1. 依赖完整性检查
        2. Paper Smoke Test（100 bar 模拟运行）
        3. 检查 Order/Position/PnL/Risk 是否正常
        """
        ...
```

#### 4.8.4 REST API

```
POST /api/strategy-studio/compose      # 装配策略
POST /api/strategy-studio/validate     # 验证策略
GET  /api/strategy-studio/strategies   # 策略列表
GET  /api/strategy-studio/strategies/{id}  # 策略详情
GET  /api/strategy-studio/dependencies/{id}  # 依赖图
```

### 4.9 Strategy Studio 前端（P5）

#### 4.9.1 装配流程 UI

```
[选择 Model] → [选择 Signal] → [选择 Position] → [选择 Risk]
    → [选择 Execution] → [选择 Observe] → [Preview] → [Validate] → [Build]
```

#### 4.9.2 组件结构

```
StrategyStudio.vue
  ├── ModelSelector.vue       # 选择 ModelPackage
  ├── SignalSelector.vue      # 选择 SignalPackage
  ├── PositionSelector.vue    # 选择 PositionPackage
  ├── RiskSelector.vue        # 选择 RiskPackage
  ├── ExecutionSelector.vue   # 选择 ExecutionProfile
  ├── ObserveSelector.vue     # 选择 ObserveProfile
  ├── DependencyGraph.vue      # 依赖图可视化
  ├── ValidationReport.vue     # 验证报告
  └── StrategyList.vue         # 已装配策略列表
```

### 4.10 Strategy Runtime 解释器（P6）

```python
# strategy_studio/runtime.py
class StrategyRuntime:
    """策略运行时解释器"""

    def load(self, strategy_id: str) -> LoadedStrategy:
        """
        解释 manifest 并加载各组件：
        1. 解析 manifest
        2. 加载 Model（从 ref）
        3. 加载 Signal（从 ref）
        4. 加载 Position（从 ref）
        5. 加载 Risk（从 ref）
        6. 加载 Execution（从 ref）
        7. 加载 Observe（从 ref）
        """
        ...

    def run(self, strategy: LoadedStrategy, market_data: pd.DataFrame) -> RunResult:
        """
        运行策略：
        1. Model.predict() → predictions
        2. Signal.generate(predictions) → signals
        3. Position.size(signals) → positions
        4. Risk.apply(positions) → adjusted_positions
        5. Execution.execute(adjusted_positions) → orders
        6. Observe.record(...) → metrics
        """
        ...
```

---

## 五、实施顺序

```
P1 (基础) → P2 (组件包) → P3 (策略包格式) → P4 (装配器后端) → P5 (前端) → P6 (Runtime)
                                                              ↘ 可并行
```

### 5.1 实施步骤

| 步骤 | 子项目 | 验证方式 |
|------|--------|---------|
| 1 | P1：Asset Package 标准化 | 单元测试：创建/保存/加载 Package |
| 2 | P2：Signal/Position/Risk/Execution/Observe Package | 单元测试：每种实现生成/计算正确 |
| 3 | P3：.qlstrategy 包格式 | 单元测试：StrategyPackage 序列化/反序列化 |
| 4 | P4：Strategy Studio 后端 | 集成测试：compose → validate → build 全流程 |
| 5 | P5：Strategy Studio 前端 | 手动验证：UI 装配流程 |
| 6 | P6：Strategy Runtime | 集成测试：load → run 全流程 |

### 5.2 现有代码清理

重写替换 `ml/strategy/` 模块：

**删除文件**：
- `ml/strategy/signal_generator.py`
- `ml/strategy/position_sizer.py`
- `ml/strategy/risk_overlay.py`
- `ml/strategy/ml_strategy.py`
- `ml/strategy/strategy_builder.py`
- `ml/strategy/backtest_adapter.py`
- `ml/strategy_builder/builder.py`

**更新文件**：
- `ml/__init__.py`：移除旧导出
- `ml/strategy/__init__.py`：清空旧导出
- `api/ml.py`：`/ml/strategies` 端点改为调用 Strategy Studio

---

## 六、数据结构汇总

### 6.1 PackageType 枚举

```python
class PackageType(str, Enum):
    MODEL = "MODEL"
    SIGNAL = "SIGNAL"
    POSITION = "POSITION"
    RISK = "RISK"
    EXECUTION = "EXECUTION"
    OBSERVE = "OBSERVE"
    STRATEGY = "STRATEGY"
```

### 6.2 Signal 数据结构

```python
@dataclass
class Signal:
    symbol: str
    side: SignalSide  # BUY / SELL / HOLD
    score: float       # 置信度 0~1
    prediction: float   # 原始预测值
    timestamp: str
    metadata: Dict[str, Any]
```

### 6.3 ComposeRequest

```python
@dataclass
class ComposeRequest:
    name: str
    family: str
    version: str = "1.0"
    model_ref: str           # ref://Momentum_LGBM@1.2.0
    signal_ref: str
    position_ref: str
    risk_ref: str
    execution_ref: str
    observe_ref: str
    description: str = ""
```

---

## 七、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 重写替换破坏现有回测 | 高 | 保留旧代码到 `ml/strategy_legacy/` 备份，新代码就绪后切换 |
| 范围过大 | 高 | 分阶段验证，每个 P 完成后测试 |
| Execution 对接复杂 | 中 | P6 先对接 PaperExecution，其他后续迭代 |
| 前端工作量大 | 中 | P5 复用现有 Selector 组件模式 |

---

## 八、验收标准

- [ ] P1：能创建/保存/加载所有类型 Package
- [ ] P2：每种 Signal/Position/Risk/Execution/Observe 至少 2 种实现可用
- [ ] P3：.qlstrategy 包能正确序列化/反序列化
- [ ] P4：compose → validate → build 全流程跑通
- [ ] P5：前端能完成完整装配流程
- [ ] P6：Runtime 能加载策略并运行 Paper Smoke Test
- [ ] 旧 `ml/strategy/` 代码全部清理
- [ ] `api/ml.py` 的 `/ml/strategies` 端点切换到 Strategy Studio

---

## 九、文档更新

完成后更新以下文档：
- `docs/plans/2026-06-24-strategy-studio.md`（本文档，标记完成状态）
- `AGENTS.md`（如有架构约定变更）

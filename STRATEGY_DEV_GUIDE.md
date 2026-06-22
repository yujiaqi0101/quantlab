# QuantLab 量化策略开发手册

> 本手册面向**基于** **`quantlab`** **框架开发新策略**的工程师。所有规则都对应到框架里的具体接口和已知坑，不写"应该如何工作"的废话，只写"必须这样写否则就跑不通 / 会出错"的硬约束。

***

## 0. 阅读对象 & 必读前提

- 已经阅读过 [`README.md`](./README.md)，理解 `Strategy → PortfolioConstructor → Execution → Engine → TradeBook` 的分层。
- 已经跑过 `python main.py` 至少一次，能看到 12 个 Stage 的输出。
- 本手册**不**讲解投资理念、不教你选股、不背指标公式；只约束**和框架的契约**。

***

## 1. 策略开发总流程（推荐顺序）

按这个顺序开发可以少踩 90% 的坑：

```
1. 写策略类       quantlab.signals.SignalStrategy 子类
2. 跑单次回测     BarEngine + Experiment + Report
3. 跑一致性       ValidationRunner(fast=VectorBT, precise=EventEngine)
4. 网格搜索       Optimizer 或 FastOptimizer
5. (可选) 并行    ParallelOptimizer
6. 滚动验证       WalkForward / WalkForwardRunner
7. 入库           ExperimentTracker
8. (可选) 灰度    LiveEngine + PaperBroker
```

**严禁**跳过第 2 步直接做第 4 步 —— 没有 baseline 的网格搜索毫无意义。

***

## 2. 文件 / 目录组织

### 2.1 推荐布局

```
my_strategies/
├── __init__.py
├── trend/
│   ├── __init__.py
│   ├── ma_cross.py              # MACrossStrategy
│   └── dual_thrust.py
├── mean_reversion/
│   ├── __init__.py
│   └── boll_band.py
├── factors/
│   ├── __init__.py
│   └── my_custom_factor.py      # 自定义因子
├── constructors/
│   ├── __init__.py
│   └── risk_parity.py           # 自定义 PortfolioConstructor
└── pipelines/
    └── run_experiment.py        # 调 Engine/Optimizer/Tracker
```

### 2.2 命名规范

| 类别     | 风格                               | 示例                                             |
| ------ | -------------------------------- | ---------------------------------------------- |
| 策略类    | PascalCase + `Strategy` 后缀       | `MACrossStrategy`、`BollingerReversionStrategy` |
| 策略文件   | snake\_case，与类名对应                | `ma_cross.py` 对应 `MACrossStrategy`             |
| 因子函数   | snake\_case，动词或名词                | `atr()`、`rsi()`、`volatility_breakout()`        |
| 因子文件   | snake\_case                      | `volatility_breakout.py`                       |
| 构造器类   | PascalCase + `Constructor` / 直接名 | `EqualWeight`、`TopN`、`RiskParity`              |
| 参数 key | 简短小写下划线                          | `fast`、`slow`、`n_top`、`position_tolerance`     |
| **strategy 注册名（V3.4）** | PascalCase，无后缀 | `"MACross"` / `"RSI"` / `"Alpha001"`（**注册名不要带 `Strategy` 后缀**） |
| **account_id（V3.4）**     | `acc_<risk>` 或 `<venue>_<risk>` | `acc_low` / `acc_mid` / `acc_high` / `ibkr_low` |
| **runtime_id（V3.4）**     | `rt_<strategy_id>`              | `rt_macross_low` / `rt_alpha_high`              |

> **V3.4 新约束**：`strategy_id` 全局唯一（在 `PortfolioSupervisor` 内不重复），`account_id` 全局唯一。两个 ID 是路由键，命名混乱会导致 `OrderRouter` 找不到目标。

### 2.3 严禁

- 不要把策略和业务脚本混在 `quantlab/` 里。`quantlab/` 是框架代码，**只读不改**。
- 不要在策略文件里写 `print()` 调试。用 `logging` 或 `ExperimentResult.extras`。
- 不要把数据 CSV 放在策略目录里。统一放 `data/`。

***

## 3. 策略类的硬约束

### 3.1 必须继承 `quantlab.signals.SignalStrategy`

```python
# 正确
from quantlab.signals.base import SignalStrategy

class MyStrategy(SignalStrategy):
    ...

# 也对（_compat 兼容旧路径）
from quantlab.strategy import SignalStrategy

# 错误
class MyStrategy:        # 没继承，Optimizer 会拿不到 .signal
    def signal(self, ctx): ...
```

新代码**统一走子包**：`quantlab.signals.base`、`quantlab.signals.ma_cross`。`quantlab.strategy` 那个顶层模块是 V1 旧路径，框架虽然通过 `_compat.py` 兼容，但**不再推荐**。

### 3.2 构造函数：参数必须可被 `int/str` 序列化

`ParallelOptimizer` 走子进程，策略实例是**按 class 全限定名 + 关键字参数构造**的：

```python
# worker 端伪代码
mod = importlib.import_module(strategy_path)        # e.g. "my_strategies.trend.dual_thrust"
cls = getattr(mod, strategy_cls_name)              # e.g. "DualThrustStrategy"
strategy = cls(**params)                            # 所以参数必须能 JSON 序列化
```

**硬约束**：

- 参数值类型限定为：`int / float / bool / str / list / dict / tuple / None`。
- **禁止**在 `__init__` 里传入文件句柄、数据库连接、DataFrame、网络 client 等。
- 如果一定要带不可序列化状态（比如模型权重），在 `.signal()` 里**懒加载**，并在文档里写清楚。

```python
# 错误示范
class BadStrategy(SignalStrategy):
    def __init__(self, model_path):
        self.model = load_model(model_path)   # 模型对象不可序列化

# 正确
class GoodStrategy(SignalStrategy):
    def __init__(self, model_path):
        self.model_path = model_path          # 只存路径

    def _get_model(self):
        return load_model(self.model_path)    # 用时再加载
```

### 3.3 `.signal(ctx)` 的签名与返回

```python
def signal(
    self,
    ctx: StrategyContext
) -> pd.DataFrame:
    """
    Returns
    -------
    pd.DataFrame
        index   = DatetimeIndex
        columns = symbol（与 ctx.data.keys() 一致）
        values  ∈ {-1, 0, 1}
    """
```

**必须**：

1. 返回**完整** `DataFrame(date × symbol)`，每个 `ctx.data` 里出现过的 symbol 都必须有列。
2. 取值 ∈ `{-1, 0, 1}`。**1=做多，0=空仓，-1=做空**（-1 暂不强用，但接口留好）。
3. 不要做"延迟一档"的操作 —— 引擎里 `signal.iloc[i-1]` 已经替你在用上一根 bar 的信号，**不要在策略里再 shift(-1)**。
4. 不要直接修改 `ctx.data` / `ctx.cache` 之外的对象（不要写文件、不要起线程）。

**禁止**：

1. 在 `.signal()` 里访问 `current_time / next_bar / 实时数据` —— 一律基于 `ctx.data` 的历史 OHLCV。
2. 在 `.signal()` 里做"过拟合陷阱"操作：未来函数、`lookahead`、`leakage`（见 §11）。
3. 用 `print` 写大段日志（多标的 + 长 bar 序列会刷屏 100MB）。

### 3.4 多标的遍历模板

```python
def signal(self, ctx) -> pd.DataFrame:
    out = {}
    for sym in ctx.data:
        out[sym] = self._signal_one(ctx, sym)
    return pd.DataFrame(out)        # 列顺序 = ctx.data.keys() 顺序
```

> **坑**：直接 `pd.DataFrame({sym: ... for sym in ctx.data})` 没问题，但**不要**用 `pd.concat` 把 Series 拼起来 —— 当某些 symbol 的 `index` 不完全一致时，会拉齐成空值。

### 3.5 单标的 / 跨标的：API 一致

`SignalStrategy` **不区分**单标和多标；单标就传一个 symbol 进去，`ctx.data` 是 `{"AAPL": df}`。

不要写"两个版本"的策略类：

```python
# 错误：拆成单标/多标两套
class MACrossSingleStrategy(SignalStrategy): ...
class MACrossMultiStrategy(SignalStrategy): ...

# 正确：统一一个，ctx.data 几个 symbol 都能跑
class MACrossStrategy(SignalStrategy): ...
```

***

## 4. 因子开发规则

### 4.1 必须使用内置因子库

当前已注册：

| 函数                                                         | 签名                                              |
| ---------------------------------------------------------- | ----------------------------------------------- |
| `ma(ctx, sym, period)`                                     | 简单均线                                            |
| `atr(ctx, sym, period=14)`                                 | 真实波幅均值                                          |
| `boll(ctx, sym, period=20, num_std=2, return_tuple=False)` | 布林带；`return_tuple=True` 返 `(mid, upper, lower)` |
| `rsi(ctx, sym, period=14)`                                 | RSI(0\~100)                                     |

**不要**绕过 `quantlab.factors` 自己写 `df['close'].rolling(20).mean()` —— 这样**不命中 cache**，12 组参数跑 12 次。

```python
# 错误
def my_signal(self, ctx):
    ma20 = ctx.data["AAPL"]["close"].rolling(20).mean()   # 不走 cache

# 正确
from quantlab.factors.ma import ma
def my_signal(self, ctx):
    ma20 = ma(ctx, "AAPL", 20)                            # 自动 cache
```

### 4.2 写自定义因子的契约

```python
# quantlab/factors/my_factor.py
def my_factor(ctx, symbol, period, *, num_std=2.0):
    key = f"my_factor_{symbol}_{period}_{num_std}"
    val = ctx.cache.get(key)
    if val is None:
        close = ctx.data[symbol]["close"]
        val = close.rolling(period).std() * num_std + close
        ctx.cache.set(key, val)
    return val
```

**必须**：

- cache key 包含 **symbol + 所有数值参数**（周期、阈值、K 系数、上下轨等）。
- 第一次计算后写 cache，下一次 `ctx.cache.get(key)` 直接命中。
- 因子函数**不接受** `int` 之外的可变状态（不要绑定 `self.xxx`）。

**禁止**：

- 不要把 cache key 写得太粗：`key="my_factor"` 会让 `AAPL` 命中 `MSFT` 的结果。
- 不要把 cache key 写得太细：`key=f"my_factor_{id(ctx)}_{id(sym)}"` 会让 cache 完全失效。

### 4.3 自定义因子的命名空间

为了避免和框架冲突，**强烈建议**在函数名前加前缀：

```python
# my_factor_*
def my_factor_breakout(ctx, sym, n): ...
def my_factor_skew(ctx, sym, n): ...
```

### 4.4 `factor_cache` 全局状态

`factor_cache` 是 **module-level singleton**（见 `quantlab/data/cache.py`）。它的语义是「在同一份数据上，多次构造同一策略时，重复使用同一份因子结果」。

**坑**：

- 跨**不同长度**的数据（WalkForward 不同窗口、不同策略不同数据切片）必须 `clear()`，否则 `ma(60)` 算在 200 根数据上，下次 80 根的窗口会**直接返回 200 根的 Series** 引发 `Can only compare identically-labeled Series`。
- `ParallelOptimizer` 内部每次 `_evaluate_one` 都会 `clear()`，不要自己再 clear 一次把这次命中的也清了。
- 如果你写了"先看一部分数据做特征、然后追加新数据"的增量式策略，**自己管 cache**（不要在策略里调 `factor_cache.clear()`）。

***

## 5. 组合构建（PortfolioConstructor）规则

### 5.1 内置实现

- `EqualWeight()`：所有 `score > 0` 的 symbol 等权 `1/N`。
- `TopN(n=2)`：取 score 降序前 N 个，等权 `1/N`。

**绝大多数策略组合构建直接用** **`TopN(n=2~5)`** **就够了**，不要过早地造自己的构造函数。

### 5.2 何时该写自定义构造函数

只有当策略有**结构性约束**时才写：

- 行业 / 板块中性（不允许同一行业占比 > X%）
- 单标的最大权重限制（默认等于 `1/TopN`）
- 多空对冲（long-only / long-short / market-neutral）
- 资金利用率约束（cash buffer ≥ 5%）
- 风险平价（`RiskParity`）

### 5.3 自定义构造函数模板

```python
# quantlab/portfolio_construction/my_constructor.py
from .base import PortfolioConstructor
from .target_portfolio import TargetPortfolio

class MaxSectorConstraint(PortfolioConstructor):
    """
    行业敞口 ≤ 60%，溢出按等权保留
    行业映射外部传入（不是策略责任）
    """
    def __init__(self, sector_map: dict, max_sector_weight=0.6, base=None):
        self.sector_map = sector_map
        self.max = max_sector_weight
        self.base = base or TopN(n=2)        # 默认走 TopN

    def construct(self, scores, timestamp):
        base_target = self.base.construct(scores, timestamp)
        # ... 自己的裁剪逻辑 ...
        return TargetPortfolio(timestamp, weights)
```

**必须**：

- 返回的 `TargetPortfolio.weights` **所有值 ≥ 0**（V1 验证器会抛 `ValueError`）。
- 总权重不必 == 1.0。允许保留现金（小于 1 意味着 hold cash）。`Engine` 不会动你的 cash buffer。
- `construct()` 是**无状态**的，不要存历史信息（如果要，写到 `self` 上并标明）。

***

## 6. 执行模型（Execution / Slippage / Commission）规则

### 6.1 默认配置

```python
from quantlab.execution import (
    PercentageCommission, PercentageSlippage, TargetWeightExecution,
)

commission = PercentageCommission(rate=0.0003)   # 3 bps
slippage   = PercentageSlippage(rate=0.0002)     # 2 bps
execution  = TargetWeightExecution(
    lot_size=1,                 # 股票 1 手，crypto 0.001
    position_tolerance=0.02,    # 2% 内不调仓（避免无效换手）
)
```

### 6.2 滑点 / 佣金的现实意义

- 美股股票：佣金 `0.0001~0.0003`，滑点 `0.0001~0.0002`。
- 数字货币：佣金 `0.001` (Binance taker)，滑点 `0.0005~0.002`。
- 国内股票：佣金 `0.0003`，滑点 `0.001`（涨跌停更难成交）。

**禁止**：

- 把 `rate=0.0` 当成"我不在意外部成本" —— 永远至少加 `1bps` 滑点，否则回测就是过拟合。
- 把 `slippage` 调成 `0.01` (1%) 当作"保守测试" —— 这是用错误参数做反例。滑点应该和**品种 + 流动性**绑定。

### 6.3 `TargetWeightExecution` 的关键参数

| 参数                   | 默认   | 含义                           |
| -------------------- | ---- | ---------------------------- |
| `lot_size`           | 1    | 委托取整（股票 100，crypto 0.0001）   |
| `position_tolerance` | 0.02 | 已有仓位与目标差距 < 2% 时不调仓（省手续费）    |
| `cash_buffer`        | 0.0  | 目标 cash 比例（0.05 = 永远留 5% 现金） |

> **坑**：`position_tolerance` 太大 → 策略"装死"几乎不调仓；太小 → 每根 bar 都换手，回测过载且手续费爆表。建议 `0.01~0.05` 之间。

***

## 7. 参数约定

### 7.1 参数必须可序列化

- ✅ `int / float / bool / str / tuple / list[基本类型] / dict[str,基本类型]`
- ❌ `pd.DataFrame / np.ndarray / 任意自定义类 / 函数 / lambda`

### 7.2 参数命名规范

| 类别   | 命名                      | 备注        |
| ---- | ----------------------- | --------- |
| 周期   | `n / period / lookback` | 一定要 `int` |
| 阈值   | `threshold / bound`     | 浮点        |
| K 系数 | `k / num_std`           | 浮点        |
| 开关   | `use_xxx / enable_xxx`  | bool      |
| 字符串  | `mode / side`           | 离散枚举      |

### 7.3 参数网格搜索的颗粒度

**严禁**一次性搜几十个超参 —— 自由度膨胀，3 次随机种子都过不了。

| 策略类型  | 建议参数数                          |
| ----- | ------------------------------ |
| 简单趋势  | 2\~3                           |
| 中等复杂  | 3\~5                           |
| 多因子融合 | 5\~8（**且** 必须有 WalkForward 验证） |

### 7.4 参数 dict 的可读性

```python
# 好
param_space = {
    "fast":   [5, 10, 20, 30],
    "slow":   [30, 60, 90, 120],
    "top_n":  [2, 3, 5],
}

# 差
param_space = {
    "a": [5, 10, 20, 30],
    "b": [30, 60, 90, 120],
    "c": [2, 3, 5],
}
```

***

## 8. 引擎选择规则

### 8.1 什么时候用哪个

| 引擎                   | 用途                                                     |
| -------------------- | ------------------------------------------------------ |
| `BarEngine`          | **默认 / 验证基线**。最精确，多标的 + 组合构建层全流程都支持。                   |
| `EventEngine`        | 几乎和 BarEngine 等价，主要用于需要接入 EventBus / RiskManager 的场景。  |
| `TickEngine`         | 需要 tick 级精度（涨跌停、市价单瞬时滑点）的研究。V1 不支持限价单/部分成交。            |
| `VectorBTAdapter`    | 大规模网格搜索（几百\~几千组参数），**结果不能作为最终结论**，必须再用 EventEngine 验证。 |
| `SubprocessVectorBT` | 在 VBT + numba 可能崩溃的环境（沙箱、IDE）冒烟。                       |

### 8.2 双引擎一致性是硬指标

```python
runner = ValidationRunner(
    fast_engine=VectorBTAdapter(constructor=TopN(n=2)),
    precise_engine=build_event_engine(),     # BarEngine / EventEngine
    consistency_threshold=0.8,
)
```

**规则**：

- `consistency < 0.8` 的参数组**直接淘汰**，不要再花时间调优。
- 这是**最低成本**的"反过拟合"工具。V1 时代没有这一步，吃过亏。

### 8.3 并行优化

```python
opt = ParallelOptimizer(
    strategy_cls=MyStrategy,
    engine_spec=("vectorbt", {"fees": 0.0003, "slippage": 0.0002}),
    max_workers=4,
    top_k=5,                  # 只保留 Sharpe 最高的 5 组
    early_split=0.3,          # 前 30% 数据先跑
)
```

**规则**：

- `max_workers ≤ CPU 核数`。
- `top_k ≤ 总参数组合 / 10`，否则没意义。
- 子进程在 Windows 上开销大，< 50 组参数**别用**。
- VBT 偶发 SIGABRT：设 `os.environ["PARALLEL_USE_THREAD"] = "1"` 切 ThreadPool。

***

## 9. WalkForward 规则

### 9.1 必须用 V2.2 `WalkForwardRunner`

旧 V1 `WalkForward` 是按 bar 滚动，**没有 val 阶段、没有 stability、没有 HTML 报告**。新策略**只准用 V2.2**。

### 9.2 参数

| 参数            | 建议   | 含义                               |
| ------------- | ---- | -------------------------------- |
| `train_years` | 2\~4 | 训练窗口年数                           |
| `test_years`  | 1    | OOS 测试窗口年数                       |
| `top_train`   | 3\~5 | train 段选 top K                   |
| `top_val`     | 1    | val 段选 top 1（V2.2 默认 OOS 只用最优一组） |

### 9.3 验收指标

| 指标                | 通过线         |
| ----------------- | ----------- |
| `avg_test_sharpe` | ≥ 0.5       |
| `avg_test_max_dd` | ≤ 0.3       |
| `stability_score` | ≥ 0.6       |
| `parameter_drift` | 越小越好（< 0.3） |
| OOS 收益/IS 收益      | ≥ 0.5       |

**如果 OOS/IS < 0.3 ⇒ 几乎肯定是过拟合，扔掉。**

***

## 10. 实验入库 & 命名

### 10.1 `ExperimentRecord` 字段

```python
from quantlab.research.tracker import ExperimentRecord

record = ExperimentRecord(
    name="ma_cross_v3_slow60",          # 必须：版本号 + 关键参数
    strategy_name="MACross",            # 必须在 strategy_registry 里
    params={"fast": 10, "slow": 60},
    tag="trend_v1",                     # 业务/研究方向分组
    note="双均线，慢线 60，TopN=2，5y 数据",  # 自然语言
)
```

### 10.2 命名规范

```
{strategy_name}_v{N}_{key_param1}{value1}_{key_param2}{value2}
```

- ✅ `ma_cross_v3_slow60_topn2`
- ✅ `boll_revert_v2_std2_period20`
- ❌ `test1`, `exp_2026_03_01_v_final_FINAL`

### 10.3 入库 SOP

```python
tracker = ExperimentTracker(
    strategy_registry={"MACross": MACrossStrategy},
    db_path="storage/research.db",
)
tracker.run(record, engine, data)

# 跑完看 leaderboard
print(tracker.leaderboard(sort_by="sharpe", top=10))
```

每次跑完**必做**：

- `name` 不要重复（重复会被覆盖）。
- 把 `note` 写满，6 个月后你不会记得当时怎么想的。
- 不入库的实验 = 一次性回测，等于没做。

***

## 11. 严禁的反模式（过拟合陷阱）

以下操作**几乎一定导致过拟合**：

### 11.1 未来函数

- ❌ 在 `.signal()` 里用 `df['close'].shift(-1)`、`df['high'].iloc[i+1]`。
- ❌ 用 `df['close'].pct_change().shift(-1)` 当 label。
- ✅ 一切决策基于 `iloc[:i]` 或 `iloc[i]` 当根 bar 的数据。

### 11.2 偷看未来数据

- ❌ 用 `df['close'].max()` 当作"如果我当时在最高点卖出"的回测。
- ❌ `df['close'].iloc[-1]` 当入场价做"完美择时"测试。
- ❌ 用 `df['volume'] == df['volume'].max()` 选股 —— 这是看未来。

### 11.3 不当的 fill 处理

- ❌ 默认**次根 bar open** 成交却按 `close` 计收益。
- ❌ 假设"跌停也能成交"。

> 框架的 `BarEngine` 用 `close` 当 fill price；如果你希望 `next_open`，要么自己写撮合逻辑，要么接受这是已知简化（要在文档里写明）。

### 11.4 偷看 alpha

- ❌ 用 `df['close'].pct_change(5).shift(-5) > 0` 当 5 日后涨跌 label。
- ❌ 用 `df['close'].rolling(20).max()` 当阻力位 —— 这是已实现 high，不是未来阻力。

### 11.5 偷看换手

- ❌ 选 `(sharpe > 1) and (turnover < threshold)` 的参数组 —— 这是**回测的 2 次利用**，更严重点说是 P-Hacking。
- ✅ 用 **WalkForward** + **ValidationRunner** 缓解。

### 11.6 P-Hacking

- ❌ 跑 10000 组参数，挑 Sharpe 最高那组直接上线。
- ✅ 跑 10000 组 → WalkForward → 看 OOS 分布 → 取中位数参数。

### 11.7 偷看 survivorship

- ❌ 用"目前还在交易的"标的（已经死了的票不进样本）。
- ✅ 在数据层就**显式标注**："以下标的为现存样本，仅供研究"。

### 11.8 偷看停牌

- ❌ 默认"每天都有 close"。
- ✅ 自行处理停牌日（`close.isna()`），可参考：

```python
close = ctx.data[sym]["close"].ffill()        # 停牌日延续前一收盘
# 或者
df = df[df["volume"] > 0]                     # 直接剔除停牌日
```

### 11.9 V3.x 反模式（多策略/多账户/可观测）

- ❌ **共享 portfolio / factor_cache**（V3.4）：跨 `StrategyRuntime` 共享任何状态会让一个策略的调仓污染另一个。**每个 runtime 必须独立 `Portfolio` / `factor_cache`**。
- ❌ **绕过 `OrderRouter` 直连 broker**（V3.4）：破坏 allocation 拆单，子单不再带原 `client_order_id`，broker 判重失效。
- ❌ **在 strategy 层 `print` 调试**（V3.2 起）：用 `TradeLogger` 替代，否则 trace_id 关联不上，排查时间×5。
- ❌ **靠 `if mode == "live"` 切换逻辑**（V3.1）：`ExecutionFactory` 已经处理三模式，策略层不感知 mode。
- ❌ **Supervisor 直接改 runtime 内部状态**（V3.4）：违反"观察者 + 调度器"边界。Runtime 必须自治。
- ❌ **每个策略一套独立的 `client_order_id` 生成规则**（V3.1+）：框架已经 `Order.client_order_id` 自动生成 UUID，自己覆盖会破坏重放幂等性。
- ❌ **V3.3 不接 `SystemContext` 自己 import logger/tracer**（V3.2）：所有监控组件都从 `ctx.logger` / `ctx.tracer` 取，不要 `import` 跨模块。

***

## 12. 数值 / 边界约束

### 12.1 整数参数要变 int

`pandas` 读 `dict` 之后 `int` 会变 `float`，导致 `rolling(10.0)` 直接报错。Optimizer 内部已经做了 `int(v) if isinstance(v, float) and v.is_integer() else v` 的处理，**但你自己在策略里**也要小心：

```python
# 安全
def signal(self, ctx):
    period = int(self.period)   # 永远显式转
    return ma(ctx, sym, period)
```

### 12.2 NaN 处理

`ma(60).iloc[:60]` 是 NaN。比较 `ma(5) > ma(60)` 时，**前 60 根都是 0**（NaN 算 False）—— 这是默认行为，**不要用** **`fillna(0)`** **抹掉**，否则会做出"刚上市第一天就建仓"的错误。

### 12.3 极端值

- 涨跌幅 ≥ 20% 一定要标注，框架不会主动截断。
- 价格 < 0 在 `Tick.__post_init__` 抛 `ValueError`，但 `DataFrame` 级别不会校验。

### 12.4 时间戳对齐

多标的的 `DatetimeIndex` 必须**完全一致**。如果不一致，先重采样到统一频率：

```python
df = df.resample("1D").last().dropna()
```

***

## 13. 性能约束

| 场景             | 建议                                         |
| -------------- | ------------------------------------------ |
| 单次回测           | BarEngine / EventEngine < 5s               |
| 网格 100\~500 组  | VectorBTAdapter（单进程）或 ParallelOptimizer    |
| 网格 500\~5000 组 | ParallelOptimizer + early\_filter + top\_k |
| 网格 > 10000 组   | 必须先粗筛（early\_filter）再细跑                    |
| 因子预计算          | 大于 1e6 行的 close/rolling 改成 numpy           |

**禁止**：

- 在 `.signal()` 里 `print(ctx.data["AAPL"].head())`。
- 在 `.signal()` 里 `for sym in ctx.data: pd.read_csv(...)`（重复 IO）。
- 在 `.signal()` 里启线程（pandas 不是线程安全，会和你后续 `Portfolio.equity()` 数据竞争）。

***

## 14. 风控 & Live 上线规则

### 14.1 Paper 阶段强制要求

**禁止**跳过 Paper 直接接实盘 broker。Paper 至少跑 2 周、跨越至少 1 次完整调仓周期 + 1 次极端行情。

### 14.2 必加 RiskManager

```python
from quantlab.risk import (
    RiskManager, OrderSizeCheck, PositionLimitCheck,
    MaxOrderSize, MaxPositionLimit,
    EmergencyStop, KillSwitch,
)

rm = RiskManager()
rm.add_check(OrderSizeCheck(MaxOrderSize(max_qty=10000)))
rm.add_check(PositionLimitCheck([
    MaxPositionLimit(symbol=s, max_qty=10000) for s in data.keys()
]))

estop = EmergencyStop(threshold=-0.05)   # 单日 -5% 停机
rm.add_check(KillSwitch(estop))
```

**所有新策略上线必须**：

- 至少有 `OrderSizeCheck`。
- 至少有 `KillSwitch(estop)`。

### 14.3 KillSwitch 阈值

- 股票：日亏 `5%` 触发。
- 加密：日亏 `10%` 触发。
- 多标的组合：日亏 `3%` 触发（因为分散度低）。

### 14.4 V3.4 系统级 Kill Switch（`PortfolioSupervisor`）

`RiskManager` + `KillSwitch` 是**单 runtime** 风控。V3.4 `PortfolioSupervisor` 额外提供**系统级**兜底：任一 runtime 净值跌穿阈值 → 全部停。

```python
# PortfolioSupervisor.on_bar() 内置：
# 任意 runtime.last_equity < 80000 → global_kill_switch.set()
#  → 所有 runtime.stop() 被调
#  → 主循环退出
```

**多账户场景必加**：

- 阈值根据**每个账户**的 `initial_cash` 设（不要 hardcode `80000`）。
- 在 `AllocationEngine` 上挂"按 pnl 反比调权"逻辑（`DynamicAllocation` 雏形），输的账户少投。
- 把 `sup.global_kill_switch.is_set()` 放在主循环每根 bar 开头判断：

```python
for i, ts in enumerate(timestamps):
    if sup.global_kill_switch.is_set():
        logger.error(f"GLOBAL KILL: {sup.kill_reason}")
        break
    sup.on_bar(bar, ts)
```

### 14.5 V3.4 跨账户风控 SOP

- [ ] 每个 `Account` 有 `risk_profile` (`low` / `medium` / `high`)
- [ ] 系统级 Kill Switch 阈值与 `risk_profile` 绑定
  - low: `equity < 0.95 * initial_cash`
  - medium: `equity < 0.85 * initial_cash`
  - high: `equity < 0.7 * initial_cash`
- [ ] RiskManager 接入 OrderRouter 做 pre-submit 检查（V3.4 路线图）
- [ ] `AlertManager` 订阅 `sup.global_kill_switch` 事件，落 `FATAL` 级别告警

***

## 15. 单元测试 & 验证清单

提交策略前**必须**跑通以下 5 条：

- [ ] **T1 单次回测**：`Experiment.run` 不抛异常，`Report` 包含 `sharpe / max_dd / trade_count`。
- [ ] **T2 双引擎一致**：`ValidationRunner.consistency >= 0.8`。
- [ ] **T3 样本内 / 样本外**：用 70% 数据调参 + 30% 验证，OOS Sharpe ≥ 0.4。
- [ ] **T4 WalkForward**：`avg_test_sharpe ≥ 0.5` 且 `parameter_drift < 0.3`。
- [ ] **T5 入库**：`ExperimentTracker` 记录到 SQLite，leaderboard 能搜到。

附加检查：

- [ ] **T6 多标的对齐**：跑 5 个 symbol 时没有 NaN / 0 trade 异常。
- [ ] **T7 现金管理**：账户 `cash` 永远 ≥ 0。
- [ ] **T8 反向交易**：把策略的 signal 取反，收益应当反向（不严格，但 \~ -0.5 \~ -1.0）。
- [ ] **T9 滑点敏感性**：把 `slippage.rate` 从 `0.0001` 升到 `0.001`，Sharpe 下降 < 30%。
- [ ] **T10 手续费敏感性**：把 `commission.rate` 翻倍，Sharpe 下降 < 20%。

**V3.4 多策略/多账户必跑**（详见 [§19.8](#198-v34-必跑测试追加到-§15)）：

- [ ] **T11 多策略隔离**、**T12 OrderRouter 拆单**、**T13 client_order_id 幂等**、**T14 系统级 Kill Switch**、**T15 全局 PnL 报告**。

***

## 16. 调试技巧

### 16.1 最快的定位方法

1. **看** **`BacktestResult.error`** —— 引擎内部异常会塞到这里。
2. **看** **`BacktestResult.fills`** —— 是不是真的在按预期下单。
3. **看** **`TradeBook.closed_trades`** —— 平仓价格、时间、pnl 是不是你预期的。
4. **看** **`equity_curve`** —— 是不是单调上升 / 突然跳变。
5. **看** **`weights_df`** —— 权重是不是按信号走的。

### 16.2 我跑出来收益很高，怎么验证？

- 把 `commission.rate` 调成 `0.01`（100 bps），如果还赚钱 ⇒ 真有 alpha。
- 把 `slippage.rate` 调成 `0.01`，同上。
- 在数据最后 30% 上重跑，OOS 收益应该 ≥ IS 收益的 50%。
- 把 `TopN(n=2)` 换成 `TopN(n=1)`，看看是否退化（如果 TopN=1 还更好，**说明多标的存在虚假分散**）。
- 颠倒信号方向（`1 - signal`），如果还赚钱 ⇒ **数据有问题**。

### 16.3 我跑出来亏钱，怎么排查？

- 检查 `equity_curve` 是否从 0 起步、是否回到 baseline。
- 检查 `trade_count == 0`（没下单 ⇒ 策略没信号 / constructor 过滤掉了）。
- 检查 `weights_df` 是不是全 0（信号全是 0）。
- 用 `live/replay_market_data.py` 重放单标的，看每根 bar 的下单/成交。

### 16.4 V3.x 调试技巧

**1) V3.2 trace_id 串联**（找出"为什么这一笔亏钱"）：

```python
from quantlab.monitoring import EventTracer
tracer = EventTracer(log_path="logs/traces.jsonl")
# 找到亏钱的那笔 fill
trace = tracer.find_by_fill(fill_event)
# 拿全链路：market → signal → order → fill
for event in trace.events:
    print(event.type, event.timestamp, event.payload)
```

**2) V3.3 ReplayEngine 一致性**（怀疑账对不上时）：

```python
from quantlab.runtime import ReplayEngine
re = ReplayEngine(event_log="logs/events_paper.log", broker=paper_broker)
result = re.run(start_bar=0, end_bar=300)
# 如果 result.diffs > 0 → 本地 portfolio 状态和 broker 不一致
```

**3) V3.4 Supervisor 报表**（多策略对比）：

```python
sup.print_report()
# 看到 rt_alpha_high 净值爆掉 50% → 看 alpha_high 的 signal / weights
# 看每个 runtime 的 orders/fills/equity/pnl 是不是预期
```

**4) V3.4 Account 隔离校验**（怀疑资金污染）：

```python
total_cash = sum(a.cash for a in am.list_accounts())
# 应该 = sum(initial_cash) - sum(commission) - sum(realized_loss)
# 任何时刻不应有 < 0 的 cash
```

**5) V3.4 OrderRouter 拆单验证**（怀疑拆单错）：

```python
from quantlab.core.order import Order
test = Order(symbol="AAPL", quantity=1000, price=150.0)
routed = sup.router.route(test, "macross_low")
# macross_low → acc_low 60% + acc_mid 40% → 600/400
assert sum(r.quantity for r in routed) == 1000
assert all(r.client_order_id == test.client_order_id for r in routed)
```

***

## 17. 提交策略时的 Code Review 清单

PR 提交前自查：

- [ ] 策略类继承 `SignalStrategy`，文件路径正确（不在 `quantlab/` 内）。
- [ ] `__init__` 参数可 JSON 序列化。
- [ ] `.signal(ctx)` 返回完整 `DataFrame(date × symbol)`，取值 ∈ {-1, 0, 1}。
- [ ] 用了 `quantlab.factors.*` 因子，**不**手写 `rolling`。
- [ ] 自定义因子 cache key 包含 `symbol + 所有数值参数`。
- [ ] 没在策略里 `print` / 起线程 / 改全局状态。
- [ ] 没在 `.signal()` 里出现 `shift(-1)` / `iloc[i+1]` 等未来函数。
- [ ] 跑了 5 条核心测试（T1\~T5）。
- [ ] 入库了至少 1 条 `ExperimentRecord`，`note` 写满。
- [ ] 命名规范（PascalCase + Strategy、snake\_case 文件、版本号 name）。

### 17.1 V3.4 多策略/多账户额外检查

- [ ] `strategy_id` / `account_id` 全局唯一（不与现有冲突）。
- [ ] 注册名**不带** `Strategy` 后缀（`"MACross"`，不是 `"MACrossStrategy"`）。
- [ ] `sup.register_strategy(..., full_data=data)` 传了全量数据。
- [ ] `FixedAllocation` 权重和 = 1.0（构造时校验失败必须立刻看到）。
- [ ] 每个 runtime 独立 `Portfolio` / `broker`（没有共享对象）。
- [ ] 没有绕过 `OrderRouter` 直连 broker。
- [ ] 系统级 Kill Switch 阈值设到 `0.7 × initial_cash`（**不**用 hardcode `80000`）。
- [ ] `examples/run_multi_strategy.py` 跑通（300 bars, 全部 runtime 都有 fills）。
- [ ] 跑了 T11\~T15（多策略隔离、OrderRouter 拆单、client_order_id 幂等、Kill Switch、全局 PnL 一致性）。

***

## 18. 附录：常见错误速查

| 错误信息                                                  | 根因                                   | 修法                                |
| ----------------------------------------------------- | ------------------------------------ | --------------------------------- |
| `Can only compare identically-labeled Series objects` | `factor_cache` 跨窗口没清                 | `factor_cache.clear()`            |
| `KeyError: 'AAPL'` 在 signal 里                         | `ctx.data` 是 `OrderedDict`，键大小写敏感    | 检查 data dict 的 key                |
| `must be real number, not NoneType`                   | 指标首段（< period）是 NaN，参与了比较            | `fillna` 或用 `.iloc[period:]` 截断   |
| `unhashable type: 'dict'`                             | `__init__` 参数里塞了 dict 但 key 不是 str   | 改用 dataclass 或纯 dict\[str, 基本类型]  |
| `ValueError: position_tolerance`                      | tolerance < 0 或 >= 1                 | 范围 (0, 1)                         |
| `OSError: [Errno 28] No space left`                   | `BacktestResult.fills` 太大写到 `extras` | 关掉 `save_fills=True`              |
| `SIGABRT` 在子进程                                        | vectorbt + numba 崩溃                  | 切 ThreadPool 或 SubprocessVectorBT |
| `RuntimeError: generator raised StopIteration`        | 旧版 Python 兼容                         | 加 Python 3.7+                     |
| Sharpe 永远是 0                                          | 收益序列全是 0                             | 检查 `weights_df` 是不是全 0            |
| Win rate 永远是 100%                                     | `trade_count == 0`                   | 强制至少 1 笔交易做 sanity check          |

### 18.1 V3.x 错误速查

| 错误信息 | 根因 | 修法 |
|---------|------|------|
| `numpy.float64 has no attribute 'rolling'` | V3.4 `signal()` 算在单行 DataFrame 上 | `sup.register_strategy(..., full_data=data)` |
| `single positional indexer is out-of-bounds` | V3.4 `_bar_count - 2` 越过 signal 长度 | 已修复：`idx = min(bar_count-1, sig_len-1)`；升级 `runtime/strategy_runtime.py` |
| `ValueError: weights sum=X, must be 1.0` | `FixedAllocation` 校验失败 | 调整权重，让每个 strategy 权重和 = 1.0 |
| `KeyError: 'macross_low'` 在 router | `strategy_id` 没 `router.register_runtime` | 用 `sup.register_strategy()` 而不是手动构造 runtime |
| `KeyError: 'acc_low'` 在 router | `account_id` 没在 `AccountManager` 里 | `am.create_account("acc_low", ...)` 放在 register 前 |
| `RuntimeError: strategy_id X already registered` | 同一个 `strategy_id` 注册两次 | 检查 supervisor 主循环外的重复注册 |
| `global_kill_switch is set` 主循环卡住 | 某个 runtime 跌破阈值 | 检查 `sup.kill_reason`；调阈值到 `0.7 * initial_cash` |
| `client_order_id` 为空字符串 | 自己手工建 `Order` 没让框架生成 | 用 `Order(symbol=..., qty=..., ...)` 让 `__post_init__` 自动生成 UUID |
| `TradeLock acquire timeout` | 多线程同时改同一个 runtime 状态 | 改单线程跑；或者用 `with critical():` 包裹（V3.3） |
| `consistency issue: positions mismatch` (V3.3) | 本地 portfolio 和 broker 端对不上 | 看 `logs/consistency.log` 哪个 symbol 差，stop trading 调查 |
| `RuntimeError: consistency check failed` (V3.3) | 启动时对账失败 | 看 `RecoveryManager.report`；多半是 checkpoint 损坏 |

***

## 19. V3.4 多策略 × 多账户开发规范

> 适用场景：在 `PortfolioSupervisor` 下同时跑 ≥ 2 个策略或 ≥ 2 个账户。

### 19.1 什么时候用 V3.4

| 场景 | 推荐方案 |
|------|----------|
| 单策略 + 单账户 + 单引擎 | ❌ 用 V2.5 `LiveEngine` 或 `BarEngine`，不要套 V3.4 |
| 单策略 + 多账户（如 A/B 资金账号） | ✅ V3.4 `OrderRouter` 拆单 |
| 多策略 + 单账户 | ✅ V3.4 `StrategyRuntime` 隔离 |
| 多策略 + 多账户（机构 / 家庭账户） | ✅ V3.4 完整矩阵 |
| 跨账户调拨 / 资金再平衡 | ❌ V3.4 不内置，自己加 Transfer 模块 |

**判断标准**：只要超过 1 个 strategy **或** 超过 1 个 account，立刻用 V3.4。

### 19.2 状态隔离硬约束

**禁止**在多个 `StrategyRuntime` 之间共享任何以下对象：
- `Portfolio` / `Position` / `TradeBook` / `factor_cache`
- `execution` / `broker`
- 任何 `self.xxx` 上的可变状态

```python
# ❌ 错误：两个 runtime 共享一个 portfolio
shared_portfolio = Portfolio(initial_cash=200000)
rt_a = StrategyRuntime(strategy=A, portfolio=shared_portfolio, ...)
rt_b = StrategyRuntime(strategy=B, portfolio=shared_portfolio, ...)
#  → A 调仓时 B 也会被改；kill switch 状态混淆

# ✅ 正确：每个 runtime 独立
rt_a = StrategyRuntime(strategy=A, portfolio=Portfolio(100000), ...)
rt_b = StrategyRuntime(strategy=B, portfolio=Portfolio(100000), ...)
```

### 19.3 资金分配规则

```python
# 必须：每个 strategy 的权重和 = 1.0
ae = AllocationEngine(FixedAllocation({
    "macross_low": [("acc_low", 0.6), ("acc_mid", 0.4)],   # sum = 1.0
    "rsi_high":    [("acc_high", 1.0)],                     # sum = 1.0
}))
```

**禁止**：
- 让一个 strategy 跨 5 个账户（5% 起步 → 拆单精度爆炸，券商最小单笔 100 股时余量归到第一个账户）
- `FixedAllocation` 权重和 = 0.99（`ValueError` 拒绝构造）
- 在 runtime 内部**直接**调 `broker.submit_order` —— 必须走 `OrderRouter`

### 19.4 订单路由契约

`OrderRouter.route(order, strategy_id)` 返回 `List[RoutedOrder]`：

```python
routed = sup.router.route(order, strategy_id)
for ro in routed:
    print(ro.account_id, ro.quantity, ro.client_order_id)
    # 所有 ro.client_order_id 相同（同一笔决策）
    # broker 端按 client_order_id 去重
```

**禁止**：
- 改 `client_order_id`（一旦重发，broker 视为新单 → 双倍成交风险）
- 在 router 之外**直接**调 `broker.submit_order`（绕开 allocation 拆单）
- 给子单生成新 UUID

### 19.5 系统级 Kill Switch

`PortfolioSupervisor` 内置全局 Kill Switch，**任一** runtime 净值跌破阈值会停所有 runtime：

```python
# 在 PortfolioSupervisor.on_bar() 内
if stats.last_equity > 0 and stats.last_equity < 80000:
    sup._request_global_kill(f"{rt.runtime_id} equity={stats.last_equity}")
    break
```

**生产环境务必**：
- 把阈值改成对应账户 `0.7 * initial_cash`
- 加上 `RiskManager` 接入 `OrderRouter` 做 pre-submit 检查（V3.4 路线图）
- 把 `sup.global_kill_switch.is_set()` 放在主循环每根 bar 开头判断

### 19.6 新增一个 StrategyRuntime 的 SOP

```python
# 1) 在 signals/ 里写好策略类（继承 SignalStrategy、参数可序列化）

# 2) 在 strategy 注册器里注册
registry.register("MyNewStrategy", MyNewStrategy)

# 3) 在 AllocationEngine 里加上分配
ae = AllocationEngine(FixedAllocation({
    "macross_low":    [...],
    "rsi_high":       [...],
    "alpha_high":     [...],
    "my_new_strategy": [("acc_low", 1.0)],   # ← 新增
}))

# 4) 给它独立 broker（or 复用现有）
broker_for_new = make_broker(initial_cash=100000)

# 5) register + 传 full_data
sup.register_strategy(
    strategy_id="my_new_strategy",           # 全局唯一
    strategy_name="MyNewStrategy",           # 注册名
    strategy_params={"lookback": 20, "k": 1.5},
    account_id="acc_low",
    broker=broker_for_new,
    constructor=TopN(n=2),
    full_data=data,                          # ← 必须传
)
```

### 19.7 多策略多账户项目布局（推荐）

```
my_fund/
├── __init__.py
├── strategies/
│   ├── __init__.py
│   ├── trend/         # MACross / DualThrust
│   ├── mean_reversion/   # BollBand / RSI
│   └── alpha/         # Alpha001 / Alpha009
├── risk_profiles/
│   ├── __init__.py
│   └── profiles.py    # 定义 low/medium/high 阈值
├── allocations/
│   ├── __init__.py
│   └── fixed.py       # FixedAllocation 矩阵
├── accounts/
│   ├── __init__.py
│   └── am.py          # AccountManager 实例化
└── pipelines/
    ├── __init__.py
    └── run_multi.py   # 调 PortfolioSupervisor 主循环
```

### 19.8 V3.4 必跑测试（追加到 §15）

- [ ] **T11 多策略隔离**：3 个策略同时跑 300 bars，**所有 portfolio.cash 单独合计等于 (initial_cash × 3) ± commission**。
- [ ] **T12 OrderRouter 拆单**：1 笔 1000 股 + 60/40 拆，应得 600/400 ± 1 股。
- [ ] **T13 client_order_id 幂等**：把同一笔 order 投两次进 router，broker 端 `fills` 数量不变。
- [ ] **T14 系统级 Kill Switch**：人为把某个 runtime 的 last_equity 改到 79999，下一根 bar 全停。
- [ ] **T15 全局 PnL 报告**：sup.print_report() 输出的 `total_orders == sum(runtime.orders_submitted)`。

### 19.9 V3.4 反模式（额外）

- ❌ **共享 `factor_cache`**：V3.4 默认 `factor_cache` 仍是 module-level singleton。不同 runtime 用不同 period 时**会**串味。每个 runtime 在 `on_bar` 开头**先 `clear()`**，或者用 `StrategyContext` 注入独立的 cache。
- ❌ **一个策略在 5 个账户上铺 20%**：拆单余量爆掉，券商最小单笔 100 股约束下严重偏离目标权重。
- ❌ **Supervisor 改 runtime 状态**：违反设计原则。Runtime 必须**自治**（自己能 stop / 调仓 / 报 stats），Supervisor 只做"广播 + 收集 + Kill Switch"。
- ❌ **同 `client_order_id` 不同 `account_id`**：拆单后子单仍共享原 `client_order_id`（这是设计），但**只有原 strategy 投出**；不要手工复用。

---

## 20. 写给团队的几条原则

1. **策略越简单越好**。一个能跑 5 年的简单策略 > 一个回测漂亮但没人能解释的复杂策略。
2. **回测不是终点**。Paper → 小资金实盘 → 资金阶梯。
3. **别在策略层加风控**。风控是 Engine / RiskManager 的责任。策略只决定"想做什么"，风控决定"能不能做"。
4. **Paper 至少 2 周**。覆盖完整换仓周期 + 一次极端行情。
5. **每个新策略都入库**。哪怕 Sharpe 很低，也是负样本。
6. **WTF per minute 原则**：你自己都解释不清的策略，不要上线。
7. **V3.4 隔离原则**：每个 `StrategyRuntime` 状态完全独立，`Supervisor` 不允许改 runtime 内部状态。多策略矩阵的稳定性来自"边界"而不是"耦合"。
8. **V3.1+ 模式无感知**：策略层**永远不**写 `if mode == "live"`。三模式切换是 `ExecutionFactory` 的事，不是策略的事。
9. **V3.2 trace_id 全程开**：从策略开发第一天起就接 `TradeLogger` + `EventTracer`，否则上线后排查"为什么亏"会成倍耗时。
10. **V3.3 先做 Replay 再上线**：每个新策略上线前都跑一次 `ReplayEngine` 验证本地和 broker 端一致。
11. **V3.5 真实化不可省**：任何"看起来很棒"的 backtest 都要过 True PnL、Orderbook 扫单、Adaptive Plan、Shadow Mode 四关。详见 §21。
12. **V3.6 Tradeability 是机构红线**：Tradeability Rank F 策略**禁止**进入实盘，无论回测多漂亮。详见 §21。

***

## 21. V3.5+ Execution Fidelity & Alpha-Aware 集成指南

> 这一节是**对开发流程的扩展**：当你的策略走完 §1 的 8 步之后，还**必须**在实盘前经过 V3.5 / V3.6 两层"真实化"评估。

### 21.1 新增的开发步骤（在 §1 的 8 步之后）

```
9.  真实化模拟        V3.5 Execution Fidelity（订单簿/冲击/成本/True PnL）
10. 执行感知评估      V3.6 Execution-Aware Alpha（10 个模块）
11. 影子模式          V3.5 Shadow Mode（paper vs live 灰度）
12. 真实资金上线      Live + Observe
```

### 21.2 V3.5 Execution Fidelity 集成硬约束

**所有新策略上线前必须先跑过下面四个真实化指标**：

1. **True PnL 必须 ≥ 0**
   - 在你策略的目标资金量级上，扣除全部成本（fee + slippage + impact + opportunity）后 PnL 仍为正
   - 用 `TruePnLTracker.compute_true_pnl()` 算 `cost_drag_bps`
   - 警告线：`cost_drag_bps > 50`（成本占去年化收益 > 50%）

2. **Orderbook 扫单不能超出 N 档**
   - 目标成交量 ≤ 订单簿前 5 档深度之和
   - 否则你的订单就是"打穿对手盘"的市价单，真实成本会远高于 `slippage_bps` 的假设

3. **Adaptive Plan 的切片数 ≥ 2**
   - 单一订单大资金必须切片（防冲击）
   - 计划生成后**自己确认**每片延迟 + 数量

4. **Shadow Mode 至少 100 单**
   - paper / live 价差 > 5 bps 的订单 < 1%
   - 否则说明你的 paper broker 假设过于乐观

### 21.3 V3.6 Execution-Aware Alpha 硬约束

**实盘前必须达到下面三条线**：

1. **Tradeability Rank ≥ B**（alpha_score ≥ 0.50）
   - 用 `TradeabilityScoreSystem().evaluate(...)` 算
   - F 评级**禁止**进入实盘

2. **Survival Filter 判定 SURVIVES**
   - `survival_score ≥ 0.6` 且 `real_sharpe ≥ 0.5`
   - 0.61 vs 0.95 都 `survives`，但**0.61 策略不能上**

3. **Adjusted Sharpe ≥ 1.0**
   - 机构线是 ≥ 2.0
   - 散户线 ≥ 1.0，否则即使实盘赚钱也不够覆盖机会成本

### 21.4 推荐集成顺序

```python
# ===== 在 §1 第 4 步（Optimize）之后插入 =====
from quantlab.execution.fidelity import (
    CostModel, ImpactModel, OrderbookSimulator, TruePnLTracker,
)
from quantlab.execution.alpha_aware import (
    AlphaRealizabilityEngine, TurnoverPressureModel,
    LiquidityAlphaFilter, ExecutionSensitivityTest,
    LatencyFragilityTest, MarketImpactBacktest,
    ExecutionAdjustedSharpe, AlphaSurvivalFilter,
    ExecutionAwareFeatures, TradeabilityScoreSystem,
)

# Step 9: 真实化模拟（V3.5）
impact = ImpactModel().calculate(...)
cost = CostModel().calculate(...)
assert cost.cost_drag_bps < 50, "成本过高, 不可执行"

# Step 10: 执行感知评估（V3.6）
report = AlphaRealizabilityEngine().evaluate(metrics, constraints)
assert report.verdict == "TRADABLE", f"alpha 不可交易: {report.warnings}"

survival = AlphaSurvivalFilter().evaluate(survival_input)
assert survival.survives and survival.survival_score >= 0.7, \
    f"alpha 生存判定失败: score={survival.survival_score}"

tradeability = TradeabilityScoreSystem().evaluate(metrics, constraints, survival_input)
assert tradeability.rank in ("S", "A", "B"), f"alpha 评级不足: {tradeability.rank}"
```

### 21.5 严禁的反模式

1. **❌ 用 paper backtest 的 Sharpe 直接进 live** —— 必经 V3.5/V3.6 两层真实化。
2. **❌ 把 ExecutionAdjustedSharpe 当可选项** —— 这是机构红线指标，**强制**。
3. **❌ 用 Tradeability Rank F 策略做"实验性小资金"** —— 小资金小不了"滑点爆炸"和"延迟敏感"的问题。
4. **❌ 跳过 Shadow Mode 直接实盘** —— 100 单 paper/live 对比是基本功。
5. **❌ 用 Execution-Aware Features 做研究阶段** —— 它们包含"成本信息"是未来函数，会污染 IC。

### 21.6 性能影响

V3.5 / V3.6 都是**纯 Python 计算**，不接交易所，不起线程。100 个标的 × 1 年数据：
- V3.5（订单簿 + 冲击 + 成本）：~200ms
- V3.6（10 个模块全跑）：~500ms
- 总计 < 1s，**可以加进每日 Pipeline**

### 21.7 推荐决策树

```
策略回测 OK
   ↓
V3.5 True PnL ≥ 0 ?
   ├─ NO → 放弃 / 改 cost model / 降资金规模
   └─ YES ↓
V3.6 Tradeability Rank ≥ B ?
   ├─ NO → 看哪个分项 0，修短板
   │       ├─ Predictive Power 不足 → 重做信号
   │       ├─ Executability 不足 → 减换手 / 提流动性要求
   │       ├─ Stability 不足 → 加 walk-forward 验证
   │       └─ Cost Efficiency 不足 → 调大滑点假设
   └─ YES ↓
Shadow Mode 100 单 paper/live < 5 bps ?
   ├─ NO → 改 paper broker 假设
   └─ YES ↓
小资金实盘（建议初始 ≤ 1/10 目标资金量）
   ↓
3 个月稳定 → 加仓到 1/3
   ↓
6 个月稳定 → 满仓
```

### 21.8 V3.5/V3.6 调试技巧

| 现象 | 大概率原因 | 解决 |
|------|------------|------|
| `real_score` 一直为 0 | `cost_adjusted_return < 0` | 检查 turnover 和 fee_rate 是否过大 |
| `sharpe_stability` < 0.5 | 策略对 slippage 极敏感 | 加 risk_parity / 减杠杆 |
| `survival_score` 低 | `real_sharpe` < 0.5 | 用 Execution-Adjusted Sharpe 反推 |
| `critical_latency_ms` < 50ms | 策略依赖极低延迟 | 这种策略**机构也跑不了**，劝退 |
| `liquidity_filter` 总是 REJECT | 标的池太冷门 | 限定 universe 到日均成交 > X 的标的 |
| `adaptive_plan` 切片数 = 1 | `urgency >= 0.9` | 大资金不应 urgent |

### 21.9 文档对应

- 完整模块说明：[`README.md` §19](./README.md#19-v35-execution-fidelity-layer), [§20](./README.md#20-v36-execution-aware-alpha-layer), [§21](./README.md#21-v44-ml-lab--observe--live-studio)
- V3.5 API：`quantlab/api/fidelity.py`
- V3.6 API：`quantlab/api/alpha_aware.py`
- V4.4 ML Lab API：`quantlab/api/ml_lab.py`
- V3.5 前端：`/fidelity`
- V3.6 前端：`/alpha-aware`
- V4.4 ML Lab 前端：`/ml-lab`
- V4.4 Observe 前端：`/observe/*`
- V4.4 Live Studio 前端：`/live`

---

## 22. V4.4 ML 策略开发规范

> 这一节是**对开发流程的进一步扩展**：当你的策略需要用机器学习方法时，走 ML Lab 的 17 Tab 工作流。

### 22.1 ML 策略开发步骤（在 §1 的 8 步基础上）

```
1.  创建 ML 数据集    ML Lab → Datasets Tab → Create Dataset + Upload CSV
2.  定义特征          ML Lab → Features Tab → Feature Sets Tab
3.  定义标签          ML Lab → Labels Tab → Label Sets Tab
4.  特征诊断          ML Lab → Feature Diagnostics / Label Diagnostics
5.  模型训练          ML Lab → Training Jobs Tab → Start Training
6.  Walk Forward 验证 ML Lab → Validation Tab
7.  模型对比          ML Lab → Model Arena Tab → Run Comparison
8.  泄露检测          ML Lab → Leakage Detector Tab（必须 PASSED）
9.  模型注册          ML Lab → Model Registry Tab → Register Version
10. 构建 ML 策略      ML Lab → Strategy Builder Tab
11. 回测验证          §1 的 2~8 步
12. 真实化评估        §21 的 9~12 步
```

### 22.2 ML 策略硬约束

1. **Leakage Detector 必须 PASSED**
   - 任何 `shift(-1)` / `rolling(center=True)` 等前瞻偏差必须消除
   - CRITICAL 级别问题 = 0 个才能注册模型

2. **Walk Forward 验证 IC Stability ≥ 0.5**
   - IC Stability < 0.5 说明模型对时间窗口敏感，过拟合风险高

3. **Model Arena 对比至少 3 个模型**
   - 单模型无法判断是否为最优选择
   - 必须包含 LightGBM / XGBoost 中的至少一个

4. **禁止用 train_test_split**
   - 时间序列数据**必须**用 Walk Forward 验证
   - ML Lab 的 Validation Tab 已内置此检查

### 22.3 Live Studio 部署规则

1. **先 Paper 后 Live**
   - Live Studio 的 Broker 选择中，Binance 实盘当前 disabled
   - 所有策略必须先在 Paper 模式下运行 ≥ 1 周

2. **Deploy 前必须完成 V3.5/V3.6 评估**
   - Tradeability Rank ≥ B
   - True PnL ≥ 0

3. **Observe 监控必须开启**
   - 部署后立即检查 `/observe/health` 页面
   - Kill Switch 阈值：日亏损 ≤ 3%，最大回撤 ≤ 15%

### 22.4 严禁的反模式

1. **❌ 跳过 Leakage Detector 直接注册模型** —— 前瞻偏差是 ML 策略最常见的致命问题
2. **❌ 用 train_test_split 代替 Walk Forward** —— 时间序列泄漏
3. **❌ 单模型直接上线** —— 必须在 Model Arena 中对比
4. **❌ ML 策略跳过 V3.5/V3.6 直接 Deploy** —— ML 策略的换手率通常更高，成本影响更大
5. **❌ 不看 Observe Health 就加仓** —— ML 策略的退化可能很突然


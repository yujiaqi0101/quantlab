# QuantLab — 量化回测框架

一个用纯 Python 写成的多标的、多引擎、可扩展的量化策略研究 & 回测框架。涵盖了从因子、信号、组合构建、执行、撮合、滑点、佣金，到参数优化、双引擎验证、Walk-Forward 分析、实验追踪（SQLite）、Tick 级回测、Paper/Live 交易、风险管理等完整链路。

整个项目以 `quantlab` 包为核心，根目录的 `main.py` 是一个端到端的**演示入口**，跑通它相当于把框架所有主要模块都验证一遍。

---

## 目录

- [1. 项目结构](#1-项目结构)
- [2. 核心设计思想](#2-核心设计思想)
- [3. 核心领域模型 `quantlab/core`](#3-核心领域模型-quantlabcore)
- [4. 数据层 `quantlab/data`](#4-数据层-quantlabdata)
- [5. 因子库 `quantlab/factors`](#5-因子库-quantlabfactors)
- [6. 信号层 `quantlab/signals`](#6-信号层-quantlabsignals)
- [7. 组合构建 `quantlab/portfolio_construction`](#7-组合构建-quantlabportfolio_construction)
- [8. 执行/撮合 `quantlab/execution`](#8-执行撮合-quantlabexecution)
- [9. 事件总线 `quantlab/event`](#9-事件总线-quantlabevent)
- [10. 三个回测引擎](#10-三个回测引擎)
- [11. VectorBT 适配器 `quantlab/adapters`](#11-vectorbt-适配器-quantlabadapters)
- [12. 研究流水线 `quantlab/research`](#12-研究流水线-quantlabresearch)
- [13. 风险管理 `quantlab/risk`](#13-风险管理-quantlabrisk)
- [14. 实时 / Paper 交易 `quantlab/live`](#14-实时--paper-交易-quantlablive)
- [15. V3.1 统一 Execution 层](#15-v31-统一-execution-层)
- [16. V3.2 可观测性中心](#16-v32-可观测性中心)
- [17. V3.3 可恢复运行时](#17-v33-可恢复运行时)
- [18. V3.4 多策略 × 多账户矩阵](#18-v34-多策略--多账户矩阵)
- [19. V3.5 Execution Fidelity Layer](#19-v35-execution-fidelity-layer)
- [20. V3.6 Execution-Aware Alpha Layer](#20-v36-execution-aware-alpha-layer)
- [21. 主入口 `main.py` 的 16 个 Stage](#21-主入口-mainpy-的-16-个-stage)
- [22. 快速上手](#22-快速上手)
- [23. 数据格式约定](#23-数据格式约定)
- [24. 版本演进](#24-版本演进)

---

## 1. 项目结构

```
回测框架/
├── main.py                       # 端到端演示入口（16 个 Stage）
├── compare.py                    # BarEngine vs VectorBT 一次性对比
├── data/                         # 示例 OHLCV CSV
│   ├── AAPL.csv
│   ├── MSFT.csv
│   └── NVDA.csv
├── reports/                      # 输出报告（CSV / HTML）
│   ├── parallel_grid.csv
│   ├── validation_report.csv
│   └── wf_report.html
├── storage/
│   └── research.db               # SQLite 实验库
└── quantlab/                     # 框架核心
    ├── _compat.py                # 兼容层（旧 import 路径 → 新模块）
    ├── core/                     # 领域对象 + 引擎抽象 + 回测结果
    │   ├── base_engine.py        # BaseBacktestEngine（抽象类）
    │   ├── backtest_result.py    # BacktestResult（统一输出）
    │   ├── order.py / fill.py    # Order / Fill
    │   ├── position.py / portfolio.py
    │   ├── trade.py / tradebook.py  # FIFO ClosedTrade
    │   ├── portfolio_snapshot.py
    │   └── tick.py               # V2.4 Tick 数据类
    ├── data/                     # 数据层
    │   ├── context.py            # StrategyContext（data + cache）
    │   ├── cache.py              # FactorCache（因子缓存）
    │   ├── datasource.py         # CSV/Parquet/API 抽象
    │   └── tick_feed.py          # V2.4 BarToTickFeed
    ├── factors/                  # 因子库
    │   ├── ma.py
    │   ├── atr.py
    │   ├── boll.py
    │   └── rsi.py
    ├── signals/                  # 策略层
    │   ├── base.py               # SignalStrategy 抽象基类
    │   └── ma_cross.py           # MACrossStrategy
    ├── portfolio_construction/   # 组合构建
    │   ├── base.py               # PortfolioConstructor
    │   ├── target_portfolio.py   # TargetPortfolio（目标权重）
    │   ├── equal_weight.py
    │   └── top_n.py
    ├── execution/                # 执行/撮合
    │   ├── order.py              # 兼容 re-export
    │   ├── commission.py         # PercentageCommission
    │   ├── slippage.py           # PercentageSlippage
    │   ├── tick_slippage.py      # V2.4 TickSlippage（按 tick_size）
    │   └── matcher.py            # TargetWeightExecution
    ├── event/                    # 事件总线
    │   ├── event_bus.py          # pub/sub
    │   └── event_types.py        # Market/Signal/Order/Fill Event
    ├── engine/                   # 引擎实现
    │   ├── __init__.py           # BarEngine（旧版）
    │   ├── tick_engine.py        # V2.4 TickEngine
    │   ├── tick_matcher.py       # Tick 级撮合
    │   └── intrabar_execution.py # bar 内 tick 成交
    ├── adapters/                 # 外部适配器
    │   ├── vectorbt_adapter.py   # V2.0 VectorBTAdapter
    │   ├── subprocess_vbt.py     # SubprocessVectorBT（沙箱）
    │   └── _vbt_worker.py        # 子进程 worker
    ├── research/                 # 研究流水线
    │   ├── result.py             # ExperimentResult
    │   ├── experiment.py         # Experiment
    │   ├── report.py             # Report
    │   ├── optimizer.py          # Optimizer / FastOptimizer
    │   ├── parallel_optimizer.py # V2.1 ParallelOptimizer
    │   ├── validation.py         # V1.8 ValidationRunner
    │   ├── walk_forward.py       # WalkForward + V2.2 WalkForwardRunner
    │   ├── database.py           # V2.3 SQLite Database
    │   ├── repository.py         # V2.3 ExperimentRepository
    │   └── tracker.py            # V2.3 ExperimentTracker
    ├── risk/                     # V2.5 风险控制
    │   ├── limits.py             # MaxPositionLimit / MaxOrderSize / ...
    │   ├── checks.py             # PositionLimitCheck / OrderSizeCheck / ...
    │   ├── risk_manager.py       # 串联多个 Check
    │   └── kill_switch.py        # EmergencyStop / KillSwitch
    ├── live/                     # V2.5 → V3.4 实盘/Paper
    │   ├── broker/               # V3.1 Broker 统一接口
    │   │   ├── base.py           # BrokerAdapter ABC
    │   │   ├── paper_broker.py   # PaperBroker（带 idempotency）
    │   │   ├── ibkr_broker.py    # IBKRBroker（stub）
    │   │   └── binance_broker.py # BinanceBroker（stub）
    │   ├── execution/            # V3.1 统一 Execution
    │   │   ├── base.py           # BaseExecution ABC
    │   │   ├── backtest_execution.py
    │   │   ├── paper_execution.py
    │   │   ├── live_execution.py
    │   │   └── factory.py        # ExecutionFactory
    │   ├── risk/                 # V3.1 RiskManager + Checks
    │   │   ├── limits.py
    │   │   ├── checks.py
    │   │   ├── risk_manager.py
    │   │   └── kill_switch.py
    │   ├── broker.py             # 旧位置（兼容）
    │   ├── market_data.py        # MarketDataAdapter 抽象
    │   ├── order_manager.py      # 订单状态机
    │   ├── paper_trading.py      # 旧 PaperBroker（兼容）
    │   ├── replay_market_data.py # ReplayMarketData
    │   ├── live_engine.py        # LiveEngine（V2.5，V3.4 待迁）
    │   └── logger.py             # LiveLogger = TradeLogger 别名
    ├── monitoring/               # V3.2 可观测性中心
    │   ├── logger.py             # TradeLogger（标准字段）
    │   ├── metrics.py            # MetricsCollector（PnL/DD/Exposure/...）
    │   ├── tracer.py             # EventTracer（trace_id 串联）
    │   ├── alert.py              # AlertManager（PnL/Slippage/Loss/...）
    │   ├── dashboard.py          # matplotlib + streamlit 面板
    │   └── system_context.py     # SystemContext 中心对象
    └── runtime/                  # V3.3 + V3.4 内核
        ├── state_store.py        # StateSnapshot
        ├── checkpoint.py         # CheckpointManager
        ├── recovery.py           # RecoveryManager
        ├── consistency.py        # ConsistencyChecker
        ├── replay.py             # ReplayEngine
        ├── shutdown.py           # ShutdownManager
        ├── thread_safety.py      # TradeLock
        ├── event_durability.py   # EventLog
        ├── account_manager.py    # V3.4 Account + AccountManager
        ├── allocation.py         # V3.4 FixedAllocation / DynamicAllocation
        ├── router.py             # V3.4 OrderRouter（拆单 + 路由）
        ├── strategy_runtime.py   # V3.4 独立运行单元
        ├── supervisor.py         # V3.4 PortfolioSupervisor + StrategyRegistry
    ├── execution/                # V3.5+ 真实交易模拟层
    │   ├── fidelity/             # V3.5 Execution Fidelity Layer
    │   │   ├── orderbook/        # 订单簿模拟器 + 流动性模型
    │   │   ├── impact/           # 市场冲击模型（sqrt / linear / power）
    │   │   ├── latency/          # 延迟模型
    │   │   ├── cost/             # 综合成本模型（fee / slippage / impact / opportunity）
    │   │   ├── fill_engine.py    # 成交引擎（限价/市价 + 部分成交）
    │   │   ├── matcher.py        # 多档撮合
    │   │   ├── reconciliation.py # 成交对账（本地 vs 交易所）
    │   │   ├── replay.py         # 确定性回放
    │   │   ├── shadow.py         # 影子模式（paper vs live 对比）
    │   │   ├── truth.py          # 真实 PnL（扣除全部成本）
    │   │   └── adaptive.py       # 自适应执行计划
    │   └── alpha_aware/          # V3.6 Execution-Aware Alpha Layer
    │       ├── realizability.py  # Alpha Realizability Engine
    │       ├── turnover.py       # Turnover Pressure Model
    │       ├── liquidity_filter.py # Liquidity-Aware Alpha Filter
    │       ├── sensitivity.py    # Execution Sensitivity Test
    │       ├── latency_fragility.py # Latency Fragility Test
    │       ├── impact_backtest.py # Market Impact Backtest
    │       ├── adj_sharpe.py     # Execution-Adjusted Sharpe
    │       ├── survival.py       # Alpha Survival Filter
    │       ├── features.py       # Execution-Aware Feature Engineering
    │       └── tradeability.py   # Tradeability Score System
    ├── api/                      # FastAPI 路由
    │   ├── app.py                # FastAPI 入口
    │   ├── fidelity.py           # V3.5 API
    │   ├── production.py         # V3.4 运行时 API
    │   └── alpha_aware.py        # V3.6 API
    └── frontend/                 # 前端（Vue 3 + Element Plus + Vite）
        └── src/views/
            ├── fidelity/FidelityStudio.vue       # V3.5 前端
            └── alpha_aware/AlphaAwareStudio.vue   # V3.6 前端
```

---

## 2. 核心设计思想

### 2.1 分层 + 解耦
整个回测流程被切成一组明确的流水线：

```
   ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │  Strategy    │ →  │  Portfolio       │ →  │  Execution       │
   │  (signals)   │    │  Constructor     │    │  (matcher)       │
   └──────────────┘    └──────────────────┘    └──────────────────┘
        scores dict         TargetPortfolio         List[Order]
   ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │  Engine      │ ←  │  Slippage        │    │  Commission      │
   │  (bar/tick/  │    │  (PriceSlip)     │    │  (% notional)    │
   │   event)     │    └──────────────────┘    └──────────────────┘
   └──────────────┘
        Fill + 扣现金 + 更新 Position
   ┌──────────────┐
   │  TradeBook   │ →  ClosedTrade(FIFO)
   └──────────────┘
```

每一层都有自己的接口和实现，可以独立替换。

### 2.2 双轨抽象：`BaseBacktestEngine` + `BacktestResult`
所有引擎（Bar / Event / Tick / VectorBTAdapter）统一继承 `BaseBacktestEngine`，入口签名是
```python
engine.run(strategy, data, params) -> BacktestResult
```
这样上层的 `Optimizer` / `ValidationRunner` / `WalkForwardRunner` / `Experiment` 不必知道底层用的是什么引擎，可以任意替换。

### 2.3 信号解耦：策略只产 signal
策略（继承 `SignalStrategy`）的 `.signal(ctx)` 永远只返回一个 `pd.DataFrame`：
- `index` = bar 时间戳
- `columns` = symbol
- `values` ∈ {0, 1, -1}（-1 暂不强用）

至于"信号 → 仓位"由 `PortfolioConstructor` 决定；"仓位 → 订单"由 `Execution` 决定；"订单 → 成交"由 `Engine` 决定。策略层完全不感知。

### 2.4 兼容层 `_compat.py`
老代码 `from quantlab.strategy import MACrossStrategy` 等仍可用，所有顶层模块都通过 `_compat.py` re-export 新模块（`signals/ma_cross.py` 等）。新代码建议直接走子包。

### 2.5 V3.1+ 演进：四层架构 + 可恢复 + 多策略矩阵

V3.0 之前：单策略 + 单账户 + 单引擎。V3.1 起把整个系统演进为**生产级交易系统内核**：

```
                ┌──────────────────────────────────────────────┐
                │           StrategyRegistry                   │
                │  (策略类注册：MACross / RSI / Alpha001 …)       │
                └──────────────┬───────────────────────────────┘
                               │
       ┌───────────────────────┼───────────────────────┐
       ▼                       ▼                       ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│StrategyRt_A  │        │StrategyRt_B  │        │StrategyRt_C  │
│strategy      │        │strategy      │        │strategy      │
│portfolio     │        │portfolio     │        │portfolio     │   ← 状态完全隔离
│execution     │        │execution     │        │execution     │
│broker        │        │broker        │        │broker        │
└──────┬───────┘        └──────┬───────┘        └──────┬───────┘
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               ▼
                  ┌────────────────────────┐
                  │  PortfolioSupervisor   │   ← 观察者 + 调度器
                  │   • 广播 market data    │     （不直接改 runtime 状态）
                  │   • 收集 stats         │
                  │   • 全局 Kill Switch   │
                  └────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │ acc_low  │     │ acc_mid  │     │ acc_high │   ← AccountManager
        │ broker_1 │     │ broker_2 │     │ broker_1 │
        └──────────┘     └──────────┘     └──────────┘
              ▲                ▲                ▲
              └────────────────┼────────────────┘
                               │
                  ┌────────────────────────┐
                  │  OrderRouter           │   ← 拆单 + 路由
                  │   (按 allocation 拆)    │
                  └────────────────────────┘
```

**核心原则**：
1. **每个 StrategyRuntime 独立**：strategy / portfolio / execution / broker 一一对应，状态**完全不共享**。
2. **Supervisor 是观察者 + 调度器**：只广播行情、收集 stats、维护全局 Kill Switch，**不直接修改任何 runtime 内部状态**。
3. **OrderRouter 是唯一对外出口**：策略不直接调 broker，所有订单先经 router 按 `AllocationEngine` 拆，再投递到对应 account 的 broker。
4. **Execution 统一接口**：Backtest / Paper / Live 三种模式走同一个 `BaseExecution.submit(target_portfolio)`，靠 `ExecutionFactory` 切换。

---

## 3. 核心领域模型 `quantlab/core`

### 3.1 Order / Fill / Position
- `Order(symbol, quantity)`：撮合器输出。`qty > 0` 买入，`qty < 0` 卖出。
- `Fill(symbol, timestamp, quantity, price, commission)`：成交记录。
- `Position(symbol, qty, avg_price, realized_pnl)`：单标的持仓。`update(qty_change, price)` 处理开仓 / 加仓 / 平仓 / 反手（FIFO）。

### 3.2 Portfolio（多标的）
- 维护 `positions: Dict[symbol, Position]`、`cash`、`equity_curve`、`timestamps`、`last_prices`。
- `get_or_create(sym)`、`get_position(sym)`（不创建）、`symbols`、`equity()`、`record(timestamp, prices)`。
- 现金不足保护：买入时 `cost > cash` 自动降仓。

### 3.3 TradeBook + TradeBuilder
- `on_fill(fill)` 收集所有成交；`rebuild()` 把 `fills` 按 symbol 分组，再交给 `TradeBuilder` 用 **FIFO** 算法生成 `ClosedTrade(symbol, entry_time, exit_time, qty, entry_price, exit_price, pnl, return_pct)`。
- V1.9 新增 `closed_trades_by_symbol` / `pnl_by_symbol()` / `trade_count_by_symbol()`。

### 3.4 BacktestResult（所有引擎统一输出）
核心字段：
- 核心指标：`equity_curve`, `total_return`, `sharpe`, `max_drawdown`, `trade_count`, `win_rate`, `final_equity`
- 来源：`source` ∈ `{"event", "bar", "vectorbt", "vectorbt_subprocess", "tick", "live"}`
- 原始输出：`raw`（保留 vbt.Portfolio 等）
- 详细：`fills / tradebook / portfolio / position_qty / signal / timestamps`
- V2.0 新增：`weights_df`（`date × symbol` ∈ [0, 1]）
- 错误：`error`（`ok()` 判断是否有错）
- `from_event_dict(raw)`：把 EventEngine/BarEngine 老 dict 包成 BacktestResult

### 3.5 BaseBacktestEngine
```python
class BaseBacktestEngine(ABC):
    @abstractmethod
    def run(self, strategy, data: Dict, params: Dict = None) -> BacktestResult: ...
```

### 3.6 PortfolioSnapshot
单 bar 的组合快照（`timestamp / equity / cash / weights`），并提供 `invested_weight` 属性（`1 - cash/equity`）。权益曲线 = `List[PortfolioSnapshot]`。

### 3.7 Tick（V2.4）
单条 tick 记录 `timestamp / symbol / price / volume`（`bid/ask` 占位但 V1 不读）。`price < 0` 在 `__post_init__` 抛 `ValueError`。

---

## 4. 数据层 `quantlab/data`

### 4.1 StrategyContext
```python
StrategyContext(data: Dict[symbol, DataFrame], cache: FactorCache)
```
- 策略通过 `ctx.data` 拿多标的 DataFrame，通过 `ctx.cache` 做因子缓存。
- `ctx.symbols` 返回所有 symbol。

### 4.2 FactorCache
- 简单的 `dict` 包装，提供 `get(key) / set(key, val) / clear()`。
- 全局实例 `factor_cache`（`quantlab/data/cache.py`）。**注意**：因为是 module-level singleton，跨 Experiment / 跨窗口必须 `clear()`，否则会拿错长度的 Series 导致 `identically-labeled Series` 错位。

### 4.3 DataSource
抽象基类 `DataSource` + `CSVSingleSource`（单文件）+ `CSVMultiSource`（目录 + pattern）。后续可扩 Parquet / Tushare / JoinQuant。

### 4.4 BarToTickFeed（V2.4）
把 `Dict[symbol, DataFrame]` 转成 `Iterator[Tick]`，V1 每个 bar 1 tick，`price = bar.close`。

---

## 5. 因子库 `quantlab/factors`

每个因子都自己带 cache 逻辑，调用格式一致：
```python
ma(ctx, symbol, period)
```

| 函数 | 说明 | 返回 |
|------|------|------|
| `ma(ctx, symbol, period)` | 简单移动平均 | `pd.Series` |
| `atr(ctx, symbol, period=14)` | True Range 的 N 期均值 | `pd.Series` |
| `boll(ctx, symbol, period=20, num_std=2, return_tuple=False)` | 布林带 | 默认中轨；`return_tuple=True` 返 `(mid, upper, lower)` |
| `rsi(ctx, symbol, period=14)` | 0~100 RSI | `pd.Series` |

cache key 包含 symbol/period/参数，确保多标的互不干扰。

---

## 6. 信号层 `quantlab/signals`

### 6.1 SignalStrategy
```python
class SignalStrategy(ABC):
    @abstractmethod
    def signal(self, ctx) -> pd.DataFrame: ...
```
策略只产 `DataFrame(date × symbol)` ∈ {0, 1}，**不关心**：
- 仓位怎么算
- 订单怎么下
- 用 Bar/Tick/VectorBT 哪个引擎
- 滑点 / 佣金多少

### 6.2 MACrossStrategy
经典双均线：`fast_ma > slow_ma` 取 1，否则 0。可配 `fast=20, slow=60`。

---

## 7. 组合构建 `quantlab/portfolio_construction`

### 7.1 TargetPortfolio
`@dataclass(timestamp, weights: Dict[symbol, float])`，`__post_init__` 校验 `weight >= 0`。
提供 `symbols` / `total_weight` 属性。

### 7.2 PortfolioConstructor
抽象类：
```python
def construct(self, scores: Dict[str, float], timestamp) -> TargetPortfolio
```

### 7.3 内置实现
- `EqualWeight()`：所有 `score > 0` 的 symbol 等权 `1/N`。
- `TopN(n=2)`：取 score 降序前 N 个，等权 `1/N`，用于动量轮动 / 行业 ETF 轮动。

未来扩展位：`RiskParity / MaxWeightConstraint / SectorLimit / CashBuffer / RebalanceTime`。

---

## 8. 执行/撮合 `quantlab/execution`

### 8.1 Order（撮合器输出）
`Order(symbol, quantity)`。`TargetWeightExecution.generate_orders(...)` 把它转成 `List[Order]`。

### 8.2 PercentageSlippage
按价格固定比例滑点（`rate=0.0002` 即 2 bps）：
- 买入：`price * (1 + rate)`
- 卖出：`price * (1 - rate)`

### 8.3 PercentageCommission
按成交金额比例：`abs(qty) * price * rate`（`rate=0.0003`）。

### 8.4 TickSlippage（V2.4）
按 `tick_size` 的固定价差：
- BUY：`price + 0.5 * tick_size`
- SELL：`price - 0.5 * tick_size`

适用于期货/股票最小变动价位。

### 8.5 TargetWeightExecution
输入 `portfolio + TargetPortfolio + prices`：
1. 算当前 equity
2. 对每个 symbol 算 target_value = equity × target_w
3. 比较 current_qty vs target_qty，`|delta_qty / ref_qty| < position_tolerance` 就跳过
4. 取整到 `lot_size`
5. 产出 `List[Order]`

> 注意：执行只产订单，**不改 Portfolio**；真正扣现金、更新仓位是 Engine 的事。

---

## 9. 事件总线 `quantlab/event`

### 9.1 Event
基类 `@dataclass(type, timestamp, payload)`，所有事件基于它。

### 9.2 四种事件
- `MarketEvent(type="MARKET")`：每根 bar 发
- `SignalEvent(type="SIGNAL", symbol, direction, score)`：策略产出
- `OrderEvent(type="ORDER", symbol, quantity)`：组合构建器产出
- `FillEvent(type="FILL", symbol, quantity, price, commission)`

### 9.3 EventBus
`pub/sub` 模型：按 `type` 路由。提供 `subscribe / unsubscribe / publish / history / clear`。全局实例 `event_bus`（V1 用，V2 改成 per-Engine）。

---

## 10. 三个回测引擎

### 10.1 BarEngine

> `quantlab/engine/__init__.py`（旧位置）+ `_compat.py` re-export `BarEngine`

**多标的 + 组合构建层**的精确回测引擎。完整流水线（每根 bar）：

```
1) scores    = strategy.signal(ctx).iloc[i-1]      # 前一根 bar 的分数
2) target    = portfolio_constructor.construct(
                   scores, timestamp)               # 目标权重
3) orders    = execution.generate_orders(
                   portfolio, target, prices)       # 调仓单
4) execute   → apply slippage → apply commission
              → 现金不足自动降仓
              → 更新 Position / 扣 cash
              → 生成 Fill → 推 TradeBook
5) record    → 收盘记一次 equity + position_qty
```

**关键设计**：
- Execution 只产 Order，BarEngine 才真正修改 Portfolio
- 现金不足时自动降仓到 `floor(cash_after_commission / price)`
- 收尾调 `tradebook.rebuild()` 生成 ClosedTrade

输入：
```python
BarEngine(
    strategy,
    portfolio_constructor,
    execution_model,
    commission_model,
    slippage_model,
    initial_cash=100000
).run(strategy=strat, data=data, params={...}) -> BacktestResult
```

### 10.2 EventEngine

> `quantlab/event_engine.py`

**事件驱动版**回测引擎，结构上和 BarEngine 等价（产出相同结果），但**所有模块都通过 EventBus 解耦**。

事件流：
```
MarketEvent (engine 发)
   ↓
SignalEvent (策略发)
   ↓
OrderEvent (组合构建器发)
   ↓
FillEvent (撮合器发)  → 更新 Portfolio / TradeBook
```

**优势**：
- 加新模块（如 RiskManager）只需订阅 / 发送事件
- 接 TickEngine：发 `MarketEvent(type="TICK", ...)`
- 接实盘：把 `MarketEvent` 推上 EventBus

### 10.3 TickEngine

> `quantlab/engine/tick_engine.py`（V2.4）

Tick 级回测：复用 `Strategy / Execution / Portfolio / TradeBook`，把 bar → tick。

每 tick 流程：
```
1) 更新 last_prices
2) pending_orders.match(tick)     撮合历史挂单
3) strategy.signal(ctx)           调仓 weights
4) execution.generate_orders(...)  产 Order
5) intrabar_execution.execute(order, tick)  → 立即以 tick.last_price + TickSlippage 成交
6) portfolio.apply_fill(...)
7) portfolio.record(tick.timestamp, prices)
8) 每 snapshot_interval ticks → 记一次 equity
```

关键参数：`tick_size=0.01` / `commission_rate=0.0003` / `snapshot_interval=10`。

**V1 不做**：L2 盘口、撮合队列、限价单、部分成交。

---

## 11. VectorBT 适配器 `quantlab/adapters`

### 11.1 VectorBTAdapter（V2.0）
基于 vectorbt 的**向量化**快引擎。流水线：
```
signal (DataFrame)
   ↓
PortfolioConstructor.construct(scores, ts)   # 与 BarEngine 共用 constructor
   ↓
weights_df (date × symbol) ∈ [0, 1]
   ↓
vbt.Portfolio.from_orders(close, size=weights)  per-symbol
   ↓
合并 equity → BacktestResult(source="vectorbt")
```

构造函数：
```python
VectorBTAdapter(
    constructor=TopN(n=2),   # 默认 EqualWeight
    fees=0.0003,
    slippage=0.0002,
    init_cash=100000,
)
```

**vbt + numba 在受限环境会崩溃**，所以模块在 import 前先 `os.environ.setdefault("NUMBA_DISABLE_JIT", "1")` / `MPLBACKEND=Agg` / `VECTORBT_NO_CACHING=1`。

### 11.2 SubprocessVectorBT（沙箱版）
把 vectorbt 隔离在子进程里跑：序列化 data → 临时 json → 子进程 `_vbt_worker.py` → stdout json → 解析 metrics。`source="vectorbt_subprocess"`。崩溃不影响主进程。

子进程 worker 走 `from_signals` 路径（不是 `from_orders`），是早期实现，**仅供单标的双均线快速冒烟**。

---

## 12. 研究流水线 `quantlab/research`

```
Signal → Experiment → BacktestResult
              ↓
            Optimizer（网格搜索）
              ↓
       FastOptimizer（fast 引擎全网格 + precise 引擎 top_n 验证）
              ↓
       ParallelOptimizer（多进程 + early filter + top_k）
              ↓
       ValidationRunner（fast vs precise 双引擎一致性）
              ↓
       WalkForward（按 bar 滚动）或 WalkForwardRunner V2.2（按年 + 三阶段 + HTML 报告）
              ↓
       ExperimentTracker V2.3（自动入库 SQLite + search + leaderboard）
```

### 12.1 Experiment & Report

`Experiment(name).run(strategy, engine, data, params) -> ExperimentResult`

会自动做：
1. 清 `factor_cache`
2. 调 `engine.run()` 拿 `BacktestResult`
3. 算额外指标：`win_rate / profit_factor / average_trade / exposure`（多标的按 qty × last_prices 算）
4. 包装成 `ExperimentResult(name, strategy_name, params, metrics, equity_curve, timestamps, tradebook, extras)`

`Report(result).generate()` 输出文本报告（Identification / Performance / Trading 三个 section）。`to_dict()` / `to_json()` / `to_html()`。

### 12.2 Optimizer & FastOptimizer

`Optimizer`：通用网格搜索。`evaluate(data, params)` 调一次 `engine.run()`，scorer 默认 `result.sharpe`，失败时 `score = -inf`。

`FastOptimizer(fast_engine, precise_engine=None, top_n=10)`：两阶段：
- 用 fast 引擎（VectorBT）跑全网格
- 取 top_n（score 有效）
- 用 precise 引擎（EventEngine）精确验证，返回 `TwoStageResult(fast_df, precise_df, top_n)`

### 12.3 ParallelOptimizer（多进程，V2.1.1）

`quantlab/parallel_optimizer.py`。**三个性能优化**：
1. **initializer 全局 data** —— 旧版每次 submit 都序列化一次，N 组 → N 次拷贝；新版用 `ProcessPoolExecutor(initializer=_init_worker)` 把 data + engine 一次性塞进 worker 的 `_WORKER_DATA / _WORKER_ENGINE / _WORKER_STRATEGY_CLS` 全局变量，序列化 0 次。
2. **early_filter** —— 每组参数先跑 30% 数据（`early_split=0.3`），`early_sharpe<0` 或 `early_return<0` 直接淘汰（经验上 80% 参数被早死）。
3. **top_k** —— 只保留 Sharpe 最高的 K 组，用 min-heap `O(n log k)` 限内存。

**关键设计**：
- `engine_spec = (type, kwargs)` 元组，worker 内按 type 派发构造引擎，避免 pickling 闭包
- `strategy_path = f"{strategy_cls.__module__}.{strategy_cls.__name__}"` 全限定名，worker 内 `importlib.import_module` + `getattr` 拿类
- 每次 `_evaluate_one` 都清 `factor_cache`，防止不同长度的 Series 串味

> `PARALLEL_USE_THREAD=1` 时切 ThreadPool（numba 内部会释放 GIL，避免 VBT + numba 子进程偶发 SIGABRT）。

### 12.4 ValidationRunner（双引擎一致性，V1.8）

设计动机：**VectorBT 很快但不精确，EventEngine 精确但慢**。双引擎差距 > 20% 几乎一定有 bug（未来函数 / 执行逻辑错 / 仓位估算错）→ 直接淘汰。

```python
runner = ValidationRunner(
    fast_engine=VectorBTAdapter(),
    precise_engine=build_event_engine(),
    consistency_threshold=0.8,
)
vr = runner.validate(strategy_cls, params, data)
# consistency = 1 - |sharpe_fast - sharpe_precise| / max(|sharpe_fast|, |sharpe_precise|, eps)
# passed = consistency >= threshold
```

`validate_top_n(optimizer_result, strategy_cls, data, top_n, param_keys, output_csv)` 批量跑 + 写 CSV。

### 12.5 WalkForward（按 bar 滚动，V1）

```python
wf = WalkForward(train_bars=200, test_bars=80, step_bars=80)
wf.set_engine_template(engine)
wf_result = wf.run(strategy_cls, param_space, data)
```

输出 `WalkForwardResult`：
- `windows`: List[WalkForwardWindow(train_start/end, test_start/end, best_params, train_score, test_result)]
- `stitched_equity_curve`: 拼接所有 test 段（去掉重复边界点）
- `avg_test_sharpe / avg_test_return`
- `summary["best_params_each_window"]`

> 关键：`self._factor_cache.clear()` 在每个 window 切到新 train 段前必清，否则 `ma(60)_AAPL(length=200)` 会在 length=80 的段被错误命中。

### 12.6 WalkForwardRunner V2.2（按年切分 + 三阶段 + HTML 报告）

> `quantlab/research/walk_forward.py` 中的 `WindowGenerator` / `WalkForwardRunner` / `WalkForwardReport`

V1 痛点：按 bar 切分（不是按年）+ 没有 validation 阶段 + 没有 stability + 没有 parameter drift + 报告只是文本。

V2.2 改进：

1. **WindowGenerator** 按 calendar year 切分，`train_years / test_years` 控制。例如 5 年数据，train=2 / test=1 → 3 个窗口。
2. **三阶段流水线**（每窗口）：
   - **Train**：`ParallelOptimizer.run(train_data)` → `top_train_params`（top_k）
   - **Val**：`ValidationRunner.validate_top_n(...)` → `top_val_params`（consistency OK）
   - **Test**：`event_engine.run(best_params, test_data)` → `test_result`
3. **Equity Stitching**：去掉重复边界点拼接成 OOS 曲线
4. **Stability Score**：`0.5 * param_consistency + 0.2 * oos_return_score + 0.3 * n_passed_ratio`
5. **Parameter Drift**：相邻窗口 best_params 的归一化欧氏距离
6. **Best Params Frequency**：参数组合在所有窗口中出现的次数
7. **HTML 报告**（`reports/wf_report.html`）：
   - 用 Agg backend（沙箱无显示器）
   - 内嵌 OOS equity 曲线 + 参数变化曲线（base64 PNG）
   - 列出所有窗口的 best_params / test return / sharpe / maxdd
   - 参数频率表

### 12.7 ExperimentTracker V2.3（SQLite 实验追踪）

> `quantlab/research/tracker.py` / `database.py` / `repository.py`

研究数据库 `storage/research.db`，3 张表：
- `experiments`：`id, name, strategy, params_json, created_at, tag, note`
- `results`：`experiment_id, final_equity, total_return, sharpe, max_drawdown, trade_count, win_rate, source, extras_json`
- `walkforward`：`experiment_id, n_windows, avg_sharpe, avg_return, avg_max_dd, stitched_*, stability_score, parameter_drift, extras_json`

```python
tracker = ExperimentTracker(
    strategy_registry={"MACross": MACrossStrategy},
    db_path="storage/research.db",
)
result = tracker.run(record, engine, data)   # 自动入库
df = tracker.search(strategy="MACross", sharpe_min=0.5, max_dd_max=0.2)
lb = tracker.leaderboard(sort_by="sharpe", top=10)
# sort_by: "sharpe" / "return" / "stability" / "max_drawdown"
```

> 为什么这一步极其重要：Random Search / Bayesian Opt 几十/几万组参数，没有 Tracking 就变成"这个策略为什么好？不知道；这个参数哪里来的？不知道"。

---

## 13. 风险管理 `quantlab/risk`

V2.5 新增。把风控做成**插件式 Check**，由 `RiskManager` 串联。

### 13.1 限额数据类 `limits.py`
- `MaxPositionLimit(symbol, max_qty)`：单 symbol 最大持仓
- `MaxOrderSize(max_qty)`：单笔最大下单量
- `MaxDailyLoss(max_loss, current_pnl)`：当日最大亏损（负数）
- `MaxLeverage(max_leverage)`：`abs(gross_position_value) / equity <= max_leverage`

### 13.2 检查 `checks.py`
`RiskCheck.check(order, context) -> bool`（True 通过 / False 拒单）：
- `OrderSizeCheck` / `PositionLimitCheck` / `DailyLossCheck` / `LeverageCheck`

### 13.3 RiskManager
- `add_check(c)` 串入
- `check(order, context)`：所有 check 都通过才放行，第一个失败即拒
- 拒单记入 `self.rejects`（List[Dict]）

### 13.4 EmergencyStop / KillSwitch
- `EmergencyStop(threshold, daily_pnl, initial_equity, stop)`
  - `update_pnl(pnl)`：算 `ret = pnl / initial_equity`，`ret <= threshold` 时 `stop=True` 并触发 `on_trigger` 回调
- `KillSwitch(estop)` 是 `RiskCheck` 包装：`return not estop.stop`（触发后所有新单都拒）

---

## 14. 实时 / Paper 交易 `quantlab/live`

### 14.1 BrokerAdapter（`broker.py`）
所有 broker 共用接口：
```python
class BrokerAdapter(ABC):
    name: str
    def connect(self): ...
    def disconnect(self): ...
    def submit_order(self, order) -> str: ...   # 返回 broker order_id
    def cancel_order(self, order_id) -> bool: ...
    def get_positions(self) -> Dict[str, int]: ...
    def get_account(self) -> AccountState: ...
    def on_fill(self, callback): ...
```

`AccountState(cash, equity, margin_used, buying_power)`。

### 14.2 PaperBroker
- 收 `Order` → 拿 `last_price` + 0.5 tick 滑点 → 生成 `Fill` → 调 `on_fill` 回调
- 内部维护 `cash / positions / avg_prices`
- 不做撮合队列、撤单、L2 盘口（V1 简化）

### 14.3 MarketDataAdapter
```python
class MarketDataAdapter(ABC):
    def subscribe(self, symbols): ...
    def unsubscribe(self, symbol): ...
    def stream(self) -> Iterator[Tick]: ...
    def on_tick(self, callback): ...
```

`ReplayMarketData`：把 `Dict[symbol, DataFrame]` 顺序回放为 `Tick` 流（每个 bar.close = 1 tick），给 LiveEngine 冒烟用。

### 14.4 OrderManager（订单状态机）
状态：`NEW / PARTIAL / FILLED / CANCELLED / REJECTED`。
- `submit(order)` → `broker.submit_order` → 返回 `ManagedOrder(order, state, broker_id, filled_qty, created_at, updated_at, reject_reason)`
- `report_fill(local_id, fill)`：broker 报来成交后调，更新 `state / filled_qty`，触发 `on_fill` 回调
- `cancel / get / all / open`

### 14.5 LiveEngine

每 tick 主循环：
```
1) broker.push_tick(symbol, price)        # 喂最新价给 broker
2) last_prices[symbol] = tick.last_price
3) strategy.signal(ctx)                   # 产 weights
4) target = TargetPortfolio(weights, ts)
5) orders = execution.generate_orders(...)
6) for order in orders:
     if not risk_manager.check(order, ctx):  # 风控拒单
         logger.reject(...)
     else: order_manager.submit(order)
7) drain_fills(portfolio, tradebook)       # broker → portfolio
8) portfolio.record(...)
9) kill_switch.update_pnl(daily_pnl)      # daily_pnl <= threshold → stop
```

返回 `BacktestResult(source="live", raw={"n_ticks", "n_orders", "n_rejects"})`。

### 14.6 LiveLogger
三路 logger（`logging + RotatingFileHandler`，每个 10MB × 3 备份）：
- `orders.log`：下单记录
- `trades.log`：成交记录
- `errors.log`：拒单 / 异常 / kill switch

> V3.2 起 `LiveLogger` 是 `quantlab.monitoring.logger.TradeLogger` 的别名，提供标准字段 `(timestamp, event_type, symbol, action, price, qty, pnl, source)`，与监控面板、告警系统共用。详见 [§16](#16-v32-可观测性中心)。

---

## 15. V3.1 统一 Execution 层

> 目录：[`quantlab/live/execution/`](./quantlab/live/execution/)、[`quantlab/live/broker/`](./quantlab/live/broker/)、[`quantlab/live/risk/`](./quantlab/live/risk/)

V3.1 的核心目标：**同一份 strategy 代码能在 Backtest / Paper / Live 三种模式下无缝切换**，不要在策略层写 `if mode == "live"` 这种判断。

### 15.1 关键抽象：`BaseExecution`

```python
class BaseExecution(ABC):
    def submit(self, target_portfolio) -> List[Order]:
        """把 TargetPortfolio 转成 Order 并撮合，return 实际发出的 Order"""
```

三种实现：

| 类 | 用途 | 关键差异 |
|----|------|---------|
| `BacktestExecution` | 离线回测 / 网格搜索 | 同步撮合，无延迟 |
| `PaperExecution` | 模拟撮合（实盘前冒烟） | 走 `PaperBroker` 喂模拟价 |
| `LiveExecution` | 实盘 | 走 `IBKRBroker` / `BinanceBroker` |

切换靠 `ExecutionFactory`：

```python
exec = ExecutionFactory.create(
    mode="paper",       # "backtest" / "paper" / "live"
    portfolio=portfolio,
    broker=broker,
)
```

### 15.2 统一 Order / FillEvent 字段

```python
@dataclass
class Order:
    id: str                  # 框架内 id
    symbol: str
    side: str                # "BUY" / "SELL"
    qty: int
    price: float
    order_type: str          # "MARKET" / "LIMIT"
    status: str              # "NEW" / "FILLED" / "REJECTED" / ...
    client_order_id: str     # UUID 幂等键（V3.1 新增）
```

`FillEvent` 无论来自 BacktestEngine / PaperBroker / 实盘 Exchange，都遵循同一结构：

```python
FillEvent(
    symbol, quantity, price, commission, timestamp,
    broker_id, source,   # source ∈ {"backtest", "paper", "ibkr", "binance"}
)
```

### 15.3 统一事件类型

`MarketEvent / SignalEvent / OrderEvent / FillEvent` 在所有模式下**同构**，靠 `source` 字段标识来源。这样 backtest 出来的结果可以**直接**和 live 结果在同一面板对比（V3.2 dashboard）。

### 15.4 RiskManager（统一）

`quantlab/live/risk/` 提供：
- `RiskManager` 串联多个 `RiskCheck`
- 内置 `OrderSizeCheck` / `PositionLimitCheck` / `DailyLossCheck` / `LeverageCheck`
- `KillSwitch(EmergencyStop)` 触发后所有新单都拒

**所有 live 模式必加**：`OrderSizeCheck` + `KillSwitch(estop)`（参见 [§14.2](#142-必加-riskmanager)）。

### 15.5 演示

```bash
python examples/run_live_paper.py
# 256 bars, 30 fills, equity=89808, return=-10.19%
```

---

## 16. V3.2 可观测性中心

> 目录：[`quantlab/monitoring/`](./quantlab/monitoring/)

V3.2 解决"为什么亏钱不知道"、"系统是不是黑盒"的问题。

### 16.1 TradeLogger（统一日志）

```python
from quantlab.monitoring import TradeLogger
logger = TradeLogger(log_dir="logs")
logger.log_fill(symbol="AAPL", price=150.0, qty=100, pnl=0.0)
```

**标准字段**：`timestamp, event_type, symbol, action, price, qty, pnl, source, trace_id`。

替换所有 `print()` 调试，统一格式便于后续 parse。

### 16.2 MetricsCollector（指标采集）

跟踪：
- `PnL` / `equity_curve` / `drawdown`
- `Exposure`（按 `|qty × price| / equity`）
- `WinRate` / `ProfitFactor` / `Sharpe`
- `Latency`（事件从 market → fill 的延迟）

### 16.3 EventTracer（事件追踪）

**核心创新**：`MarketEvent → SignalEvent → OrderEvent → FillEvent → PortfolioUpdate` 全链路共用一个 `trace_id`。

```python
trace_id = tracer.new_trace("market", bar_ts)
tracer.link(trace_id, "signal", signal_event)
tracer.link(trace_id, "order",  order_event)
tracer.link(trace_id, "fill",   fill_event)
# 任何 trace_id 反查都能拿到完整链路
```

写入 `logs/traces.jsonl`，便于回溯"这一笔亏钱的订单当时发生了什么"。

### 16.4 AlertManager（告警）

内置告警规则：
- `PNL_THRESHOLD`：累计 PnL 跌破阈值
- `DRAWDOWN_BREACH`：最大回撤跌破阈值
- `CONSECUTIVE_LOSS`：连续 N 笔亏损
- `SLIPPAGE_ABNORMAL`：实际成交价偏离理论价 > X bps
- `ORDER_REJECT`：订单被拒 / kill switch 触发

告警分级：`WARN` / `CRITICAL` / `FATAL`，`FATAL` 触发全局停机。

### 16.5 Dashboard

```python
from quantlab.monitoring import Dashboard
Dashboard(metrics=collector, tracer=tracer, alerts=alerts).render(
    out_path="logs/dashboard.png"
)
```

- matplotlib 出图：Equity Curve / Drawdown / Positions / Orders / Trades
- streamlit 实时面板（可选）
- `Agg` backend 支持沙箱无显示器环境

### 16.6 SystemContext（中心对象）

```python
@dataclass
class SystemContext:
    strategy, portfolio, execution, broker,
    logger, metrics, tracer, alert,
```

**所有模块依赖 `SystemContext` 而不是互相 import**。这是 V3.2 起的新约束。

### 16.7 演示

```bash
python examples/run_observability.py
# 300 bars, 255 traces, 60 fills, 132 alerts
# logs/traces.jsonl / events_paper.log / alerts.log / dashboard.png
```

---

## 17. V3.3 可恢复运行时

> 目录：[`quantlab/runtime/`](./quantlab/runtime/)

V3.3 解决"程序崩了能不能恢复"、"事件丢了能不能补"的问题。**9 个核心组件**：

| 组件 | 职责 |
|------|------|
| `StateSnapshot` | 状态快照（portfolio / cash / positions / orders） |
| `CheckpointManager` | 定时存盘（按 time / ticks / trades） |
| `RecoveryManager` | 启动时加载最近 checkpoint 恢复 |
| `ConsistencyChecker` | 对账：本地状态 vs broker 实际状态 |
| `ReplayEngine` | 用持久化事件重放验证一致性 |
| `ShutdownManager` | 优雅停机（停数据 / 完单 / 存盘 / 关 broker） |
| `TradeLock` | 关键段加锁（防多线程改 order state） |
| `EventLog` | 事件持久化（MarketEvent / OrderEvent / FillEvent） |
| `Recovery` | 上述组件串联 |

### 17.1 启动流程

```
1) RecoveryManager.load_latest()
2) 恢复 portfolio / positions / cash / open_orders
3) ConsistencyChecker.check()   不一致则告警 + 停机
4) 启动主循环
5) CheckpointManager 每 60s / 50 ticks / 10 trades 存盘
6) ShutdownManager 收到 SIGTERM/SIGINT → 完单 + 存盘 + 关 broker
```

### 17.2 幂等性

`Order` 的 `client_order_id` 是 **UUID 字符串**，Broker 端按它去重：

```python
# PaperBroker 内部
if order.client_order_id in self._seen_client_order_ids:
    return self._id_map[order.client_order_id]   # 重放
```

实盘 broker 也走同样协议（IBKR `client_id` / Binance `clientOrderId`）。

### 17.3 演示

```bash
python examples/run_resumable.py
# Phase 1: 50..100 bars + checkpoint
# Phase 2: final snapshot
# Phase 3: restart + recovery (equity=99949.39)
# Phase 4: ReplayEngine 299 bars, 0 diffs
# Phase 5: graceful shutdown
```

### 17.4 V3.3 vs V3.1 兼容性

- `run_live_paper.py`（V3.1）仍然 0 改动跑通 ✅
- `run_observability.py`（V3.2）仍然 0 改动跑通 ✅
- V3.3 = 增强层，不破坏老路径

---

## 18. V3.4 多策略 × 多账户矩阵

> 目录：[`quantlab/runtime/` 下的 `account_manager.py` / `allocation.py` / `router.py` / `strategy_runtime.py` / `supervisor.py`](./quantlab/runtime/)

V3.4 解决"能不能同时跑多个策略在多个账户"的问题。**这是从回测框架到生产系统的最后一步**。

### 18.1 Account（账户模型）

```python
@dataclass(slots=True)
class Account:
    account_id: str
    cash: float
    equity: float
    positions: Dict[str, int]      # symbol → qty
    broker_name: str               # "PAPER" / "IBKR" / "BINANCE"
    risk_profile: str              # "low" / "medium" / "high"
```

### 18.2 AccountManager（多账户管理）

```python
am = AccountManager()
am.create_account("acc_low",  cash=100000, broker_name="PAPER", risk_profile="low")
am.create_account("acc_mid",  cash=150000, broker_name="PAPER", risk_profile="medium")
am.create_account("acc_high", cash=200000, broker_name="IBKR",  risk_profile="high")
```

**硬约束**：`Account.cash` 不互通，资金隔离。

### 18.3 StrategyRuntime（独立运行单元）

一个 `StrategyRuntime` 就是一个完整的"小交易系统"：

```python
class StrategyRuntime:
    runtime_id: str
    strategy: SignalStrategy
    portfolio: Portfolio
    execution: BaseExecution
    broker: BrokerAdapter
    constructor: PortfolioConstructor
    account_id: str
```

**V3.4 硬约束**：
- 状态完全独立（不共享 `factor_cache` / `tradebook` / `last_target`）。
- 每个 runtime 自己的 `RuntimeStats(bars, signals, orders, fills, last_pnl, last_equity, stopped)`。
- `full_data` 在注册时一次性传入（`StrategyRuntime(full_data={...})`），首次算 signal 用全量 DataFrame 避免 `numpy.float64.rolling` 报错。

### 18.4 StrategyRegistry（策略注册器）

```python
registry = StrategyRegistry()
registry.register("MACross", MACrossStrategy)
registry.register("RSI",     RSIStrategy)
registry.register("Alpha001", Alpha001Strategy)
```

### 18.5 AllocationEngine（策略 × 账户分配）

```python
allocation = FixedAllocation({
    "macross_low": [("acc_low", 0.6), ("acc_mid", 0.4)],
    "rsi_high":    [("acc_high", 1.0)],
    "alpha_high":  [("acc_mid", 0.5), ("acc_high", 0.5)],
})
ae = AllocationEngine(allocation)
```

权重和必须 = 1.0（构造时校验）。

### 18.6 OrderRouter（订单路由）

唯一对外出口：

```python
router = OrderRouter(account_manager=am, allocation_engine=ae)
router.register_runtime("macross_low", broker=broker_low)
# ...
routed = router.route(order, "macross_low")
# → [(acc_low, 360 股), (acc_mid, 240 股)]   同一 client_order_id
```

**拆单 + 路由**：按 allocation 拆成 N 个子单，每个子单带原 `client_order_id`（幂等）。

### 18.7 PortfolioSupervisor（总调度器）

```python
sup = PortfolioSupervisor(registry, account_manager=am, allocation_engine=ae)

rt1 = sup.register_strategy("macross_low", "MACross", params={"fast":5,"slow":20},
                            account_id="acc_low", broker=broker_low, full_data=data)
rt2 = sup.register_strategy("rsi_high",    "RSI",     params={"period":14},
                            account_id="acc_high", broker=broker_high, full_data=data)
rt3 = sup.register_strategy("alpha_high",  "Alpha001", params={"period":10},
                            account_id="acc_mid", broker=broker_mid, full_data=data)

for ts, bar in market_stream:
    sup.on_bar(bar, ts)              # 广播 → 各 runtime 独立处理
    if sup.global_kill_switch.is_set():
        break
```

**Supervisor 的边界**：
- ✅ 广播行情、收集 stats、维护全局 Kill Switch、调 `print_report`
- ❌ **不**直接改 runtime 内部 portfolio / execution / broker 状态

### 18.8 全局 Kill Switch

```python
# PortfolioSupervisor 内置
if any_runtime_equity < 80000:
    sup._request_global_kill(reason=...)
    #  → global_kill_switch.set()
    #  → 所有 runtime.stop() 被调
    #  → 主循环退出
```

系统级兜底，任一 runtime 爆仓即全局停机。

### 18.9 演示

```bash
python examples/run_multi_strategy.py
# 3 strategies × 3 accounts × 3 brokers
# 300 bars, 27515 orders, 27515 fills, kill_switch=False
# OrderRouter: 600 股 AAPL → acc_low 360 + acc_mid 240 (同一 client_order_id)
```

### 18.10 演示输出

```
============================================================
  V3.4 PortfolioSupervisor Report
============================================================
  bars processed     = 300
  total orders       = 27515
  total fills        = 27515
  kill switch        = False

  Runtimes:
    rt_macross_low            strat=MACrossStrategy   acc=acc_low    orders=103 fills=103 equity=303679.21
    rt_rsi_high               strat=RSIStrategy       acc=acc_high   orders= 62 fills= 62 equity=256619.96
    rt_alpha_high             strat=Alpha001Strategy  acc=acc_mid    orders= 40 fills= 40 equity=164919.47
```

### 18.11 V3.4 新能力总结

| 能力 | 之前 (V3.3) | V3.4 |
|------|------------|------|
| 多策略并行 | ❌ | ✅ |
| 多账户管理 | ❌ | ✅ |
| 资金隔离 | n/a | ✅ |
| 统一风控 | 单引擎 | ✅ 系统级 Kill Switch |
| 资金分配 | 写死 | ✅ AllocationEngine |
| 订单路由 | 直连 broker | ✅ OrderRouter（拆单+幂等） |
| 跨策略追踪 | ❌ | ✅ Supervisor report |
| 扩展性 | n/a | ✅ 加新策略 = `registry.register()` + `sup.register_strategy()` |

---

## 19. V3.5 Execution Fidelity Layer

> 核心命题：**让"纸上交易" ≈ "真实交易"**。把回测从"假设你能成交"升级为"真实模拟你能不能成交"。

### 19.1 为什么需要这一层

普通回测假设：
- 订单**瞬间以中价成交**
- 没有对手盘，没有深度限制
- 滑点是**常数 bps**
- 没有延迟

这导致"纸面收益"和"实盘收益"差距 20~50%，机构叫这个差距为**"Paper-to-Live Gap"**。V3.5 的目标就是**把这段 gap 显式化、可量化、可控化**。

### 19.2 模块结构

```
quantlab/execution/fidelity/
├── orderbook/
│   ├── simulator.py        # 订单簿模拟器（生成 asks/bids）
│   └── liquidity_model.py  # 流动性模型（深度 + spread）
├── impact/model.py         # 市场冲击模型（sqrt / linear / power）
├── latency/model.py        # 延迟模型
├── cost/model.py           # 综合成本模型（fee / slippage / impact / opportunity）
├── fill_engine.py          # 成交引擎（限价/市价 + 部分成交）
├── matcher.py              # 多档撮合
├── reconciliation.py       # 成交对账（本地 vs 交易所）
├── replay.py               # 确定性回放
├── shadow.py               # 影子模式（paper vs live 对比）
├── truth.py                # 真实 PnL（扣除全部成本）
└── adaptive.py             # 自适应执行计划
```

### 19.3 核心模块说明

#### 19.3.1 Orderbook Simulator — 订单簿模拟
- 输入：`mid_price, volatility, volume`
- 输出：ask/bid 多档（5~20 档），每档含 `price, qty`
- 算法：在 mid 价附近按对数正态分布生成 depth，spread 受 `volatility` 驱动

#### 19.3.2 Impact Model — 市场冲击
三种模型可选：
- **Sqrt**（默认）：`impact = σ × c × sqrt(participation)`，**学术主流**（Almgren-Chriss）
- **Linear**：`impact = σ × c × participation`，保守模型
- **Power**：`impact = σ × c × participation^α`，通用框架

输出分**永久冲击**和**暂时冲击**，永久冲击不会被回退。

#### 19.3.3 Latency Model — 延迟模型
- 分解为：`send_latency + exchange_latency + recv_latency`
- 默认中位数 50ms，可调分布（对数正态）
- 配合 `latency_fragility` 测试策略对延迟的脆弱性

#### 19.3.4 Cost Model — 综合成本
```
total_cost = fee_cost 
           + slippage_cost 
           + impact_cost 
           + opportunity_cost 
           + funding_cost
```
每个分量按 `bps` 标准化，可单独查询或汇总。

#### 19.3.5 Fill Engine — 成交引擎
- 支持 **市价单 / 限价单**
- 支持 **部分成交**（多档撮合）
- 输出完整 `Fill` 对象：`fill_qty, fill_price, slippage_bps, commission, is_partial`

#### 19.3.6 Reconciliation — 成交对账
- 本地成交 vs 交易所回报逐笔对账
- 不匹配项标记：`MISSING / EXTRA / QTY_MISMATCH / PRICE_MISMATCH`
- 提供对账报告

#### 19.3.7 Replay — 确定性回放
- 给定相同 input + seed，**逐 byte 重现**回放过程
- 配合 V3.3 `RecoveryManager` 做崩溃后精确恢复

#### 19.3.8 Shadow Mode — 影子模式
- 同时运行 paper 和 live，记录每次成交差异
- 三档告警：`OK / WARNING / CRITICAL`
- 用于 **paper→live 灰度切换**前的最后一关

#### 19.3.9 True PnL — 真实 PnL
- 区别于"理论 PnL"，**扣完全部成本**后的 PnL
- 包含：`gross_pnl, fee, slippage, impact, true_pnl, true_pnl_bps, cost_drag_bps`
- `cost_drag_bps` 量化成本对收益的拖拽幅度

#### 19.3.10 Adaptive — 自适应执行
- 输入：订单参数 + 市场状态（volatility, liquidity_score, urgency）
- 输出：执行计划（切片数 + 切片量 + 切片延迟 + 订单类型）
- 内部根据市场状态判断 `regime`（trending / ranging / volatile）和 `style`（aggressive / passive / neutral）

### 19.4 集成方式

#### Python API
```python
from quantlab.execution.fidelity import (
    OrderbookSimulator, ImpactModel, LatencyModel,
    CostModel, FillEngine, TruePnLTracker, ShadowMode,
    AdaptiveExecutionPlanner,
)

# 1. 生成订单簿
sim = OrderbookSimulator()
book = sim.generate(mid_price=50000, volatility=0.02, volume=1_000_000)

# 2. 模拟扫单
result = sim.sweep(book, side="BUY", qty=10)
print(result.avg_price, result.impact_bps)

# 3. 算成本
cost = CostModel().calculate(
    symbol="BTCUSDT", side="BUY", qty=10, price=50000,
    slippage_bps=2.0, volume=1_000_000, volatility=0.02,
)
print(cost.total_cost)  # 包含 fee + slippage + impact + ...

# 4. 真实 PnL
tracker = TruePnLTracker()
tracker.update_position("BTCUSDT", qty=0.5, avg_entry=50000)
tracker.update_price("BTCUSDT", 51000)
report = tracker.compute_true_pnl()
print(report.true_pnl, report.cost_drag_bps)
```

#### HTTP API（FastAPI）
- `GET /api/v1/fidelity/status` — 全局状态
- `POST /api/v1/fidelity/orderbook/generate` — 生成订单簿
- `POST /api/v1/fidelity/orderbook/sweep` — 扫单
- `POST /api/v1/fidelity/impact/calculate` — 计算冲击
- `POST /api/v1/fidelity/impact/suggest-split` — 建议拆单
- `POST /api/v1/fidelity/cost/calculate` — 计算成本
- `POST /api/v1/fidelity/fill/process` — 处理订单
- `POST /api/v1/fidelity/adaptive/plan` — 生成执行计划
- `POST /api/v1/fidelity/truth/position` / `/price` / `GET /pnl` — 真实 PnL
- `POST /api/v1/fidelity/shadow/*` — 影子模式

#### 前端
- `FidelityStudio.vue` — 7 个 Tab 页：Overview / Order Book / Impact / Cost / Fill Engine / Shadow Mode / Adaptive / True PnL
- 路径：`/fidelity`

### 19.5 V3.5 注意事项

1. **冲击模型按品种选**：股票用 `linear`（受冲击衰减慢），crypto 用 `sqrt`（Almgren-Chriss 标准），低流动性用 `power`。
2. **CostModel 的 funding_cost 仅 crypto 有**：股票策略不要传 funding。
3. **ShadowMode 不是校验工具**：它是**告警**。paper 和 live 的差异 **永远存在**，但 > X bps 就要调查。
4. **Replayer 的种子**：生产环境别忘记录 `seed`，事故复盘时能 byte-by-byte 重现。
5. **Adaptive Planner 不会自动下单**：它只**生成计划**，执行要走 `StrategyRuntime` 的 Execution 通道。

---

## 20. V3.6 Execution-Aware Alpha Layer

> 核心命题：**从"预测收益"到"真实可交易"**。没有这一层，你在优化"数学正确性"；有了这一层，你在优化"市场存活率"。

### 20.1 为什么需要这一层

普通 alpha 评估：
- IC 0.08，Sharpe 2.0 → **看起来很棒**
- 但实盘可能：成交太慢、滑点太大、换手太高、延迟敏感
- 真实 `real_score < 0`

V3.6 的目标：**在策略进 paper/live 之前**，系统地评估它"能不能活下来"。

### 20.2 完整闭环

```
Research Alpha
  ↓
ML Validation
  ↓
Auto Research
  ↓
Execution Fidelity Layer (V3.5)
  ↓
Execution-Aware Alpha Layer (V3.6)  ← 本层
  ↓
Paper Trading
  ↓
Live Trading
  ↓
Observe Studio
```

### 20.3 10 个核心模块

```
quantlab/execution/alpha_aware/
├── realizability.py        # 1. Alpha Realizability Engine
├── turnover.py             # 2. Turnover Pressure Model
├── liquidity_filter.py     # 3. Liquidity-Aware Alpha Filter
├── sensitivity.py          # 4. Execution Sensitivity Test
├── latency_fragility.py    # 5. Latency Fragility Test
├── impact_backtest.py      # 6. Market Impact Backtest
├── adj_sharpe.py           # 7. Execution-Adjusted Sharpe
├── survival.py             # 8. Alpha Survival Filter
├── features.py             # 9. Execution-Aware Feature Engineering
└── tradeability.py         # 10. Tradeability Score System
```

#### ① Alpha Realizability Engine — 可实现性评估
核心评分：
```
real_score = signal_strength 
            × liquidity_score 
            × turnover_penalty 
            × cost_adjusted_return
```
- 信号强但**不能成交** → 0
- 论文 IC=0.08、Sharpe=2.0，真实环境可能 real_score < 0

#### ② Turnover Pressure Model — 换手压力模型
- 计算 `turnover = Σ|position_t - position_{t-1}|`
- 输出：`avg_daily_turnover, max_daily_turnover, annual_turnover, annual_cost, cost_drag_bps, pressure_score`
- `pressure_score = avg_component × 0.5 + vol_component × 0.2 + max_component × 0.3`
- 高换手 → 成本爆炸 → 不可持续

#### ③ Liquidity-Aware Alpha Filter — 流动性过滤
- 指标：`volume, spread, depth, impact_cost`
- 四维评分 → 总分 → `PASS / WARN / REJECT`
- 过滤规则：`volume < threshold → reject`

#### ④ Execution Sensitivity Test — 执行敏感性测试
- 模拟 `slippage × 0.5x, 1x, 2x, 3x, 5x`
- 输出：`sharpe_stability, return_degradation, breakpoint_multiplier`
- breakpoint = 让收益归零的 slippage 倍数
- 收益崩塌 → alpha 不可执行

#### ⑤ Latency Fragility Test — 延迟脆弱性测试
- 模拟 `delay = 1ms, 10ms, 100ms, 500ms, 1000ms, 5000ms`
- 输出：`alpha_half_life_ms, critical_latency_ms, latency_class, is_scalable`
- 依赖极低延迟 → 不可扩展 alpha

#### ⑥ Market Impact Backtest — 冲击回测
- 普通回测：假设无限成交
- 冲击回测：订单影响价格
- `real_sharpe = paper_sharpe × (1 - cost_ratio)`
- `real_return = paper_return × (1 - return_decay)`

#### ⑦ Execution-Adjusted Sharpe — 执行调整夏普
```
Sharpe_real = Sharpe_paper 
              - fee_penalty 
              - slippage_penalty 
              - impact_penalty
```
- 这是机构内部真正看的指标
- 等级 A~F（A: ≥2.0, B: ≥1.5, C: ≥1.0, D: ≥0.5, F: <0.5）

#### ⑧ Alpha Survival Filter — 生存过滤器
- 综合评分 IC 稳定性 + 换手 + 滑点 + 流动性 + 延迟
- 输出 `survival_score ∈ [0, 1]` + `survives / dies / marginal`
- 通过线：`survival_score >= 0.6` 且 `real_sharpe >= 0.5`

#### ⑨ Execution-Aware Feature Engineering — 执行感知特征
- `RSI → RSI_adjusted`
- 加入：`liquidity weighting, turnover penalty, impact scaling`
- 变成 **Execution-aware feature space**
- 高质量的低换手、低冲击的因子会被"放大权重"

#### ⑩ Tradeability Score System — 可交易评分系统（最终层）
```
Alpha Score = (Predictive Power 
               × Executability 
               × Stability 
               × Cost Efficiency) ^ 0.25
```
- 几何平均 → 任何一项为 0 整个分数归零
- 评级：`S / A / B / C / D / F`
- **最终不再选"Sharpe 最高的策略"，而是"最能活下来的策略"**

### 20.4 集成方式

#### Python API
```python
from quantlab.execution.alpha_aware import (
    AlphaRealizabilityEngine, TurnoverPressureModel,
    LiquidityAlphaFilter, ExecutionSensitivityTest,
    LatencyFragilityTest, MarketImpactBacktest,
    ExecutionAdjustedSharpe, AlphaSurvivalFilter,
    ExecutionAwareFeatures, TradeabilityScoreSystem,
)

# 1. 可实现性
report = AlphaRealizabilityEngine().evaluate(metrics, constraints)
print(report.real_score, report.verdict)  # 'TRADABLE' / 'UNTRADABLE'

# 2. 换手压力
turnover = TurnoverPressureModel().analyze(positions=[0.1, 0.15, 0.12], capital=1_000_000)
print(turnover.pressure_score, turnover.is_sustainable)

# 3. 流动性过滤
filt = LiquidityAlphaFilter().check(metrics)
print(filt.verdict, filt.overall_score)  # 'PASS' / 'WARN' / 'REJECT'

# 4. 一键全流程
system = TradeabilityScoreSystem()
result = system.evaluate(metrics, constraints, survival_input)
print(result.alpha_score, result.rank, result.is_recommended)
```

#### HTTP API（FastAPI）
- `POST /api/v1/alpha-aware/realizability/evaluate`
- `POST /api/v1/alpha-aware/turnover/analyze`
- `POST /api/v1/alpha-aware/liquidity/filter`
- `POST /api/v1/alpha-aware/sensitivity/test`
- `POST /api/v1/alpha-aware/latency/fragility`
- `POST /api/v1/alpha-aware/impact/backtest`
- `POST /api/v1/alpha-aware/sharpe/adjusted`
- `POST /api/v1/alpha-aware/survival/evaluate`
- `POST /api/v1/alpha-aware/features/adjust`
- `POST /api/v1/alpha-aware/tradeability/score`
- `POST /api/v1/alpha-aware/evaluate/all` — 一键全流程

#### 前端
- `AlphaAwareStudio.vue` — 10 个 Tab 页 + 一键全流程评估
- 路径：`/alpha-aware`
- 顶部 5 个 summary 卡片：可实现性、生存判定、可交易评级、真实夏普、推荐实盘

### 20.5 评分体系速查

| 评级 | Alpha Score | 推荐 |
|------|-------------|------|
| **S** | ≥ 0.80 | 强烈推荐 |
| **A** | ≥ 0.65 | 推荐 |
| **B** | ≥ 0.50 | 谨慎 |
| **C** | ≥ 0.35 | 不推荐 |
| **D** | ≥ 0.20 | 拒绝 |
| **F** | < 0.20 | 强烈拒绝 |

### 20.6 V3.6 注意事项

1. **real_score 是 0~1，不是 R²**：表示"在真实环境下还能保留多少原 alpha"。
2. **Tradeability 用几何平均**：单项 0 直接归零 → 任何短板都要修。
3. **Latency Fragility 是机构指标**：散户策略会得到"SCALABLE"，不代表真的好；要看 `critical_latency_ms` 绝对值。
4. **Feature Engineering 谨慎用**：执行感知特征**只在 live 阶段使用**，研究阶段用原始特征避免引入未来函数。
5. **生存判定 survival_score 要看具体分数**而不是**survives 布尔值**——0.61 和 0.95 都"survives"，但差别巨大。

---

## 21. 主入口 `main.py` 的 16 个 Stage

`main.py` 是一个端到端 demo，把所有模块都验证一遍。整体流程：

| Stage | 模块 | 验证内容 |
|------:|------|----------|
| 1 | `quantlab.research` | `Experiment.run` 单次回测 + `Report.generate` |
| 2 | `quantlab.research` | `Report.to_dict` / `to_html` |
| 3 | `quantlab.research.walk_forward` | V1 `WalkForward` 按 bar 滚动 |
| 4 | `quantlab.research.validation` | `ValidationRunner`（双引擎一致性） |
| 5 | `quantlab.event_engine` | `EventEngine` 与 `BarEngine` 等价性校验 |
| 6 | `quantlab.optimizer` + `ValidationRunner` | `Optimizer` 全网格 + `validate_top_n` |
| 7 | `quantlab.data` + `quantlab.core` | V1.9 multi-asset API（`ctx.symbols` / `Portfolio.get_position` / `TradeBook.pnl_by_symbol` / `PortfolioSnapshot`） |
| 8 | `quantlab.adapters.vectorbt_adapter` | V2.0 VectorBTAdapter 用 `from_orders` + constructor 组合权重 |
| 9 | `quantlab.parallel_optimizer` | V2.1 多进程网格搜索（initializer + early filter + top_k） |
| 10 | `quantlab.research.walk_forward` | V2.2 `WalkForwardRunner`（按年 + 三阶段 + HTML 报告） |
| 11 | `quantlab.research.tracker` | V2.3 `ExperimentTracker`（SQLite 持久化 + search + leaderboard） |
| 12 | `quantlab.live` + `quantlab.risk` | V2.5 `LiveEngine` + `PaperBroker` + `RiskManager` + `KillSwitch` + `ReplayMarketData` |
| 13 | `quantlab.live.execution` | V3.1 `ExecutionFactory` 统一三模式（backtest/paper/live）+ `client_order_id` 幂等 |
| 14 | `quantlab.monitoring` | V3.2 `TradeLogger` + `MetricsCollector` + `EventTracer(trace_id)` + `AlertManager` + `Dashboard` |
| 15 | `quantlab.runtime` | V3.3 `CheckpointManager` + `RecoveryManager` + `ReplayEngine` + `ShutdownManager` |
| 16 | `quantlab.runtime` | V3.4 `PortfolioSupervisor` + `StrategyRuntime` + `AccountManager` + `OrderRouter` |

每个 stage 都用 `try/except` 包装，vectorbt / 子进程不可用时优雅跳过，方便在受限环境跑。

---

## 20. 快速上手

### 20.1 安装依赖
最小依赖：`numpy / pandas`。
可选：`vectorbt`（走 VBT 快引擎时需要）、`matplotlib`（HTML 报告画图）。

```bash
pip install numpy pandas
# 可选
pip install vectorbt matplotlib
```

### 20.2 跑全量 demo
```bash
cd d:/python_workspace/回测框架
python main.py
```
会依次输出 16 个 Stage 的运行结果到 stdout，并生成：
- `reports/parallel_grid.csv`
- `reports/validation_report.csv`
- `reports/wf_report.html`
- `storage/research.db`

### 20.3 跑双引擎对比
```bash
python compare.py
```
比较 `BarEngine(EventBus 风格)` 和 `VectorBTAdapter` 在同一份数据 / 同一组策略上的最终权益。

### 20.3.1 跑 V3.x 演示
```bash
# V3.1 统一 Execution
python examples/run_live_paper.py

# V3.2 可观测性
python examples/run_observability.py

# V3.3 可恢复运行时
python examples/run_resumable.py

# V3.4 多策略 × 多账户
python examples/run_multi_strategy.py
```

### 20.4 写一个新策略
```python
# my_strategy.py
import pandas as pd
from quantlab.signals.base import SignalStrategy
from quantlab.factors.ma import ma

class MyCrossStrategy(SignalStrategy):
    def __init__(self, fast=10, slow=30):
        self.fast, self.slow = fast, slow

    def signal(self, ctx) -> pd.DataFrame:
        return pd.DataFrame({
            sym: (ma(ctx, sym, self.fast) > ma(ctx, sym, self.slow)).astype(int)
            for sym in ctx.data
        })
```

### 20.5 跑一次回测
```python
from quantlab.engine import BarEngine
from quantlab.portfolio_construction import TopN
from quantlab.execution import PercentageCommission, PercentageSlippage, TargetWeightExecution
from quantlab.research import Experiment, Report

engine = BarEngine(
    strategy=MyCrossStrategy(fast=10, slow=30),
    portfolio_constructor=TopN(n=2),
    execution_model=TargetWeightExecution(lot_size=1, position_tolerance=0.02),
    commission_model=PercentageCommission(rate=0.0003),
    slippage_model=PercentageSlippage(rate=0.0002),
    initial_cash=100000,
)

exp = Experiment(name="my_v1")
result = exp.run(
    strategy=MyCrossStrategy(fast=10, slow=30),
    engine=engine,
    data={"AAPL": df_aapl, "MSFT": df_msft},
    params={"fast": 10, "slow": 30},
)
print(Report(result).generate())
```

### 20.6 网格优化 + 双引擎验证
```python
from quantlab.adapters import VectorBTAdapter
from quantlab.optimizer import Optimizer
from quantlab.research import ValidationRunner

fast = VectorBTAdapter(constructor=TopN(n=2))
opt = Optimizer(strategy_cls=MyCrossStrategy, engine=fast)
df = opt.run(data, param_space={"fast": [5, 10, 20], "slow": [30, 60, 90]})
# df 已按 score 倒序

runner = ValidationRunner(
    fast_engine=fast,
    precise_engine=build_precise_engine(),  # BarEngine/EventEngine
    consistency_threshold=0.8,
)
val_df = runner.validate_top_n(
    optimizer_result=df,
    strategy_cls=MyCrossStrategy,
    data=data,
    top_n=10,
    output_csv="reports/validation_report.csv",
)
```

### 20.7 实验入库 + Leaderboard
```python
from quantlab.research.tracker import ExperimentRecord, ExperimentTracker

tracker = ExperimentTracker(
    strategy_registry={"MyCross": MyCrossStrategy},
    db_path="storage/research.db",
)

tracker.run(
    record=ExperimentRecord(
        name="my_v1",
        strategy_name="MyCross",
        params={"fast": 10, "slow": 30},
        tag="trend",
    ),
    engine=engine,
    data=data,
)
print(tracker.leaderboard(sort_by="sharpe", top=10))
```

### 20.8 Walk-Forward（V2.2）
```python
from quantlab.research.walk_forward import (
    WalkForwardRunner, WalkForwardReport,
)
from quantlab.adapters.vectorbt_adapter import VectorBTAdapter
from quantlab.parallel_optimizer import ParallelOptimizer
from quantlab.research.validation import ValidationRunner

wf = WalkForwardRunner(
    optimizer=ParallelOptimizer(
        strategy_cls=MyCrossStrategy,
        engine_spec=("vectorbt", {"fees": 0.0003, "slippage": 0.0002}),
        max_workers=4, top_k=5, early_split=0.3,
    ),
    validation_runner=ValidationRunner(
        fast_engine=VectorBTAdapter(constructor=TopN(n=2)),
        precise_engine=build_precise_engine(),
    ),
    event_engine=build_precise_engine(),
    train_years=2, test_years=1, top_train=3, top_val=1,
)
wf_v2 = wf.run(data=data, param_space={"fast": [10, 20], "slow": [60, 80]})
WalkForwardReport(wf_v2).to_html("reports/wf_report.html")
```

### 20.9 跑一次 Live / Paper 冒烟
```python
import os
os.environ["PARALLEL_USE_THREAD"] = "1"   # 或不用

from quantlab.live import (
    LiveEngine, PaperBroker, ReplayMarketData,
)
from quantlab.risk import (
    RiskManager, OrderSizeCheck, PositionLimitCheck,
    MaxOrderSize, MaxPositionLimit, EmergencyStop, KillSwitch,
)
from quantlab.execution import TargetWeightExecution

md = ReplayMarketData(data); md.subscribe(list(data.keys()))
pb = PaperBroker(market_data=md, tick_size=0.01, initial_cash=100000); pb.connect()

rm = RiskManager()
rm.add_check(OrderSizeCheck(MaxOrderSize(max_qty=10000)))
rm.add_check(PositionLimitCheck([MaxPositionLimit(symbol=s, max_qty=10000) for s in data]))
estop = EmergencyStop(threshold=-0.05)
rm.add_check(KillSwitch(estop))

live = LiveEngine(
    strategy=MyCrossStrategy(fast=5, slow=10),
    execution=TargetWeightExecution(lot_size=1, position_tolerance=0.02),
    market_data=md,
    broker=pb,
    risk_manager=rm,
    emergency_stop=estop,
    initial_cash=100000,
    log_dir="logs",
)
br = live.run(data=data)
print(br.source, br.raw, br.final_equity, br.total_return)
```

### 20.10 多策略 × 多账户（V3.4）

```python
import os
os.environ.setdefault("MPLBACKEND", "Agg")

from quantlab.live import PaperBroker, ReplayMarketData
from quantlab.signals import (
    MACrossStrategy, RSIStrategy, Alpha001Strategy,
)
from quantlab.portfolio_construction import TopN
from quantlab.runtime import (
    AccountManager, AllocationEngine, FixedAllocation,
    StrategyRegistry, PortfolioSupervisor,
)

# 1) 多账户
am = AccountManager()
am.create_account("acc_low",  cash=100000, risk_profile="low")
am.create_account("acc_mid",  cash=150000, risk_profile="medium")
am.create_account("acc_high", cash=200000, risk_profile="high")

# 2) 资金分配
ae = AllocationEngine(FixedAllocation({
    "macross_low": [("acc_low", 0.6), ("acc_mid", 0.4)],
    "rsi_high":    [("acc_high", 1.0)],
    "alpha_high":  [("acc_mid", 0.5), ("acc_high", 0.5)],
}))

# 3) 注册策略
registry = StrategyRegistry()
registry.register("MACross",  MACrossStrategy)
registry.register("RSI",      RSIStrategy)
registry.register("Alpha001", Alpha001Strategy)

sup = PortfolioSupervisor(registry, am, ae)

# 4) 给每个策略建独立 broker + 注册 runtime
def make_broker(initial_cash):
    md = ReplayMarketData(data); md.subscribe(list(data.keys()))
    pb = PaperBroker(market_data=md, tick_size=0.01,
                     commission_rate=0.0003,
                     initial_cash=initial_cash)
    pb.connect()
    return pb

broker_low  = make_broker(100000)
broker_mid  = make_broker(150000)
broker_high = make_broker(200000)

sup.register_strategy("macross_low", "MACross",
    params={"fast": 5, "slow": 20},
    account_id="acc_low",  broker=broker_low,
    constructor=TopN(n=2), full_data=data)
sup.register_strategy("rsi_high", "RSI",
    params={"period": 14, "oversold": 30, "overbought": 70},
    account_id="acc_high", broker=broker_high,
    constructor=TopN(n=2), full_data=data)
sup.register_strategy("alpha_high", "Alpha001",
    params={"period": 10},
    account_id="acc_mid",  broker=broker_mid,
    constructor=TopN(n=2), full_data=data)

# 5) 主循环：广播行情给所有 runtime
sym0 = list(data.keys())[0]
for i, ts in enumerate(data[sym0].index):
    if sup.global_kill_switch.is_set():
        break
    bar = {s: data[s].iloc[i] for s in data}
    sup.on_bar(bar, ts)

# 6) 报告
sup.print_report()
# V3.4 PortfolioSupervisor Report
#   rt_macross_low  MACross  acc_low    103 orders  103 fills  equity=303679
#   rt_rsi_high     RSI      acc_high    62 orders   62 fills  equity=256620
#   rt_alpha_high   Alpha001 acc_mid     40 orders   40 fills  equity=164919

# 7) OrderRouter 拆单
from quantlab.core.order import Order
routed = sup.router.route(
    Order(symbol="AAPL", quantity=600, price=150.0),
    strategy_id="macross_low",
)
# → [(acc_low, 360), (acc_mid, 240)]    共享同一 client_order_id
```

完整可跑版本见 `examples/run_multi_strategy.py`。

---

## 21. 数据格式约定

**Bar DataFrame**（`Dict[symbol, pd.DataFrame]`）至少含以下列：
- `open / high / low / close / volume`
- `DatetimeIndex`（`parse_dates=True, index_col=0`）

`data/AAPL.csv` 示例：
```csv
datetime,open,high,low,close,volume
2024-01-01,9.98,10.3,9.91,10.15,13495
2024-01-02,9.95,10.25,9.88,10.07,9708
...
```

多 symbol 共享同一时间索引。

---

## 22. 版本演进

| 版本 | 模块 | 关键变化 |
|------|------|----------|
| V1.0 | `core / engine` | 基础 BarEngine |
| V1.4 | `data` | StrategyContext + FactorCache（防 ma(20) 在 12 组参数中重算） |
| V1.8 | `research.validation` | ValidationRunner 双引擎一致性验证 |
| V1.9 | `core / portfolio_construction` | 多标的 + PortfolioConstructor（EqualWeight / TopN）+ PortfolioSnapshot |
| V1.x | `event / event_engine` | EventEngine 全解耦版（与 BarEngine 等价） |
| V2.0 | `adapters.vectorbt_adapter` | VectorBTAdapter 用 `from_orders` + constructor 组合权重策略 |
| V2.1 | `parallel_optimizer` | ParallelOptimizer：initializer 全局 data + early filter + top_k |
| V2.2 | `research.walk_forward` | WalkForwardRunner：按年切 + 三阶段 + Stability / Drift + HTML 报告 |
| V2.3 | `research.tracker` | ExperimentTracker + SQLite + Repository + Leaderboard |
| V2.4 | `core.tick / engine.tick_engine` | TickEngine + TickSlippage + BarToTickFeed + IntrabarExecution |
| V2.5 | `live / risk` | LiveEngine + PaperBroker + ReplayMarketData + OrderManager + RiskManager + KillSwitch |
| **V3.1** | `live.execution / live.broker / live.risk` | **统一 Execution**：`BaseExecution` + `ExecutionFactory` 三模式切换；`Order.client_order_id` 标准化；`live/broker/` + `live/execution/` + `live/risk/` 子包重整 |
| **V3.2** | `monitoring` | **可观测性中心**：`TradeLogger` + `MetricsCollector` + `EventTracer(trace_id 串联)` + `AlertManager` + `Dashboard` + `SystemContext`（替代 cross-import） |
| **V3.3** | `runtime` | **可恢复运行时**：`StateSnapshot` + `CheckpointManager` + `RecoveryManager` + `ConsistencyChecker` + `ReplayEngine` + `ShutdownManager` + `TradeLock` + `EventLog` |
| **V3.4** | `runtime` | **多策略 × 多账户矩阵**：`Account` + `AccountManager` + `StrategyRuntime`（状态隔离） + `StrategyRegistry` + `AllocationEngine` + `OrderRouter`（拆单+幂等） + `PortfolioSupervisor`（系统级 Kill Switch） |
| **V3.5** | `execution.fidelity` | **执行保真层**：订单簿模拟 + 市场冲击（sqrt/linear/power）+ 延迟模型 + 综合成本（fee+slippage+impact+opportunity+funding）+ 成交引擎（部分成交） + 多档撮合 + 成交对账 + 确定性回放 + 影子模式（paper vs live 对比） + True PnL（扣完全部成本） + 自适应执行计划（按 regime 切算法） |
| **V3.6** | `execution.alpha_aware` | **执行感知 Alpha 层**：Alpha Realizability Engine + Turnover Pressure Model + Liquidity-Aware Filter + Execution Sensitivity Test + Latency Fragility Test + Market Impact Backtest + Execution-Adjusted Sharpe + Alpha Survival Filter + Execution-Aware Feature Engineering + Tradeability Score System。**核心理念：从优化"数学正确性"到优化"市场存活率"** |

**架构演进总览**：

```
V1.x   单策略 + 单账户 + 多引擎               框架/工具
V2.x   + Optimizer / Walker / Tracker       研究平台
V3.1   统一 Execution（回测/paper/live 同构）  生产接口
V3.2   + 监控/告警/Trace                    可观测性
V3.3   + 状态恢复 / 事件重放 / 优雅停机        高可用
V3.4   + 多策略/多账户矩阵 / 系统级 Kill Switch  多租户/多账户
V3.5   + 订单簿/冲击/延迟/成本/对账/影子/True PnL  让纸上交易 ≈ 真实交易
V3.6   + 可实现性/换手/流动性/敏感性/生存/可交易  从数学正确到市场存活
```

---

## 附录 A：典型指标计算公式

- **Sharpe**：`mean(returns) / std(returns) * sqrt(252)`（年化）
- **Max Drawdown**：`min((equity - peak) / peak)`，peak 是 running max
- **Total Return**：`equity[-1] / equity[0] - 1`
- **Win Rate**：`sum(trade.pnl > 0) / len(trades)`
- **Profit Factor**：`sum(profit) / abs(sum(loss))`
- **Expectancy**：`win_rate * avg_win - (1 - win_rate) * avg_loss`
- **Exposure**：每天 in-pos 比例（多标的按 `|qty × last_price| / equity`）
- **Consistency Score**（双引擎）：`1 - |sharpe_fast - sharpe_precise| / max(|sharpe_fast|, |sharpe_precise|, eps)`
- **Stability Score**（WF）：`0.5 * param_consistency + 0.2 * oos_return_score + 0.3 * n_passed_ratio`
- **Parameter Drift**：相邻窗口 best_params 归一化欧氏距离

## 附录 B：常见注意事项

1. **`factor_cache` 必须清**：跨 Experiment / 跨 WalkForward 窗口 / ParallelOptimizer 每次 `_evaluate_one` 都要 `factor_cache.clear()`，否则不同长度的 Series 串味导致 `Can only compare identically-labeled Series objects`。
2. **VectorBT 偶发 SIGABRT**：在受限环境用 `SubprocessVectorBT`；`ParallelOptimizer` 下设 `PARALLEL_USE_THREAD=1` 切 ThreadPool。
3. **整数参数**：pandas 读 dict 后 `int` 会变 `float`，所有走 `int(v) if isinstance(v, float) and v.is_integer() else v` 转回，否则 `rolling(10.0)` 报错。
4. **TickEngine 的 snapshot_interval**：每 N ticks 才记一次 equity，过大会丢失精度。
5. **沙箱画图**：`os.environ["MPLBACKEND"] = "Agg"`，否则无显示器会崩。
6. **Paper broker 是同步成交**：撤单永远 False（V1 简化）。
7. **WalkForwardRunner 强制 copy engine**：`_run_test` 时 `copy.deepcopy(event_engine)` + 覆盖 `engine.strategy`，避免与 train_engine 共享状态。
8. **SQLite thread-safety**：`check_same_thread=False`，每次 query 走新 connection；启用 `PRAGMA foreign_keys = ON` 让 `ON DELETE CASCADE` 生效。

### B.1 V3.1+ 注意事项

9. **Execution 切换走 Factory**：不要在 strategy 代码里 `if mode == "live"`。统一用 `ExecutionFactory.create(mode=..., portfolio=..., broker=...)`，不同模式的差异由 `BaseExecution` 子类封装。
10. **`client_order_id` 必带**：所有 `Order` 必须设 `client_order_id`（框架自动生成 UUID）。PaperBroker / 实盘 broker 都会按它去重，重放时不会重复成交。
11. **不要混用 LiveEngine 和 ExecutionFactory**：V2.5 的 `LiveEngine` 还没迁移到新的 Execution 接口，**新代码走 `StrategyRuntime` + `PortfolioSupervisor`**。
12. **SystemContext 中心化**：V3.2 起新模块不要互相 import，通过 `SystemContext` 注入。TradeLogger / MetricsCollector / EventTracer / AlertManager 都是如此。

### B.2 V3.4 注意事项

13. **禁止共享 portfolio**：每个 `StrategyRuntime` 必须独立 `Portfolio`，`Supervisor` 不会、也不应该合并 portfolio。
14. **`full_data` 必须传**：`sup.register_strategy(..., full_data=data)`，否则 `signal()` 算在单行 DataFrame 上，`rolling` 直接报错（`numpy.float64 has no attribute rolling`）。
15. **allocation 权重和必须 = 1.0**：`FixedAllocation` 构造时校验，差 1% 都会抛 `ValueError`。
16. **OrderRouter 共享 client_order_id**：拆出来的子单**保留**原 `client_order_id`，broker 端按它判重，**不要**给每个子单生成新 UUID。
17. **系统级 Kill Switch 阈值**：默认 `equity < 80000` 触发全局停，可改 `PortfolioSupervisor._request_global_kill` 内部条件。**生产环境务必设**对应账户的 70% initial_cash。
18. **Account 不互通**：`am.get_account("acc_low")` 的 cash 改了，`acc_high` 不会变。如要"跨账户调拨"，自己写 Transfer（V3.4 不内置）。
19. **BacktestEngine 没有完整的 V3.4 支持**：`examples/run_multi_strategy.py` 用的是 `mode="paper"`。要纯回测模式需自建适配（V3.4 路线图：把 BarEngine 包装成 `BacktestBroker` + `BacktestExecution`）。
20. **资金分配 ≠ 风控**：allocation 决定"一笔单按 60/40 拆"，**不是**风控上限。单账户风控仍走 `RiskManager` + `OrderSizeCheck` + `KillSwitch`（V3.4 路线图：把 `RiskManager` 接入 `OrderRouter` 做 pre-submit 检查）。

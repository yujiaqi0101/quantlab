# 统一 Trading Core 设计文档

> 日期：2026-07-02
> 状态：待用户确认

## 1. 背景与目标

### 1.1 问题

QuantLab 现有3套 Paper Trading 实现，接口不统一：
- `execution/broker/paper.py` 的 PaperBroker（Broker接口，OrderRequest）
- `execution/paper/upgraded_broker.py` 的 UpgradedPaperBroker（独立，OMSOrder，有Bug）
- `paper_trading/engine.py` 的 PaperTradingEngine（A股每日收盘批量，独立）

还有两套策略抽象：
- `SignalStrategy`（signal() -> DataFrame，向量化信号面板）
- `BaseStrategy`（on_bar/exit_checker -> List[Order]，事件驱动）

### 1.2 目标

统一 Trading Core，实现 Backtest/Paper/Live 三模式共享同一套引擎：
- 同一套 Strategy Engine（EventStrategy 事件驱动接口）
- 同一套 OMS（OMSOrder 状态机）
- 同一套 Portfolio Engine（PositionBook + PortfolioBook）
- 同一套 Risk Engine
- 唯一变化：数据来源（DataFeed）和 Broker 类型

### 1.3 核心原则

1. **事件驱动为主接口**：EventStrategy.on_bar() -> List[OrderIntent]，最接近实盘
2. **SignalSet 通过适配器接入**：不废弃现有 ML Lab，通过 SignalStrategyAdapter 桥接
3. **复用现有 execution/ 组件**：OMS/Broker/PositionBook/PortfolioBook/FillEngine 直接复用
4. **以 Runtime 为骨架**：现有 execution/runtime/entry.py 的 Runtime 升级为 TradingCore

## 2. 整体架构

```
TradingCore（统一入口，升级自 Runtime）
    │
    ├── TradingMode（抽象层：决定数据来源+Broker类型）
    │     ├── BacktestMode   历史数据驱动 + PaperBroker(即时撮合)
    │     ├── PaperMode      实时行情 + PaperBroker(模拟撮合)
    │     └── LiveMode       实时行情 + 真实券商(Binance/IB/QMT)
    │
    ├── 共享组件层（直接复用 execution/ 现有代码）
    │     ├── OMS (OrderManager + OMSOrder 状态机)
    │     ├── Broker 抽象 (Broker base + PaperBroker)
    │     ├── PositionBook / PortfolioBook
    │     ├── FillEngine + SlippageModel
    │     └── RiskManager
    │
    └── 策略接口层
          ├── EventStrategy（事件驱动主接口：on_bar -> List[OrderIntent]）
          └── SignalStrategyAdapter（将现有 SignalStrategy 适配为事件驱动）
```

## 3. 策略接口统一

### 3.1 主接口 EventStrategy

```python
class EventStrategy(ABC):
    """统一策略接口。Paper/Live/Backtest 共用。"""
    name: str
    version: str

    @abstractmethod
    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        """每根K线/Tick到来时调用，返回订单意图列表。"""

    @abstractmethod
    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        """检查持仓出场，返回出场订单意图。"""

    def on_init(self) -> None: ...
```

### 3.2 数据结构

```python
@dataclass
class Bar:
    """单根K线/行情快照。"""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class OrderIntent:
    """策略产出的订单意图（非OMS订单）。"""
    symbol: str
    side: str           # 'buy' / 'sell'
    quantity: float
    order_type: str     # 'market' / 'limit'
    price: Optional[float] = None
    reason: str = ""

@dataclass
class Position:
    """持仓。"""
    symbol: str
    quantity: float
    entry_price: float
    entry_date: str
    current_price: float
    direction: str = "long"

    @property
    def value(self) -> float: return self.quantity * self.current_price
    @property
    def cost(self) -> float: return self.quantity * self.entry_price
    @property
    def unrealized_pnl(self) -> float: return self.value - self.cost

@dataclass
class TradingContext:
    """策略每日运行上下文。"""
    timestamp: datetime
    cash: float
    frozen_cash: float
    positions: Dict[str, Position]
    bar_data: Dict[str, pd.DataFrame]  # 历史K线缓冲
    universe: List[str]

    @property
    def total_value(self) -> float:
        return self.cash + self.frozen_cash + sum(p.value for p in self.positions.values())
```

### 3.3 SignalStrategyAdapter

```python
class SignalStrategyAdapter(EventStrategy):
    """将 SignalStrategy(信号面板模式) 适配为事件驱动。"""

    def __init__(self, signal_strategy: SignalStrategy, portfolio_constructor):
        self._strategy = signal_strategy
        self._constructor = portfolio_constructor

    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        # 1. 用当前ctx构造FactorContext
        # 2. 调用 signal_strategy.signal(ctx) 取当日信号行
        # 3. 用 portfolio_constructor 将信号转为目标权重
        # 4. 目标权重 vs 当前持仓 → 差异 → OrderIntent
        ...

    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        return []  # 信号面板模式出场由权重差异自动处理
```

## 4. 订单模型与 OMS 统一

### 4.1 统一到 OMSOrder

```
策略产出 OrderIntent
       │
       ▼
TradingCore._submit_intent(intent)
       │  转换为 OMSOrder
       ▼
OMS.create_order()  →  OMSOrder (状态: NEW)
       │
       ▼
Broker.submit_order(OrderRequest)  →  OMSOrder (状态: SUBMITTED)
       │
       ▼
Broker 撮合成交  →  OMS.apply_fill()  →  OMSOrder (状态: FILLED/PARTIAL)
       │
       ▼
PositionBook.apply_fill() + PortfolioBook.apply_fill()
```

### 4.2 三套订单模型处置

| 模型 | 处置 |
|---|---|
| OMSOrder（execution/core/oms/） | ✅ 唯一标准，直接复用 |
| OrderRequest（execution/broker/base.py） | ✅ 保留作为 Broker 调用契约 |
| Order（strategy/context.py 刚实现） | ❌ 废弃，由 OrderIntent 替代 |

### 4.3 OMS 状态机（复用现有）

```
NEW → PENDING_SUBMIT → SUBMITTED → PARTIAL → FILLED
                                  ↘ CANCELLED / REJECTED / EXPIRED
```

## 5. 三种模式的数据流

### 5.1 BacktestMode

```
DataFeed(历史K线) → 逐bar推送 → EventStrategy.on_bar()
    → OrderIntent → OMS → PaperBroker(即时撮合)
    → Fill → PositionBook/PortfolioBook → Performance记录
```
- 数据来源：历史K线（从文件/数据库读取）
- Broker：PaperBroker（即时成交，支持滑点模型）
- 特点：可快进、可重复、无网络延迟
- 复用：现有 BarEngine 改造为 BacktestMode 的 DataFeed

### 5.2 PaperMode

```
DataFeed(实时行情) → 逐bar/tick推送 → EventStrategy.on_bar()
    → OrderIntent → OMS → PaperBroker(模拟撮合)
    → Fill → PositionBook/PortfolioBook → 持久化到DB → 报告
```
- 数据来源：实时行情（QMT/东财/WebSocket）
- Broker：PaperBroker（模拟成交，支持部分成交/排队/滑点）
- 特点：实时运行、不可重复、有真实行情延迟

### 5.3 LiveMode

```
DataFeed(实时行情) → 逐bar/tick推送 → EventStrategy.on_bar()
    → OrderIntent → OMS → RealBroker(Binance/IB/QMT)
    → Fill → PositionBook/PortfolioBook → 持久化
```
- 数据来源：实时行情（券商API）
- Broker：真实券商接口
- 特点：真实资金、真实成交

### 5.4 三模式共享

EventStrategy / OMS / PositionBook / PortfolioBook / FillEngine / RiskManager 全部一致。

## 6. 废弃代码清理

| 废弃文件 | 原因 |
|---|---|
| quantlab/strategy/（整个目录） | 由 trading_core/ 下的 EventStrategy 替代 |
| quantlab/data/（整个目录） | 由 TradingCore 的 DataFeed 替代 |
| quantlab/database.py | 5张paper_*表保留但引擎层不用 |
| quantlab/paper_trading/（整个目录） | 由 TradingCore + PaperMode 替代 |
| quantlab/cli/（整个目录） | 重新设计 CLI |
| main.py（刚改造的CLI入口） | 恢复或重新设计 |
| tests/test_paper_trading.py | 废弃，重写 |
| tests/test_paper_trading_e2e.py | 废弃，重写 |

### 保留的代码

| 保留文件 | 原因 |
|---|---|
| execution/core/oms/ | OMSOrder + OrderManager 直接复用 |
| execution/broker/base.py | Broker 抽象 + OrderRequest 直接复用 |
| execution/broker/paper.py | PaperBroker 直接复用 |
| execution/position_book.py | 直接复用 |
| execution/portfolio_book.py | 直接复用 |
| execution/core/fills/ | FillEngine + SlippageModel 直接复用 |
| execution/runtime/engine.py | ProductionRuntime 直接复用 |
| execution/runtime/entry.py | Runtime 升级为 TradingCore |
| execution/risk/ | RiskManager 直接复用 |
| signals/base.py | SignalStrategy 保留，通过 Adapter 接入 |
| ml/signal_engine/ | SignalSet 保留，通过 Adapter 接入 |

### 需修复的Bug

- execution/paper/upgraded_broker.py 第122行：slippage_model.calculate() 应为 slippage_model.apply()（方法名和签名不匹配）

## 7. 模块结构

```
quantlab/
  ├── trading_core/                 # [NEW] 统一交易核心
  │   ├── __init__.py
  │   ├── core.py                   # TradingCore 主类（升级自 Runtime）
  │   ├── interfaces.py             # EventStrategy / OrderIntent / TradingContext / Bar
  │   ├── adapters/
  │   │   ├── __init__.py
  │   │   └── signal_adapter.py     # SignalStrategyAdapter
  │   └── modes/
  │       ├── __init__.py
  │       ├── base.py               # TradingMode 抽象基类
  │       ├── backtest.py           # BacktestMode（历史数据驱动）
  │       ├── paper.py              # PaperMode（实时行情+模拟撮合）
  │       └── live.py               # LiveMode（实时行情+真实券商）
  │
  ├── execution/                    # [保留] 共享组件层
  │   ├── core/oms/                 # OMSOrder + OrderManager（直接复用）
  │   ├── broker/                   # Broker抽象 + PaperBroker（直接复用）
  │   ├── position_book.py          # 直接复用
  │   ├── portfolio_book.py         # 直接复用
  │   ├── core/fills/               # FillEngine + SlippageModel（直接复用）
  │   ├── risk/                     # RiskManager（直接复用）
  │   └── runtime/engine.py         # ProductionRuntime（直接复用）
  │
  ├── signals/                      # [保留] SignalStrategy + Adapter接入
  ├── ml/                           # [保留] ML Lab + SignalSet
  └── cli/                          # [NEW] 重新设计的CLI
      ├── __init__.py
      ├── main.py                   # CLI主入口
      └── trading_cli.py            # trading子命令
```

## 8. TradingCore 主类设计

```python
class TradingCore:
    """统一交易核心 — Backtest/Paper/Live 三模式共享。"""

    def __init__(
        self,
        mode: TradingMode,
        initial_capital: float = 1_000_000,
        broker: Optional[Broker] = None,
        config: Optional[RuntimeConfig] = None,
    ):
        self.mode = mode
        self.runtime = ProductionRuntime(config or RuntimeConfig())
        self.broker = broker or mode.create_broker(initial_capital)
        self.oms = OrderManager()
        self.position_book = PositionBook()
        self.portfolio_book = PortfolioBook(initial_capital)
        self._strategies: Dict[str, EventStrategy] = {}

    # 生命周期
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def pause(self) -> None: ...

    # 策略管理
    def deploy_strategy(self, strategy_id: str, strategy: EventStrategy,
                        symbols: List[str]) -> None: ...
    def undeploy_strategy(self, strategy_id: str) -> bool: ...

    # 核心数据流
    def on_bar(self, bar: Bar) -> None:
        """行情驱动入口（三模式统一）。"""
        # 1. 更新价格
        self._update_prices(bar)
        # 2. 构造上下文
        ctx = self._build_context(bar)
        # 3. 遍历策略：on_exit + on_bar
        for sid, strategy in self._strategies.items():
            exit_orders = strategy.on_exit(ctx)
            entry_orders = strategy.on_bar(bar, ctx)
            # 4. 提交订单
            for intent in exit_orders + entry_orders:
                self._submit_intent(sid, intent)
        # 5. 模式特定后处理

    def _submit_intent(self, strategy_id: str, intent: OrderIntent) -> Optional[OMSOrder]:
        """将OrderIntent转为OMSOrder并提交Broker。"""
        # OMS创建 → Broker提交 → apply_fill → PositionBook/PortfolioBook
        ...

    # 查询
    def get_account(self) -> Dict: ...
    def get_positions(self) -> List[Dict]: ...
    def get_orders(self, active_only=False) -> List[Dict]: ...
    def get_status(self) -> Dict: ...
```

## 9. 实施分阶段计划

### 阶段1：清理废弃代码 + 搭建 trading_core 骨架
- 删除刚实现的 paper_trading/、strategy/、data/、database.py、cli/、main.py改造
- 创建 trading_core/ 目录结构
- 实现 interfaces.py（EventStrategy / OrderIntent / TradingContext / Bar）
- 实现 core.py（TradingCore 主类，整合现有 Runtime 组件）
- 验证：导入成功，可实例化

### 阶段2：实现 BacktestMode（验证统一引擎）
- 实现 modes/backtest.py（从历史数据逐bar推送）
- 实现 SignalStrategyAdapter（将现有 SignalStrategy 接入）
- 用现有 Alpha014 策略跑通回测，验证统一引擎正确性
- 单元测试

### 阶段3：实现 PaperMode（模拟交易）
- 实现 modes/paper.py（实时行情 + PaperBroker）
- 修复 UpgradedPaperBroker 的 SlippageModel Bug
- 持久化层（复用5张paper_*表，由PortfolioBook写入）
- CLI 重新设计
- 单元测试

### 阶段4：LiveMode 骨架 + 后续扩展
- LiveMode 骨架（RealBroker 抽象，BinanceBroker 占位）
- 后续扩展：Performance Analyzer / Recorder / Report / Session / Feedback

## 10. 验收标准

- [ ] 废弃代码已清理（paper_trading/、strategy/、data/、database.py、cli/）
- [ ] trading_core/ 目录结构完整
- [ ] EventStrategy 接口定义清晰（on_bar/on_exit/on_init）
- [ ] TradingCore 主类可实例化（整合 OMS/Broker/PositionBook/PortfolioBook）
- [ ] BacktestMode 可用历史数据逐bar驱动策略
- [ ] SignalStrategyAdapter 可将现有 SignalStrategy 接入统一引擎
- [ ] PaperMode 可用 PaperBroker 模拟成交
- [ ] 三模式共享同一套 OMS/PositionBook/PortfolioBook
- [ ] UpgradedPaperBroker 的 SlippageModel Bug 已修复
- [ ] CLI 支持 `python main.py trading --mode backtest/paper/live`
- [ ] 单元测试全部通过

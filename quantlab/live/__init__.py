"""
V3.1 Live 包 —— 回测/Paper/Live 统一交易系统

新目录结构：
  live/
    execution/    统一 Execution（Backtest/Paper/Live 三模式）
    broker/       Broker 统一接口 + Paper/IBKR/Binance
    risk/         RiskManager + Checks + KillSwitch
    market_data.py / order_manager.py / live_engine.py / logger.py  保持兼容

旧路径 兼容：
    from quantlab.live.broker import BrokerAdapter          → re-export
    from quantlab.live.paper_trading import PaperBroker      → re-export
    from quantlab.live.live_engine import LiveEngine         → 仍然在旧文件
    from quantlab.risk import RiskManager                    → re-export
"""

# ---- 新结构：V3.1 子包 ----
from .execution import (
    BaseExecution,
    BacktestExecution,
    PaperExecution,
    LiveExecution,
    ExecutionFactory,
)
from .broker import (
    AccountState,
    BrokerAdapter,
    PaperBroker,
    IBKRBroker,
    BinanceBroker,
)
from .risk import (
    RiskManager,
    RiskCheck,
    PositionLimitCheck,
    OrderSizeCheck,
    DailyLossCheck,
    LeverageCheck,
    MaxPositionLimit,
    MaxDailyLoss,
    MaxLeverage,
    MaxOrderSize,
    EmergencyStop,
    KillSwitch,
)

# ---- 兼容旧导出 ----
from .market_data import (
    MarketDataAdapter,
)
from .order_manager import (
    ManagedOrder,
    OrderManager,
    OrderState,
)
from .replay_market_data import (
    ReplayMarketData,
)
from .live_engine import (
    LiveEngine,
)
from .logger import (
    LiveLogger,
)

# V3.2：把 monitoring 整体可从 live 包访问
from ..monitoring import (  # noqa: E402
    TradeLogger,
    MetricsCollector,
    EventTracer,
    AlertManager,
    Dashboard,
    SystemContext,
)


__all__ = [
    # V3.1 新结构
    "BaseExecution",
    "BacktestExecution",
    "PaperExecution",
    "LiveExecution",
    "ExecutionFactory",
    "AccountState",
    "BrokerAdapter",
    "PaperBroker",
    "IBKRBroker",
    "BinanceBroker",
    "RiskManager",
    "RiskCheck",
    "PositionLimitCheck",
    "OrderSizeCheck",
    "DailyLossCheck",
    "LeverageCheck",
    "MaxPositionLimit",
    "MaxDailyLoss",
    "MaxLeverage",
    "MaxOrderSize",
    "EmergencyStop",
    "KillSwitch",
    # 旧兼容
    "MarketDataAdapter",
    "ManagedOrder",
    "OrderManager",
    "OrderState",
    "ReplayMarketData",
    "LiveEngine",
    "LiveLogger",
]

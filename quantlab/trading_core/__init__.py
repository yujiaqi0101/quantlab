"""
Trading Core — 统一交易核心
=========================

Backtest/Paper/Live 三模式共享同一套引擎：
    - 同一套 Strategy Engine（EventStrategy 事件驱动接口）
    - 同一套 OMS（OMSOrder 状态机）
    - 同一套 Portfolio Engine（PositionBook + PortfolioBook）
    - 唯一变化：数据来源（DataFeed）和 Broker 类型（由 TradingMode 决定）

快速开始：
    from quantlab.trading_core import TradingCore, EventStrategy, OrderIntent
    from quantlab.trading_core.modes import BacktestMode

    mode = BacktestMode()
    core = TradingCore(mode, initial_capital=1_000_000)
    core.deploy_strategy("my_strategy", my_strategy, symbols=["BTCUSDT"])
    core.on_bar(bar)
"""
from __future__ import annotations

from .core import TradingCore
from .interfaces import (
    Bar,
    EventStrategy,
    OrderIntent,
    Position,
    TradingContext,
)
from .persistence import TradingPersistence, get_trading_persistence
from .replay import ReplayEngine

__all__ = [
    "TradingCore",
    "EventStrategy",
    "OrderIntent",
    "TradingContext",
    "Bar",
    "Position",
    "TradingPersistence",
    "get_trading_persistence",
    "ReplayEngine",
]

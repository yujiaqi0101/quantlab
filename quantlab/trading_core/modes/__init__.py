"""
交易模式 (modes)
===============

三模式共享同一套 TradingCore 引擎，唯一变化是数据来源和 Broker 类型：
    - BacktestMode   历史数据驱动 + PaperBroker(即时撮合)
    - PaperMode      实时行情 + PaperBroker(模拟撮合)
    - LiveMode       实时行情 + 真实券商(占位)

用法：
    from quantlab.trading_core.modes import BacktestMode
    mode = BacktestMode()
    core = TradingCore(mode, initial_capital=1_000_000)
"""
from __future__ import annotations

from .base import TradingMode
from .backtest import BacktestMode
from .paper import PaperMode
from .live import LiveMode

__all__ = [
    "TradingMode",
    "BacktestMode",
    "PaperMode",
    "LiveMode",
]

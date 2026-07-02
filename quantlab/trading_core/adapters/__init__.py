"""
适配器 (adapters)
================

将现有的策略抽象桥接到统一 TradingCore：
    - SignalStrategyAdapter  将 SignalStrategy(信号面板) 适配为 EventStrategy(事件驱动)

用法：
    from quantlab.trading_core.adapters import SignalStrategyAdapter
"""
from __future__ import annotations

from .signal_adapter import SignalStrategyAdapter

__all__ = ["SignalStrategyAdapter"]

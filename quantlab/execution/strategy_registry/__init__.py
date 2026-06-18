"""
Strategy Registry — 本地策略目录

T1 第九模块：本地策略目录（非企业版 Registry）

  RSI Strategy
  Momentum Strategy
  LGBM Strategy

前端 "Strategy Library" 页面数据来源

用法：
    from quantlab.execution.strategy_registry import StrategyRegistry, get_registry

    reg = get_registry()
    strategies = reg.list_strategies()
    info = reg.get_strategy("rsi")
"""

from .registry import (
    StrategyInfo,
    StrategyParameter,
    StrategyRegistry,
    get_registry,
    register_builtin,
)
from .builtin import register_all_builtin

__all__ = [
    "StrategyInfo",
    "StrategyParameter",
    "StrategyRegistry",
    "get_registry",
    "register_builtin",
    "register_all_builtin",
]

"""
QuantLab V2.0 — Plugin System

核心思想：新增因子/信号/策略，不改主代码，只需 @register_xxx

用法：
    from quantlab.plugins import register_factor, register_signal, register_strategy

    @register_factor
    class MyFactor(Factor):
        name = "my_factor"
        ...

    @register_signal
    class MySignal(Signal):
        name = "my_signal"
        ...

    @register_strategy
    class MyStrategy(BaseStrategy):
        strategy_id = "my_strategy"
        ...

第三方插件：
    # plugins/my_plugin.py
    from quantlab.plugins import register_factor

    @register_factor
    class ThirdPartyFactor(Factor):
        ...

    # main.py
    from quantlab.plugins import load_plugins
    load_plugins("plugins.my_plugin")
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger("quantlab.plugins")


# ============================================================
# Global Registries — 延迟初始化
# ============================================================

_factor_registry = None
_signal_engine = None
_strategy_registry = None


def _get_factor_registry():
    global _factor_registry
    if _factor_registry is None:
        from ..factor.registry import FactorRegistry
        _factor_registry = FactorRegistry()
    return _factor_registry


def _get_signal_engine():
    global _signal_engine
    if _signal_engine is None:
        from ..signal.signal_engine import SignalEngine
        _signal_engine = SignalEngine()
    return _signal_engine


def _get_strategy_registry():
    global _strategy_registry
    if _strategy_registry is None:
        from ..strategy.registry import get_strategy_registry
        _strategy_registry = get_strategy_registry()
    return _strategy_registry


# ============================================================
# Decorators — @register_factor / @register_signal / @register_strategy
# ============================================================

def register_factor(cls: Type) -> Type:
    """
    注册因子装饰器

    用法：
        @register_factor
        class RSIFactor(Factor):
            name = "RSI14"
            ...
    """
    registry = _get_factor_registry()
    registry.register(cls)
    logger.info(f"[Plugin] Factor registered: {cls.__name__}")
    return cls


def register_signal(cls: Type) -> Type:
    """
    注册信号装饰器

    用法：
        @register_signal
        class RSIOversoldSignal(Signal):
            name = "rsi_oversold"
            ...
    """
    engine = _get_signal_engine()
    instance = cls()
    engine.register(instance)
    logger.info(f"[Plugin] Signal registered: {cls.__name__}")
    return cls


def register_strategy(cls: Type) -> Type:
    """
    注册策略装饰器

    用法：
        @register_strategy
        class MACrossStrategy(BaseStrategy):
            strategy_id = "ma_cross"
            ...
    """
    registry = _get_strategy_registry()
    registry.register(cls)
    logger.info(f"[Plugin] Strategy registered: {cls.__name__}")
    return cls


# ============================================================
# Plugin Loader — 自动发现和加载
# ============================================================

_loaded_plugins: List[str] = []


def load_plugins(*module_paths: str) -> List[str]:
    """
    加载插件模块

    用法：
        load_plugins("plugins.my_plugin", "plugins.another_plugin")

    或者：
        load_plugins("plugins")  # 加载整个包
    """
    loaded = []
    for path in module_paths:
        try:
            module = importlib.import_module(path)
            loaded.append(path)
            _loaded_plugins.append(path)
            logger.info(f"[Plugin] Loaded: {path}")
        except ImportError as e:
            logger.error(f"[Plugin] Failed to load {path}: {e}")
    return loaded


def list_plugins() -> List[str]:
    """列出已加载的插件"""
    return list(_loaded_plugins)


def plugin_info() -> Dict[str, Any]:
    """获取插件系统信息"""
    return {
        "loaded_plugins": list(_loaded_plugins),
        "registered_factors": _get_factor_registry().list() if _factor_registry else [],
        "registered_signals": _get_signal_engine().list_signals() if _signal_engine else [],
        "registered_strategies": [],
    }

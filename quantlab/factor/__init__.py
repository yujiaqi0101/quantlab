"""
QuantLab 因子系统
================

提供统一的因子注册、查询、计算服务，供前端 Factor Studio 使用。

模块结构:
    base.py      - FactorInfo / FactorFn 类型定义
    registry.py  - FactorRegistry 单例注册表
    technical.py - 内置技术指标因子（MA / RSI / MACD / BOLL 等）
    cache.py     - 因子值计算缓存

使用:
    from quantlab.factor import get_registry
    reg = get_registry()
    info = reg.get('alpha_001')
    factor_df = info.compute(ctx)  # ctx: FactorContext
"""
from __future__ import annotations

from .registry import FactorRegistry, get_registry
from .base import FactorInfo

__all__ = [
    "FactorRegistry",
    "FactorInfo",
    "get_registry",
]


def _register_all() -> None:
    """启动时自动注册所有内置因子（Alpha191 / Alpha101 / 技术因子）"""
    from . import technical as _technical  # noqa: F401
    from . import alpha_auto as _alpha_auto  # noqa: F401


_register_all()

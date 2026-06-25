"""
Alpha191 #186 — 复杂多窗口量价结构
========================================

公式:
    MEAN((CLOSE - OPEN)^2, 20)

公式解释:
    计算 (CLOSE - OPEN) 的平方
    进行20日均值平滑

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/CLOSE（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    日内价格波动的20日均值。

适用场景:
    波动率策略。

变种与优化:
    - 调整窗口 20
    - 替换为标准差

注意事项:
    - 前 19 期返回 NaN (ts_mean 20)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_186"]

DIRECTION = 1


def alpha_186(ctx: FactorContext, period: int = 20) -> pd.DataFrame:
    """Alpha191 #186: 复杂多窗口量价结构。

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 20)

    Returns:
        因子面板 (date × symbol)
    """
    diff_sq = (ctx.close - ctx.open) ** 2
    return ts_mean(diff_sq, period)

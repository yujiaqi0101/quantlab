"""
Alpha191 #34 — 12日均值与现价比
========================================

公式:
    MEAN(CLOSE, 12) / CLOSE

公式解释:
    计算12日收盘价均值与当前收盘价的比值。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    当该比值大于1时，说明当前价格低于近期均值（超卖）；
    小于1时说明当前价格高于近期均值（超买）。
    反向选择意味着偏好比值大的股票（超卖反弹）。

适用场景:
    均值回复策略。

变种与优化:
    - 可调整窗口期 (12 → 6/24)
    - 使用不同的均值计算方式
    - 与 Alpha31 等价变换

注意事项:
    - 与 Alpha31 本质相同，只是表现形式不同
    - 前 11 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_034"]

DIRECTION = -1
DEFAULT_PERIOD = 12


def alpha_034(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #34: 12日均值与现价比。

    公式: MEAN(CLOSE, period) / CLOSE

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 12)

    Returns:
        均值比因子面板 (date × symbol)
    """
    return ts_mean(ctx.close, period) / ctx.close

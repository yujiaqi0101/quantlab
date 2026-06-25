"""
Alpha191 #71 — 24日均值偏离百分比
========================================

公式:
    (CLOSE - MA24) / MA24 * 100

公式解释:
    计算收盘价偏离24日均线百分比。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    与 Alpha31/66 类似但使用24日窗口期。更长的窗口期反映中期均值
    回复机会。

适用场景:
    中期均值回复策略。

变种与优化:
    - 可调整窗口期 (24 → 12/60)
    - 使用不同的均线类型
    - 结合趋势判断

注意事项:
    - 24日窗口期在月频调仓中较为常用
    - 前 23 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_071"]

DIRECTION = -1
DEFAULT_PERIOD = 24


def alpha_071(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #71: 24日均值偏离百分比。

    公式: (CLOSE - MEAN(CLOSE, period)) / MEAN(CLOSE, period) * 100

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 24)

    Returns:
        均值偏离因子面板 (date × symbol)，单位 %
    """
    ma = ts_mean(ctx.close, period)
    return (ctx.close - ma) / ma * 100.0

"""
Alpha191 #31 — 12日均值偏离百分比
========================================

公式:
    (CLOSE - MEAN(CLOSE, 12)) / MEAN(CLOSE, 12) * 100

公式解释:
    计算收盘价偏离12日均值的百分比。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好价格低于均值的标的）

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    标准的均值回复因子，衡量当前价格偏离近期均值的程度。
    反向意味着偏好价格低于均值的股票（超卖反弹逻辑）。

适用场景:
    均值回复策略。

变种与优化:
    - 可调整窗口期 (12 → 6/24)
    - 使用不同的均值计算方式 (中位数、VWAP)
    - 结合波动率标准化

注意事项:
    - 简单均值回复因子在趋势市中表现不佳
    - 需结合趋势判断
    - 前 11 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_031"]

DIRECTION = -1
DEFAULT_PERIOD = 12


def alpha_031(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #31: 12日均值偏离百分比。

    公式: (CLOSE - MEAN(CLOSE, period)) / MEAN(CLOSE, period) * 100

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 12)

    Returns:
        均值偏离因子面板 (date × symbol)，单位 %
    """
    ma = ts_mean(ctx.close, period)
    return (ctx.close - ma) / ma * 100.0

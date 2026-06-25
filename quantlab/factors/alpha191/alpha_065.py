"""
Alpha191 #65 — 6日均值与现价比
========================================

公式:
    MEAN(CLOSE, 6) / CLOSE

公式解释:
    计算6日收盘价均值与当前收盘价的比值。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    与 Alpha34 类似但使用更短的窗口期。比值大于1表示当前价格低于短期
    均值（超卖），反向选择偏好超卖股票。

适用场景:
    短期均值回复策略。

变种与优化:
    - 可调整窗口期 (6 → 3/12)
    - 使用不同的均值计算方式
    - 结合成交量确认

注意事项:
    - 短期均值回复因子噪声较大
    - 前 5 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_065"]

DIRECTION = -1
DEFAULT_PERIOD = 6


def alpha_065(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #65: 6日均值与现价比。

    公式: MEAN(CLOSE, period) / CLOSE

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 6)

    Returns:
        均值比因子面板 (date × symbol)
    """
    return ts_mean(ctx.close, period) / ctx.close

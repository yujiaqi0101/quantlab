"""
Alpha191 #114 — 复杂排名比率
========================================

公式:
    RANK(DELAY((HIGH-LOW)/(SUM(CLOSE,5)/5), 2)) * RANK(RANK(VOLUME))
    / (((HIGH-LOW)/(SUM(CLOSE,5)/5)) / (VWAP-CLOSE))

公式解释:
    分子: 振幅均值的2日延迟截面排名 × 成交量双重截面排名
    分母: 当日振幅均值与(VWAP-CLOSE)的比值

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW/CLOSE/VOLUME/VWAP（日频，后复权）

算子依赖:
    - rank
    - delay
    - ts_sum

背后逻辑:
    通过振幅与价格位置的比率衡量量价结构。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 (5 → 10)
    - 用绝对值替代排名

注意事项:
    - 分母为 0 时返回 NaN
    - 前 6 期返回 NaN (ts_sum 5 + delay 2)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_114"]

DIRECTION = 1


def alpha_114(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #114: 复杂排名比率。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    close = ctx.close
    vol = ctx.volume
    vwap = ctx.get_vwap()

    amplitude = (high - low) / (ts_sum(close, 5) / 5.0)
    numerator = rank(delay(amplitude, 2)) * rank(rank(vol))
    denominator = amplitude / (vwap - close)

    safe_denom = denominator.where(denominator.abs() > 0, np.nan)
    return numerator / safe_denom

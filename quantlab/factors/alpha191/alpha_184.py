"""
Alpha191 #184 — 排名相关性与排名差比率
========================================

公式:
    RANK(CORR(SUM(((CLOSE*0.35) + (OPEN*0.65)), 20), SUM(MEAN(VOL,20), 20), 5))
    / RANK(CLOSE + OPEN + HIGH + LOW)

公式解释:
    分子: 0.35*收盘+0.65*开盘 的20日和 与 20日均量20日和 的5日相关性排名
    分母: 当日OHLC之和的排名
    结果: 分子 / 分母

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW/CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - ts_mean
    - ts_sum
    - corr

背后逻辑:
    量价相关性与价格绝对水平的排名比率。

适用场景:
    量价综合选股。

变种与优化:
    - 调整权重 0.35/0.65
    - 调整窗口 20/5

注意事项:
    - 分母为 0 时返回 NaN
    - 前 44 期返回 NaN (ts_mean 20 + ts_sum 20 + corr 5)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean, ts_sum

__all__ = ["alpha_184"]

DIRECTION = 1


def alpha_184(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #184: 排名相关性与排名差比率。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low
    close = ctx.close
    vol = ctx.volume

    hybrid = close * 0.35 + open_ * 0.65
    numerator = rank(corr(ts_sum(hybrid, 20), ts_sum(ts_mean(vol, 20), 20), 5))
    denominator = rank(close + open_ + high + low)

    safe_denom = denominator.where(denominator.abs() > 0, np.nan)
    return numerator / safe_denom

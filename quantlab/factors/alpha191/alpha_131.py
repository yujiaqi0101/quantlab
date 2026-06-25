"""
Alpha191 #131 — 收盘价/成交量时序排名与相关性
========================================

公式:
    RANK(DECAYLINEAR(CORR(DELAY(CLOSE,5), MEAN(VOL,40), 10), 10)) +
    RANK(DECAYLINEAR(CORR(RANK(CLOSE^5), RANK((OPEN^5) + (CLOSE^5)), 10), 10)) +
    RANK(DECAYLINEAR(CORR(RANK(CLOSE^5), RANK((OPEN^5) + (HIGH^5)), 10), 10))

公式解释:
    三项相加:
    1) 延迟5日收盘价 与 40日均量的10日相关性的10日衰减平均排名
    2) 收盘5次幂排名 与 (开盘5次幂+收盘5次幂)排名 的10日相关性的10日衰减平均排名
    3) 收盘5次幂排名 与 (开盘5次幂+最高5次幂)排名 的10日相关性的10日衰减平均排名

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delay
    - ts_mean
    - corr
    - signed_power

背后逻辑:
    多层量价相关性衰减平均排名的累积。

适用场景:
    量价综合选股。

变种与优化:
    - 调整权重5
    - 调整窗口参数

注意事项:
    - 前 54 期返回 NaN (ts_mean 40 + corr 10 + decay 10)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_mean

__all__ = ["alpha_131"]

DIRECTION = 1


def alpha_131(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #131: 收盘价/成交量时序排名与相关性。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    close = ctx.close
    vol = ctx.volume

    c5 = signed_power(close, 5)
    o5 = signed_power(open_, 5)
    h5 = signed_power(high, 5)

    term1 = rank(decay_linear(corr(delay(close, 5), ts_mean(vol, 40), 10), 10))
    term2 = rank(decay_linear(corr(rank(c5), rank(o5 + c5), 10), 10))
    term3 = rank(decay_linear(corr(rank(c5), rank(o5 + h5), 10), 10))

    return term1 + term2 + term3

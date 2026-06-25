"""
Alpha191 #35 — 开盘变化与量价相关复合反转
========================================

公式:
    MIN(RANK(DECAYLINEAR(DELTA(OPEN,1),15)),
        RANK(DECAYLINEAR(CORR(VOLUME,OPEN,17),7))) * -1

公式解释:
    分别计算开盘价1日变化的15日线性衰减移动平均的截面排名，
    以及成交量与开盘价17日相关系数的7日衰减平均的截面排名，
    取两者最小值后取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delta
    - corr
    - decay_linear (线性衰减移动平均)
    - rank (截面)
    - numpy.minimum

背后逻辑:
    该因子综合了开盘价变化趋势和量价相关性两个维度。取最小值意味着两个
    信号中至少有一个发出看空信号时才触发，取负值反转后偏好两个信号都较弱
    的股票。

适用场景:
    量价综合反转策略。

变种与优化:
    - 可调整各窗口期 (1/15/17/7)
    - 使用 MAX 替代 MIN
    - 调整衰减参数

注意事项:
    - MIN 操作可能导致信号过于保守
    - 需关注两个子信号的相关性
    - 前 18 期数据不足时返回 NaN (17日相关)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_035"]

DIRECTION = -1
DEFAULT_DELTA_PERIOD = 1
DEFAULT_DECAY_OPEN = 15
DEFAULT_CORR_PERIOD = 17
DEFAULT_DECAY_CORR = 7


def alpha_035(
    ctx: FactorContext,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    decay_open: int = DEFAULT_DECAY_OPEN,
    corr_period: int = DEFAULT_CORR_PERIOD,
    decay_corr: int = DEFAULT_DECAY_CORR,
) -> pd.DataFrame:
    """Alpha191 #35: 开盘变化与量价相关复合反转。

    公式: -1 * MIN(RANK(DECAYLINEAR(DELTA(OPEN,delta_period),decay_open)),
                   RANK(DECAYLINEAR(CORR(VOLUME,OPEN,corr_period),decay_corr)))

    Args:
        ctx: 因子数据上下文
        delta_period: 开盘变化窗口期 (默认 1)
        decay_open: 开盘变化衰减窗口期 (默认 15)
        corr_period: 量价相关窗口期 (默认 17)
        decay_corr: 相关衰减窗口期 (默认 7)

    Returns:
        复合反转因子面板 (date × symbol)
    """
    open_change = delta(ctx.open, delta_period)
    decayed_change = decay_linear(open_change, decay_open)
    vp_corr = corr(ctx.volume, ctx.open, corr_period)
    decayed_corr = decay_linear(vp_corr, decay_corr)
    return -1.0 * np.minimum(rank(decayed_change), rank(decayed_corr))

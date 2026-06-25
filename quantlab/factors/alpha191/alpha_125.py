"""
Alpha191 #125 — 20日 RSI 动量
========================================

公式:
    -1 * RANK(DECAYLINEAR(CORR((VWAP - MEAN(VOL,20)), MEAN(VOL,20), 20), 20))
    / RANK((OPEN^5) + ((CLOSE^5) + (OPEN^5)))

公式解释:
    分子: VWAP 与 20日均量的差 与 20日均量 的20日相关性的20日衰减线性平均排名，取负
    分母: 开盘5次幂 + 收盘5次幂 + 开盘5次幂的排名

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好 (公式原本有 -1)

数据来源与频率:
    - OPEN/CLOSE/VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_mean
    - corr
    - signed_power

背后逻辑:
    VWAP-量相关性的衰减平均 与 价格5次幂的比率。

适用场景:
    短期动量选股。

变种与优化:
    - 调整RSI窗口
    - 调整衰减窗口

注意事项:
    - 分母为 0 时返回 NaN
    - 前 39 期返回 NaN (ts_mean 20 + corr 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_125"]

DIRECTION = 1


def alpha_125(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #125: 20日 RSI 动量。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    close = ctx.close
    vol = ctx.volume
    vwap = ctx.get_vwap()

    mean_vol_20 = ts_mean(vol, 20)
    corr_val = corr(vwap - mean_vol_20, mean_vol_20, 20)
    numerator = -1.0 * rank(decay_linear(corr_val, 20))

    o5 = signed_power(open_, 5)
    c5 = signed_power(close, 5)
    denominator = rank(o5 + c5 + o5)

    safe_denom = denominator.where(denominator.abs() > 0, np.nan)
    return numerator / safe_denom

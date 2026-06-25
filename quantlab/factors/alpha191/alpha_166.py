"""
Alpha191 #166 — 多重SMA与均量比率
========================================

公式:
    -1 * RANK(DECAYLINEAR(CORR(VWAP, MEAN(VOL,5), 5), 6))

公式解释:
    VWAP 与 5日均量 的5日相关性的6日衰减线性平均排名，取负

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_mean
    - corr

背后逻辑:
    通过短期量价相关性反向排名。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 5/6
    - 替换为 ts_rank

注意事项:
    - 前 10 期返回 NaN (ts_mean 5 + corr 5)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_166"]

DIRECTION = -1


def alpha_166(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #166: 多重SMA与均量比率。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    vol = ctx.volume

    corr_val = corr(vwap, ts_mean(vol, 5), 5)
    return -1.0 * rank(decay_linear(corr_val, 6))

"""
Alpha191 #167 — 多重SMA与均量比率(20日)
========================================

公式:
    -1 * RANK(DECAYLINEAR(CORR(VWAP, MEAN(VOL,20), 6), 16))

公式解释:
    VWAP 与 20日均量 的6日相关性的16日衰减线性平均排名，取负

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
    通过中长期量价相关性反向排名。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 20/6/16
    - 替换为 ts_rank

注意事项:
    - 前 41 期返回 NaN (ts_mean 20 + corr 6 + decay 16)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_167"]

DIRECTION = -1


def alpha_167(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #167: 多重SMA与均量比率(20日)。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    vol = ctx.volume

    corr_val = corr(vwap, ts_mean(vol, 20), 6)
    return -1.0 * rank(decay_linear(corr_val, 16))

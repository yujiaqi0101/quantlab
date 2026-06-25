"""
Alpha191 #157 — 复杂多窗口量价结构
========================================

公式:
    -1 * RANK(DECAYLINEAR(CORR(MEAN(CLOSE,30), MEAN(VOL,30),7),10))

公式解释:
    30日均值收盘价 与 30日均量7日相关性的10日衰减线性平均排名，取负

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_mean
    - corr

背后逻辑:
    通过30日量价相关性衰减平均反向排名。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 30/7/10
    - 替换为 SMA 平滑

注意事项:
    - 前 46 期返回 NaN (ts_mean 30 + corr 7 + decay 10)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_157"]

DIRECTION = -1


def alpha_157(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #157: 复杂多窗口量价结构。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume

    corr_val = corr(ts_mean(close, 30), ts_mean(vol, 30), 7)
    return -1.0 * rank(decay_linear(corr_val, 10))

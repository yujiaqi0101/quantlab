"""
Alpha191 #154 — VWAP与成交量的时序排名相关性
========================================

公式:
    -1 * RANK(DECAYLINEAR(CORR(RANK(DELAY(OPEN,1)), RANK(MEAN(VOL,20)), 10), 10))

公式解释:
    内层: 前一日开盘价排名 与 20日均量排名 的10日相关性
    外层: 相关性的10日衰减线性平均排名，取负

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - OPEN/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delay
    - ts_mean
    - corr

背后逻辑:
    通过开盘-量相关性的衰减平均反向排名。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 10/20
    - 替换为 ts_rank

注意事项:
    - 前 30 期返回 NaN (ts_mean 20 + corr 10)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_mean

__all__ = ["alpha_154"]

DIRECTION = -1


def alpha_154(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #154: VWAP与成交量的时序排名相关性。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    vol = ctx.volume

    corr_val = corr(rank(delay(open_, 1)), rank(ts_mean(vol, 20)), 10)
    return -1.0 * rank(decay_linear(corr_val, 10))

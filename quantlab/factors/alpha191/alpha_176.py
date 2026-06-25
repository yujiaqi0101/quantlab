"""
Alpha191 #176 — 12日时序排名差
========================================

公式:
    RANK(DECAYLINEAR(CORR(TSRANK(CLOSE,7), TSRANK(ADV20,7),6),6))

公式解释:
    内层: 7日时序排名收盘价 与 7日时序排名20日均量 的6日相关性
    外层: 相关性的6日衰减线性平均排名

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_rank
    - ts_mean
    - corr

背后逻辑:
    通过时序排名相关性识别量价结构。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 7/6
    - 替换为 ts_min/ts_max

注意事项:
    - 前 32 期返回 NaN (ts_mean 20 + ts_rank 7 + corr 6)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean, ts_rank

__all__ = ["alpha_176"]

DIRECTION = 1


def alpha_176(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #176: 12日时序排名差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume

    adv20 = ts_mean(vol, 20)
    corr_val = corr(ts_rank(close, 7), ts_rank(adv20, 7), 6)
    return rank(decay_linear(corr_val, 6))

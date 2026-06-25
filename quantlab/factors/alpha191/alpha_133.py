"""
Alpha191 #133 — DECAYLINEAR 双层排名差
========================================

公式:
    RANK(DECAYLINEAR(DELTA(LOG(CLOSE),5), 5))
    - RANK(DECAYLINEAR(CORR(TSRANK(CLOSE,5), TSRANK(MEAN(VOL,60),2), 10), 3))

公式解释:
    左侧: 5日对数收盘价差值的5日衰减平均排名
    右侧: (5日时序排名收盘 与 2日时序排名60日均量 的10日相关性)的3日衰减平均排名
    结果: 左 - 右

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delta
    - ts_mean
    - ts_rank
    - corr

背后逻辑:
    价格变化衰减平均 与 量价时序排名相关性的差异。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口参数

注意事项:
    - 前 71 期返回 NaN (ts_mean 60 + ts_rank 2 + corr 10 + decay 3)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_mean, ts_rank

__all__ = ["alpha_133"]

DIRECTION = 1


def alpha_133(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #133: DECAYLINEAR 双层排名差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume

    log_close = np.log(close.where(close > 0, np.nan))

    left = rank(decay_linear(delta(log_close, 5), 5))
    right = rank(decay_linear(corr(ts_rank(close, 5), ts_rank(ts_mean(vol, 60), 2), 10), 3))

    return left - right

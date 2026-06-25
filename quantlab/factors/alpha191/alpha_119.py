"""
Alpha191 #119 — DECAYLINEAR 双层排名差
========================================

公式:
    RANK(DECAYLINEAR(CORR(VWAP, SUM(MEAN(VOL,5), 26), 5), 7))
    - RANK(DECAYLINEAR(TSRANK(MIN(CORR(RANK(OPEN), RANK(MEAN(VOL,15)), 21), 9), 7), 8))

公式解释:
    两个 DECAYLINEAR 排名的差:
    1) VWAP 与 5日均量26日和的5日相关性的7日衰减平均排名
    2) (开盘排名与15日均量排名的21日相关性最小值9日时序排名)的7日衰减平均8日时序排名

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_mean
    - ts_sum
    - ts_min
    - ts_rank
    - corr

背后逻辑:
    通过 VWAP-量相关性 和 开盘-量排名相关性的最小值时序状态对比。

适用场景:
    量价背离选股。

变种与优化:
    - 调整衰减窗口

注意事项:
    - 前 ~50 期返回 NaN (复杂多层预热)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_min, ts_mean, ts_rank, ts_sum

__all__ = ["alpha_119"]

DIRECTION = 1


def alpha_119(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #119: DECAYLINEAR 双层排名差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    vol = ctx.volume
    vwap = ctx.get_vwap()

    # 左: RANK(DECAYLINEAR(CORR(VWAP, SUM(MEAN(VOL,5), 26), 5), 7))
    mean_vol_5 = ts_mean(vol, 5)
    sum_mean_vol_26 = ts_sum(mean_vol_5, 26)
    corr_left = corr(vwap, sum_mean_vol_26, 5)
    left = rank(decay_linear(corr_left, 7))

    # 右: RANK(DECAYLINEAR(TSRANK(MIN(CORR(RANK(OPEN), RANK(MEAN(VOL,15)), 21), 9), 7), 8))
    mean_vol_15 = ts_mean(vol, 15)
    corr_open_vol = corr(rank(open_), rank(mean_vol_15), 21)
    min_corr = ts_min(corr_open_vol, 9)
    ts_rank_min = ts_rank(min_corr, 7)
    decay_right = decay_linear(ts_rank_min, 8)
    right = rank(decay_right)

    return left - right

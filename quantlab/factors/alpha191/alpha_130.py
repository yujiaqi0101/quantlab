"""
Alpha191 #130 — 量价相关性与排名组合
========================================

公式:
    RANK(DECAYLINEAR(CORR(((HIGH*0.6) + (LOW*0.4)), MEAN(VOL,40), 11), 4))
    - RANK(DECAYLINEAR(CORR(RANK(VWAP), RANK(VOL), 7), 13))

公式解释:
    左侧: 0.6*HIGH+0.4*LOW 与 40日均量的11日相关性的4日衰减平均排名
    右侧: VWAP排名与成交量排名的7日相关性的13日衰减平均排名
    结果: 左 - 右

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW/VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_mean
    - corr

背后逻辑:
    通过高低价-量 与 VWAP-量排名相关性的衰减平均差异。

适用场景:
    量价结构选股。

变种与优化:
    - 调整权重 0.6/0.4
    - 调整窗口参数

注意事项:
    - 前 50 期返回 NaN (ts_mean 40 + corr 11)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_130"]

DIRECTION = 1


def alpha_130(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #130: 量价相关性与排名组合。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    vol = ctx.volume
    vwap = ctx.get_vwap()

    left = rank(decay_linear(corr(high * 0.6 + low * 0.4, ts_mean(vol, 40), 11), 4))
    right = rank(decay_linear(corr(rank(vwap), rank(vol), 7), 13))

    return left - right

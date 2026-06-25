"""
Alpha191 #172 — 12日价格差值的累积与排名差
========================================

公式:
    RANK(DECAYLINEAR(DELTA(LOW,2),8)) + RANK(DECAYLINEAR(CORR(VWAP, MEAN(VOL,20),7),3))

公式解释:
    左项: 2日低点差值的8日衰减线性平均排名
    右项: VWAP 与 20日均量7日相关性的3日衰减线性平均排名
    结果: 二者之和

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - LOW/VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delta
    - ts_mean
    - corr

背后逻辑:
    通过低点动量与量价相关性的排名组合。

适用场景:
    量价综合选股。

变种与优化:
    - 调整窗口 2/8, 7/3
    - 替换为减法

注意事项:
    - 前 26 期返回 NaN (ts_mean 20 + corr 7)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_mean

__all__ = ["alpha_172"]

DIRECTION = 1


def alpha_172(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #172: 12日价格差值的累积与排名差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    low = ctx.low
    vol = ctx.volume
    vwap = ctx.get_vwap()

    left = rank(decay_linear(delta(low, 2), 8))
    right = rank(decay_linear(corr(vwap, ts_mean(vol, 20), 7), 3))

    return left + right

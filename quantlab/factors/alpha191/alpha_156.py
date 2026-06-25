"""
Alpha191 #156 — 20日最大量时序排名与反转
========================================

公式:
    MAX(RANK(DECAYLINEAR(CORR(RANK(VWAP), RANK(VOL),5),6)),
        RANK(DECAYLINEAR(DELTA(DELTA(CLOSE,1),1),5)))

公式解释:
    左项: VWAP排名与成交量排名5日相关性的6日衰减平均排名
    右项: 二阶价格差分的5日衰减平均排名
    结果: 取二者较大值

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE/VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delta
    - corr

背后逻辑:
    通过量价相关性与价格二阶动量的最大排名。

适用场景:
    量价综合选股。

变种与优化:
    - 调整窗口 5/6
    - 替换为 min

注意事项:
    - 前 10 期返回 NaN (delay 1 + delta + decay 6)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_156"]

DIRECTION = 1


def alpha_156(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #156: 20日最大量时序排名与反转。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume
    vwap = ctx.get_vwap()

    left = rank(decay_linear(corr(rank(vwap), rank(vol), 5), 6))
    right = rank(decay_linear(delta(delta(close, 1), 1), 5))

    # NaN 保护: 取较大值时避免 NaN < NaN 误判
    mask = left.notna() & right.notna()
    out = np.maximum(left, right)
    return out.where(mask)

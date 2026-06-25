"""
Alpha191 #12 — 开盘VWAP偏离与收盘VWAP偏离复合反转
========================================

公式:
    RANK(OPEN - (SUM(VWAP, 10)/10)) * (-1 * RANK(ABS(CLOSE - VWAP)))

公式解释:
    计算开盘价与10日VWAP均值之差的截面排名，乘以收盘价与VWAP绝对
    偏差的截面排名的负值。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - ts_sum
    - rank (截面)
    - numpy.abs

背后逻辑:
    开盘价偏离VWAP均值衡量开盘时的价格偏离程度，收盘价与VWAP的绝对
    偏差衡量全天价格偏离程度。两者乘积综合反映价格偏离VWAP的程度，
    取负值偏好偏离较小的标的（均值回复逻辑）。

适用场景:
    均值回复策略，偏好价格围绕VWAP波动的标的。

变种与优化:
    - 可调整VWAP均值窗口期 (10 → 5/20)
    - 使用不同的价格基准
    - 加权组合两个偏离项

注意事项:
    - VWAP近似计算(amount/volume)可能引入误差
    - 需关注开盘集合竞价的影响
    - 前 9 期数据不足时返回 NaN (10日均值预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_012"]

DIRECTION = -1
DEFAULT_VWAP_PERIOD = 10


def alpha_012(ctx: FactorContext, vwap_period: int = DEFAULT_VWAP_PERIOD) -> pd.DataFrame:
    """Alpha191 #12: 开盘VWAP偏离与收盘VWAP偏离复合反转。

    公式: RANK(OPEN-MEAN(VWAP,vwap_period)) * (-1*RANK(ABS(CLOSE-VWAP)))

    Args:
        ctx: 因子数据上下文
        vwap_period: VWAP 均值窗口期 (默认 10)

    Returns:
        复合反转因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    vwap_mean = ts_sum(vwap, vwap_period) / vwap_period
    part1 = rank(ctx.open - vwap_mean)
    part2 = rank(np.abs(ctx.close - vwap))
    return part1 * (-1.0 * part2)

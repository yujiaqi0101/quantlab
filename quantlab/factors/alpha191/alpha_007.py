"""
Alpha191 #7 — VWAP偏离极值与量变化复合
========================================

公式:
    (RANK(MAX(VWAP-CLOSE, 3)) + RANK(MIN(VWAP-CLOSE, 3))) * RANK(DELTA(VOLUME, 3))

公式解释:
    分别计算VWAP与收盘价差值的3日最大值和3日最小值的截面排名，
    两者相加后乘以成交量3日变化量的截面排名。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - ts_max
    - ts_min
    - delta
    - rank (截面)

背后逻辑:
    VWAP与收盘价的差值反映日内价格偏离均价的程度。MAX 和 MIN 综合使用
    同时考虑正向和负向偏离的极端情况，再结合成交量变化，形成量价偏离的
    综合信号。

适用场景:
    日内价格偏离后的趋势延续策略。

变种与优化:
    - 可调整窗口期 (3 → 5)
    - 使用不同的价格基准 (TWAP)
    - 加入成交额信息

注意事项:
    - VWAP 近似计算(amount/volume)可能不够精确
    - 前 5 期数据不足时返回 NaN (3日极值 + 3日变化)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_max, ts_min

__all__ = ["alpha_007"]

DIRECTION = 1
DEFAULT_PERIOD = 3


def alpha_007(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #7: VWAP偏离极值与量变化复合。

    公式: (RANK(MAX(VWAP-CLOSE,period)) + RANK(MIN(VWAP-CLOSE,period))) * RANK(DELTA(VOLUME,period))

    Args:
        ctx: 因子数据上下文
        period: 极值与变化窗口期 (默认 3)

    Returns:
        量价复合因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    diff = vwap - ctx.close
    part1 = rank(ts_max(diff, period)) + rank(ts_min(diff, period))
    part2 = rank(delta(ctx.volume, period))
    return part1 * part2

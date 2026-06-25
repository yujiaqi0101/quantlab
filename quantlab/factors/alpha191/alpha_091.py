"""
Alpha191 #91 — 高点回落与量价相关复合反转
========================================

公式:
    -1 * RANK(CLOSE - MAX(CLOSE, 5)) * RANK(CORR(MA(VOLUME,40), LOW, 5))

公式解释:
    计算收盘价与5日最高收盘价之差的截面排名，乘以40日成交量均值与最低价
    5日相关系数的截面排名，取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_max
    - ts_mean
    - corr
    - rank (截面)

背后逻辑:
    第一个子因子衡量价格从高点的回落程度，第二个子因子衡量成交量均值与
    最低价的相关性。两者相乘后取负值偏好价格接近高点且量价配合良好的
    股票。

适用场景:
    量价综合策略。

变种与优化:
    - 可调整各窗口期 (5/40/5)
    - 使用不同的价格基准
    - 加权组合两个子信号

注意事项:
    - 两个子信号的方向需仔细分析
    - 前 39 期数据不足时返回 NaN (40日量均值最长)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_max, ts_mean

__all__ = ["alpha_091"]

DIRECTION = -1
DEFAULT_MAX_PERIOD = 5
DEFAULT_VOL_PERIOD = 40
DEFAULT_CORR_PERIOD = 5


def alpha_091(
    ctx: FactorContext,
    max_period: int = DEFAULT_MAX_PERIOD,
    vol_period: int = DEFAULT_VOL_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #91: 高点回落与量价相关复合反转。

    公式: -1 * RANK(CLOSE - MAX(CLOSE, max_period))
          * RANK(CORR(MA(V, vol_period), LOW, corr_period))

    Args:
        ctx: 因子数据上下文
        max_period: 最高收盘价窗口期 (默认 5)
        vol_period: 成交量均值窗口期 (默认 40)
        corr_period: 相关系数窗口期 (默认 5)

    Returns:
        复合反转因子面板 (date × symbol)
    """
    pullback = ctx.close - ts_max(ctx.close, max_period)
    vol_mean = ts_mean(ctx.volume, vol_period)
    vp_corr = corr(vol_mean, ctx.low, corr_period)
    return -1.0 * rank(pullback) * rank(vp_corr)

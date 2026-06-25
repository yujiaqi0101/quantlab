"""
Alpha191 #45 — 加权收盘动量与长期量价相关复合反转
========================================

公式:
    RANK(DELTA((CLOSE*0.6 + OPEN*0.4), 1)) * RANK(CORR(VWAP, MEAN(VOLUME,150), 15))

公式解释:
    计算加权收盘价（60%收盘+40%开盘）1日变化量的截面排名，乘以VWAP与
    150日成交量均值15日相关系数的截面排名。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - delta
    - ts_mean
    - corr
    - rank (截面)

背后逻辑:
    该因子将短期价格动量与长期量价相关性相结合。取负值意味着偏好价格
    回落或量价相关性弱的股票。

适用场景:
    量价反转策略。

变种与优化:
    - 可调整加权比例 (0.6/0.4)
    - 可调整窗口期 (1/150/15)
    - 使用不同的价格基准

注意事项:
    - 150日的成交量均值需要较长历史数据
    - 两个子信号的相关性需关注
    - 前 15 期数据不足时返回 NaN (15日相关最长)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_mean

__all__ = ["alpha_045"]

DIRECTION = -1
DEFAULT_DELTA_PERIOD = 1
DEFAULT_VOL_PERIOD = 150
DEFAULT_CORR_PERIOD = 15


def alpha_045(
    ctx: FactorContext,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    vol_period: int = DEFAULT_VOL_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #45: 加权收盘动量与长期量价相关复合反转。

    公式: RANK(DELTA((CLOSE*0.6+OPEN*0.4), delta_period))
          * RANK(CORR(VWAP, MEAN(V, vol_period), corr_period))
          * (-1)

    Args:
        ctx: 因子数据上下文
        delta_period: 加权收盘变化窗口期 (默认 1)
        vol_period: 成交量均值窗口期 (默认 150)
        corr_period: 相关系数窗口期 (默认 15)

    Returns:
        复合反转因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    weighted_close = ctx.close * 0.6 + ctx.open * 0.4
    price_change = delta(weighted_close, delta_period)
    vol_mean = ts_mean(ctx.volume, vol_period)
    vp_corr = corr(vwap, vol_mean, corr_period)
    return -1.0 * rank(price_change) * rank(vp_corr)

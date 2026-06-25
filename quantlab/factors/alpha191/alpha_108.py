"""
Alpha191 #108 — 短期突破与长期量价相关幂次复合反转
========================================

公式:
    -1 * RANK(HIGH - MIN(HIGH, 2)) ^ RANK(CORR(VWAP, MA(VOLUME, 120), 6))

公式解释:
    计算最高价与2日最低最高价之差的截面排名的成交量与VWAP相关系数排名
    的幂次，取负值。

分类:
    相关性 (correlation)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - ts_min
    - ts_mean
    - corr
    - rank (截面)
    - numpy.power

背后逻辑:
    该因子将短期价格突破信号与长期量价相关性信号非线性组合。取负值偏好
    突破幅度小或量价相关性弱的股票。

适用场景:
    量价相关性反转策略。

变种与优化:
    - 可调整各窗口期 (2/120/6)
    - 使用不同的非线性组合方式
    - 结合成交额确认

注意事项:
    - 幂次运算可能导致数值不稳定，需处理底数为0且指数为负的inf
    - 120日成交量均值需要较长历史数据
    - 前 5 期数据不足时返回 NaN (6日相关最长，120日均值需长历史但预热计算)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean, ts_min

__all__ = ["alpha_108"]

DIRECTION = -1
DEFAULT_MIN_PERIOD = 2
DEFAULT_VOL_PERIOD = 120
DEFAULT_CORR_PERIOD = 6


def alpha_108(
    ctx: FactorContext,
    min_period: int = DEFAULT_MIN_PERIOD,
    vol_period: int = DEFAULT_VOL_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #108: 短期突破与长期量价相关幂次复合反转。

    公式: -1 * RANK(HIGH - MIN(HIGH, min_period))
          ^ RANK(CORR(VWAP, MA(V, vol_period), corr_period))

    Args:
        ctx: 因子数据上下文
        min_period: 最高价最小值窗口期 (默认 2)
        vol_period: 成交量均值窗口期 (默认 120)
        corr_period: 相关系数窗口期 (默认 6)

    Returns:
        幂次复合反转因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    breakout = ctx.high - ts_min(ctx.high, min_period)
    vol_mean = ts_mean(ctx.volume, vol_period)
    vp_corr = corr(vwap, vol_mean, corr_period)
    base = rank(breakout)
    expo = rank(vp_corr)
    # 注意: np.power(1.0, NaN) = 1.0 (numpy 特性), 需显式 mask
    result = np.power(base, expo)
    result = result.where(expo.notna())
    result = result.replace([np.inf, -np.inf], np.nan)
    return -1.0 * result

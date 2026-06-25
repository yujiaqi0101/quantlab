"""
Alpha101 #2 — 量价相关性
============================

公式:
    -1 * correlation(rank(delta(log(volume), 2)), rank((close - open) / open), 6)

公式解释:
    计算成交量对数 2 日变化的排名与日内涨跌幅 (close-open)/open 排名的 6 日滚动相关系数，取负。

分类:
    量价相关性 (volume_price_correlation)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - CLOSE / OPEN 收盘价 / 开盘价（日频，后复权）

算子依赖:
    - delta (时序差分)
    - rank (截面)
    - corr (滚动相关)

背后逻辑:
    捕捉成交量变化与价格变化之间的反向关系。
    log(volume) 处理使因子对成交量量级不敏感；双重 rank 增强横截面可比性。
    当成交量上升但价格涨幅排名下降时，相关系数为负，取负后因子值为正 (看多)。

适用场景:
    适用于量价背离检测——当成交量变化与价格变化方向不一致时，预示反转机会。

变种与优化:
    - 可调整窗口参数 (2 日、6 日)
    - 可使用其他价格变化指标 (如收盘价差分)

注意事项:
    - log(volume) 处理使因子对成交量量级不敏感
    - 双重 rank 增强横截面可比性
    - 前 7 期因 delta + corr 预热返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_002"]

DIRECTION = -1
DEFAULT_VOL_DELTA = 2
DEFAULT_CORR_PERIOD = 6


def alpha_002(
    ctx: FactorContext,
    vol_delta: int = DEFAULT_VOL_DELTA,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #2: 量价相关性。

    公式: -1 * correlation(rank(delta(log(volume), vol_delta)), rank((close - open) / open), corr_period)

    Args:
        ctx: 因子数据上下文
        vol_delta: 成交量对数差分窗口 (默认 2)
        corr_period: 相关系数窗口 (默认 6)

    Returns:
        量价相关性因子面板 (date × symbol)
    """
    vol = ctx.volume.where(ctx.volume > 0, np.nan)
    vol_chg = delta(np.log(vol), vol_delta)
    price_chg = (ctx.close - ctx.open) / ctx.open
    return -1.0 * corr(rank(vol_chg), rank(price_chg), corr_period)

"""
Alpha191 #1 — 量价变化相关性反转
========================================

公式:
    -1 * CORR(RANK(DELTA(LOG(VOLUME), 1)), RANK((CLOSE-OPEN)/OPEN), 6)

公式解释:
    计算成交量对数变化率的截面排名与当日涨跌幅截面排名的6日相关系数，
    取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay
    - delta
    - rank (截面)
    - corr (滚动相关)
    - numpy.log

背后逻辑:
    当成交量变化与价格变化高度正相关时，说明市场跟风效应明显，
    往往是过热信号。取负值意味着偏好量价背离的股票——即成交量增加
    但价格未同步上涨，或价格上涨但成交量萎缩的标的。

适用场景:
    短期反转策略，在市场情绪过热时寻找潜在反转机会。

变种与优化:
    - 可调整窗口期 (6 → 10/15)
    - 用 TSRANK 替代 RANK
    - 加入成交额替代成交量

注意事项:
    - 停牌期间成交量异常会导致噪声
    - 需对成交量做对数变换处理零值
    - 前 6 期数据不足时返回 NaN (corr 预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, delta

__all__ = ["alpha_001"]

DIRECTION = -1
DEFAULT_CORR_PERIOD = 6


def alpha_001(ctx: FactorContext, corr_period: int = DEFAULT_CORR_PERIOD) -> pd.DataFrame:
    """Alpha191 #1: 量价变化相关性反转。

    公式: -1 * CORR(RANK(DELTA(LOG(VOLUME),1)), RANK((CLOSE-OPEN)/OPEN), corr_period)

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口期 (默认 6)

    Returns:
        量价反转因子面板 (date × symbol)
    """
    log_vol = np.log(ctx.volume.where(ctx.volume > 0, np.nan))
    vol_change = delta(log_vol, 1)
    price_change = (ctx.close - ctx.open) / ctx.open
    return -1.0 * corr(rank(vol_change), rank(price_change), corr_period)

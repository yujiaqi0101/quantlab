"""
Alpha101 #52 — 日内变化-量价相关
====================================

公式:
    ((-1 * delta((close - open), 5)) * rank(correlation(returns, volume, 5))) * sign(delta(close, 5))

公式解释:
    负的 5 日日内涨跌幅变化、收益率与成交量 5 日相关性排名、5 日价格变化方向符号，三者相乘。

分类:
    日内变化-量价相关 (intraday_change_volume_price)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE / OPEN 收盘价 / 开盘价（日频，后复权）
    - RETURNS 日收益率（由 close.pct_change 推导）
    - VOLUME 成交量（日频）

算子依赖:
    - delta (时序差分)
    - rank (截面)
    - corr (滚动相关)
    - sign (符号)

背后逻辑:
    sign 提取方向信息，rank 提供横截面标准化。
    三因子乘积创造交互效应。

适用场景:
    适用于日内变化趋势与量价关系的交互择时。

变种与优化:
    - 可调整窗口参数 (5, 5, 5)
    - 可引入波动率因子

注意事项:
    - 前 10 期因 delta(5) + corr(5) 预热返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_052"]

DIRECTION = -1
DEFAULT_PERIOD = 5


def alpha_052(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #52: 日内变化-量价相关。

    公式: ((-1 * delta((close - open), period)) * rank(correlation(returns, volume, period))) * sign(delta(close, period))

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口 (默认 5)

    Returns:
        日内变化-量价相关因子面板 (date × symbol)
    """
    intraday = ctx.close - ctx.open
    ret = ctx.get_returns()
    intraday_delta = delta(intraday, period)
    corr_term = rank(corr(ret, ctx.volume, period))
    sign_term = np.sign(delta(ctx.close, period))
    return (-1.0 * intraday_delta) * corr_term * sign_term

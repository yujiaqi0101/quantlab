"""
Alpha101 #14 — 收益变化-量价相关
====================================

公式:
    (-1 * rank(delta(returns, 3))) * correlation(open, volume, 10)

公式解释:
    3 日收益率变化的排名取负，乘以开盘价与成交量的 10 日滚动相关系数。

分类:
    收益变化-量价相关 (return_change_volume_price)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - RETURNS 日收益率（由 close.pct_change 推导）
    - OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delta (时序差分)
    - rank (截面)
    - corr (滚动相关)

背后逻辑:
    结合收益动量与量价关系。
    两个因子的乘积创造了交互效应。

适用场景:
    适用于收益率加速变化时的量价确认。

变种与优化:
    - 可调整两个窗口参数 (3, 10)
    - 可加入波动率因子作为第三个维度

注意事项:
    - 前 13 期因 delta(3) + corr(10) 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_014"]

DIRECTION = -1
DEFAULT_RET_DELTA = 3
DEFAULT_CORR_PERIOD = 10


def alpha_014(
    ctx: FactorContext,
    ret_delta: int = DEFAULT_RET_DELTA,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #14: 收益变化-量价相关。

    公式: (-1 * rank(delta(returns, ret_delta))) * correlation(open, volume, corr_period)

    Args:
        ctx: 因子数据上下文
        ret_delta: 收益率差分窗口 (默认 3)
        corr_period: 相关系数窗口 (默认 10)

    Returns:
        收益变化-量价相关因子面板 (date × symbol)
    """
    ret = ctx.get_returns()
    return (-1.0 * rank(delta(ret, ret_delta))) * corr(ctx.open, ctx.volume, corr_period)

"""
Alpha101 #50 — 量价相关极值
==============================

公式:
    -1 * ts_max(rank(correlation(rank(volume), rank(vwap), 5)), 3)

公式解释:
    成交量排名与 VWAP 排名的 5 日相关系数排名，取 3 日最大值再取负。

分类:
    量价相关极值 (volume_price_correlation_extreme)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - VWAP 成交量加权均价（日频）

算子依赖:
    - rank (截面)
    - corr (滚动相关)
    - ts_max (滚动最大值)

背后逻辑:
    捕捉量价相关性的短期极端状态。
    ts_max 捕捉相关性的极端值。

适用场景:
    适用于量价关系极端时的择时。

变种与优化:
    - 可使用 ts_min 或 ts_mean 替代 ts_max
    - 可调整窗口参数 (5, 3)

注意事项:
    - VWAP 缺失时由 amount/volume 近似
    - 前 7 期因 corr(5) + ts_max(3) 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_max

__all__ = ["alpha_050"]

DIRECTION = -1
DEFAULT_CORR_PERIOD = 5
DEFAULT_MAX_PERIOD = 3


def alpha_050(
    ctx: FactorContext,
    corr_period: int = DEFAULT_CORR_PERIOD,
    max_period: int = DEFAULT_MAX_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #50: 量价相关极值。

    公式: -1 * ts_max(rank(correlation(rank(volume), rank(vwap), corr_period)), max_period)

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口 (默认 5)
        max_period: 最大值窗口 (默认 3)

    Returns:
        量价相关极值因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    inner = rank(corr(rank(ctx.volume), rank(vwap), corr_period))
    return -1.0 * ts_max(inner, max_period)

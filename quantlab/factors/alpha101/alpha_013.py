"""
Alpha101 #13 — 量价协方差
=============================

公式:
    -1 * rank(covariance(rank(close), rank(volume), 5))

公式解释:
    收盘价排名与成交量排名的 5 日滚动协方差，截面排名取负。

分类:
    量价协方差 (volume_price_covariance)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - cov (滚动协方差)

背后逻辑:
    与相关性因子类似，但协方差保留了更多幅度信息。
    适用于量价同向/反向运动的检测。

适用场景:
    适用于量价同向/反向运动的检测。

变种与优化:
    - 可替换为 correlation
    - 可调整窗口 (5 → 3/10)

注意事项:
    - 协方差与相关性的区别在于协方差受变量量级影响
    - 前 5 期因 cov 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import cov

__all__ = ["alpha_013"]

DIRECTION = -1
DEFAULT_PERIOD = 5


def alpha_013(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #13: 量价协方差。

    公式: -1 * rank(covariance(rank(close), rank(volume), period))

    Args:
        ctx: 因子数据上下文
        period: 协方差窗口 (默认 5)

    Returns:
        量价协方差因子面板 (date × symbol)
    """
    return -1.0 * rank(cov(rank(ctx.close), rank(ctx.volume), period))

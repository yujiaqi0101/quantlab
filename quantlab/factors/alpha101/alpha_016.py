"""
Alpha101 #16 — 量价协方差
=============================

公式:
    -1 * rank(covariance(rank(high), rank(volume), 5))

公式解释:
    最高价排名与成交量排名的 5 日滚动协方差，截面排名取负。

分类:
    量价协方差 (volume_price_covariance)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - cov (滚动协方差)

背后逻辑:
    与 Alpha#13 类似但使用最高价。
    使用最高价可能更敏感地反映买方力量。

适用场景:
    适用于检测最高价与成交量的同向/反向关系。

变种与优化:
    - 可替换为 close/low/open
    - 可调整窗口 (5 → 3/10)
    - 可结合最低价构建高低价差与成交量的关系

注意事项:
    - 与 Alpha#13 类似但使用最高价
    - 前 5 期因 cov 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import cov

__all__ = ["alpha_016"]

DIRECTION = -1
DEFAULT_PERIOD = 5


def alpha_016(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #16: 量价协方差。

    公式: -1 * rank(covariance(rank(high), rank(volume), period))

    Args:
        ctx: 因子数据上下文
        period: 协方差窗口 (默认 5)

    Returns:
        量价协方差因子面板 (date × symbol)
    """
    return -1.0 * rank(cov(rank(ctx.high), rank(ctx.volume), period))

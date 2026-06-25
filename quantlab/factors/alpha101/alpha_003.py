"""
Alpha101 #3 — 量价相关性
============================

公式:
    -1 * correlation(rank(open), rank(volume), 10)

公式解释:
    开盘价排名与成交量排名的 10 日滚动相关系数取负。

分类:
    量价相关性 (volume_price_correlation)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - corr (滚动相关)

背后逻辑:
    捕捉开盘价与成交量之间的反向关系。
    rank 处理消除了量级差异，使因子更稳健。

适用场景:
    适用于检测开盘价高估/低估与成交量异常的关系。

变种与优化:
    - 可替换为 high/low/vwap 与 volume 的相关性
    - 可调整窗口 (10 → 5/20)

注意事项:
    - 简洁的量价背离因子
    - 前 10 期因 corr 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr

__all__ = ["alpha_003"]

DIRECTION = -1
DEFAULT_PERIOD = 10


def alpha_003(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #3: 量价相关性。

    公式: -1 * correlation(rank(open), rank(volume), period)

    Args:
        ctx: 因子数据上下文
        period: 相关系数窗口 (默认 10)

    Returns:
        量价相关性因子面板 (date × symbol)
    """
    return -1.0 * corr(rank(ctx.open), rank(ctx.volume), period)

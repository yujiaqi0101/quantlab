"""
Alpha101 #4 — 低价时序排名反转
========================================

公式:
    -1 * Ts_Rank(rank(low), 9)

公式解释:
    先对最低价做横截面排名 (rank)，再对排名值做 9 日时序排名 (Ts_Rank)，取负值。

分类:
    价格排名-时序 (price_rank_timeseries)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - LOW 最低价（日频，后复权）

算子依赖:
    - rank (截面)
    - ts_rank (时序)

背后逻辑:
    双重排名 (横截面 + 时序) 是核心特征。低价股在近期排名上升时因子值下降，
    取负值后因子值上升表示看好——即低价股近期排名下降时看多 (短期反转)。
    适用于短期反转策略: 当低价股近期表现相对较好时做空。

适用场景:
    短期反转策略，捕捉低价股排名反转机会。

变种与优化:
    - 可替换为 high/close/open
    - 可调整时序窗口 (9 → 5/20)
    - 可改为时序百分位而非排名

注意事项:
    - 双重排名会放大极端值的影响
    - 前 9 期数据不足返回 NaN (ts_rank 窗口)
    - 截面标的数 < 2 时 rank 退化
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_rank

__all__ = ["alpha_004"]

DIRECTION = -1
DEFAULT_PERIOD = 9


def alpha_004(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #4: 低价时序排名反转。

    公式: -1 * Ts_Rank(rank(low), period)

    Args:
        ctx: 因子数据上下文
        period: 时序排名窗口 (默认 9)

    Returns:
        反向排名因子面板 (date × symbol)
    """
    return -1 * ts_rank(rank(ctx.low), period)

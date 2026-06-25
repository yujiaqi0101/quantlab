"""
Alpha191 #105 — 开盘量价背离
========================================

公式:
    -1 * CORR(RANK(OPEN), RANK(VOLUME), 10)

公式解释:
    计算开盘价截面排名与成交量截面排名的10日相关系数，取负值。

分类:
    相关性 (correlation)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面排名)
    - corr (滚动相关系数)

背后逻辑:
    当开盘价排名与成交量排名正相关时，说明高开伴随放量。取负值偏好这种
    相关性弱的标的，即开盘价与成交量走势背离的股票。

适用场景:
    开盘量价背离策略。

变种与优化:
    - 可调整相关系数窗口期 (10 → 5/20)
    - 使用收盘价/最高价替代开盘价
    - 使用 TSRANK 替代 RANK

注意事项:
    - 开盘价受集合竞价影响较大
    - 截面排名会损失绝对值信息
    - 前 10 期数据不足时返回 NaN (corr 预热)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr

__all__ = ["alpha_105"]

DIRECTION = -1
DEFAULT_PERIOD = 10


def alpha_105(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #105: 开盘量价背离。

    公式: -1 * CORR(RANK(OPEN), RANK(VOLUME), period)

    Args:
        ctx: 因子数据上下文
        period: 相关系数窗口期 (默认 10)

    Returns:
        量价背离因子面板 (date × symbol)
    """
    open_rank = rank(ctx.open)
    vol_rank = rank(ctx.volume)
    return -1.0 * corr(open_rank, vol_rank, period)

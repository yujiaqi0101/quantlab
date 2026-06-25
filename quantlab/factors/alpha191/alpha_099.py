"""
Alpha191 #99 — 收盘价量排名协方差反转
========================================

公式:
    -1 * RANK(COV(RANK(CLOSE), RANK(VOLUME), 5))

公式解释:
    计算收盘价排名与成交量排名5日协方差的截面排名，取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - cov (滚动协方差)

背后逻辑:
    与 Alpha83 类似但使用收盘价替代最高价。衡量收盘价与成交量的协同
    变化，取负值偏好协同性弱的股票。

适用场景:
    量价背离策略。

变种与优化:
    - 可调整窗口期 (5 → 10)
    - 使用相关系数替代协方差
    - 结合成交额确认

注意事项:
    - 与 Alpha83 逻辑类似，仅价格基准不同
    - 前 4 期数据不足时返回 NaN (5日协方差)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import cov

__all__ = ["alpha_099"]

DIRECTION = -1
DEFAULT_PERIOD = 5


def alpha_099(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #99: 收盘价量排名协方差反转。

    公式: -1 * RANK(COV(RANK(CLOSE), RANK(VOLUME), period))

    Args:
        ctx: 因子数据上下文
        period: 协方差窗口期 (默认 5)

    Returns:
        量价背离因子面板 (date × symbol)
    """
    return -1.0 * rank(cov(rank(ctx.close), rank(ctx.volume), period))

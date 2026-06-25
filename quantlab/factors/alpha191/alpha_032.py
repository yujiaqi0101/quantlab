"""
Alpha191 #32 — 高低价量排名相关累积反转
========================================

公式:
    -1 * SUM(RANK(CORR(RANK(HIGH), RANK(VOLUME), 3)), 3)

公式解释:
    计算最高价排名与成交量排名的3日相关系数的截面排名，再求3日和后取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - corr (滚动)
    - ts_sum

背后逻辑:
    该因子衡量最高价与成交量的短期相关性。高相关表示放量创新高，
    取负值偏好这种趋势减弱的股票。

适用场景:
    量价趋势反转策略。

变种与优化:
    - 可调整各窗口期 (3/3)
    - 使用不同的价格基准
    - 结合成交额确认

注意事项:
    - 3日窗口期较短，信号可能不稳定
    - 前 5 期数据不足时返回 NaN (3日相关 + 3日累积)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_032"]

DIRECTION = -1
DEFAULT_CORR_PERIOD = 3
DEFAULT_SUM_PERIOD = 3


def alpha_032(
    ctx: FactorContext,
    corr_period: int = DEFAULT_CORR_PERIOD,
    sum_period: int = DEFAULT_SUM_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #32: 高低价量排名相关累积反转。

    公式: -1 * SUM(RANK(CORR(RANK(HIGH), RANK(VOLUME), corr_period)), sum_period)

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口期 (默认 3)
        sum_period: 累积窗口期 (默认 3)

    Returns:
        量价反转因子面板 (date × symbol)
    """
    high_rank = rank(ctx.high)
    vol_rank = rank(ctx.volume)
    return -1.0 * ts_sum(rank(corr(high_rank, vol_rank, corr_period)), sum_period)

"""
Alpha191 #62 — 最高价与量排名相关性反转
========================================

公式:
    -1 * CORR(HIGH, RANK(VOLUME), 5)

公式解释:
    计算最高价与成交量截面排名的5日相关系数，取负值。

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

背后逻辑:
    当最高价与成交量排名正相关时，说明放量创新高的趋势明显。取负值
    偏好这种趋势减弱的股票。

适用场景:
    量价趋势反转策略。

变种与优化:
    - 可调整窗口期 (5 → 10)
    - 使用不同的价格基准
    - 结合成交额确认

注意事项:
    - RANK 操作会损失绝对值信息
    - 前 4 期数据不足时返回 NaN (5日相关)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr

__all__ = ["alpha_062"]

DIRECTION = -1
DEFAULT_PERIOD = 5


def alpha_062(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #62: 最高价与量排名相关性反转。

    公式: -1 * CORR(HIGH, RANK(VOLUME), period)

    Args:
        ctx: 因子数据上下文
        period: 相关系数窗口期 (默认 5)

    Returns:
        量价反转因子面板 (date × symbol)
    """
    return -1.0 * corr(ctx.high, rank(ctx.volume), period)

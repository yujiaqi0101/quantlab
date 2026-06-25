"""
Alpha101 #10 — 趋势一致性截面排名
========================================

公式:
    rank( (0 < ts_min(delta(close,1), 4)) ? delta(close,1)
        : ((ts_max(delta(close,1), 4) < 0) ? delta(close,1) : (-1 * delta(close,1))) )

公式解释:
    与 Alpha#9 结构相同，但使用 4 日窗口判断趋势一致性，并增加外层截面 rank。

分类:
    趋势一致性 (trend_consistency)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delta
    - ts_min
    - ts_max
    - rank (截面)

背后逻辑:
    与 Alpha#9 相同的趋势一致-反转逻辑，但更短的趋势判断窗口 (4 日) 对短期趋势更敏感。
    外层 rank 增加了横截面可比性，使不同标的的因子值可比较。

适用场景:
    短期趋势跟踪与反转混合策略，强调截面相对强弱。

变种与优化:
    - 窗口参数可调 (4 → 5/10)
    - 可去掉外层 rank 得到 Alpha#9 变种
    - 可结合多个窗口的趋势判断进行投票

注意事项:
    - 外层 rank 增加截面可比性但会改变因子分布
    - 前 5 期数据不足返回 NaN (delta 1 + ts_min/max 4)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_min, ts_max

__all__ = ["alpha_010"]

DIRECTION = 1
DEFAULT_PERIOD = 4


def alpha_010(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #10: 趋势一致性截面排名。

    公式: rank( Alpha#9 逻辑, period=4 )

    Args:
        ctx: 因子数据上下文
        period: 趋势判断窗口 (默认 4)

    Returns:
        趋势一致性截面排名面板 (date × symbol)
    """
    d1 = delta(ctx.close, 1)
    min_d1 = ts_min(d1, period)
    max_d1 = ts_max(d1, period)
    cond_up = min_d1 > 0
    cond_down = max_d1 < 0
    inner = d1.where(cond_up | cond_down, -1 * d1)
    return rank(inner)

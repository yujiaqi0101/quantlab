"""
Alpha191 #139 — 20日最大涨幅的10日衰减线性平均
========================================

公式:
    -1 * RANK(DECAYLINEAR(DELTA(LOW,5), 5))

公式解释:
    对5日低点差值进行5日衰减线性平均，并取截面排名的相反数

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - LOW（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delta

背后逻辑:
    低点变化的衰减平均，反映短期价格动能。

适用场景:
    短期动量反转策略。

变种与优化:
    - 调整窗口 5
    - 替换为高点差值

注意事项:
    - 前 10 期返回 NaN (delay 5 + decay 5)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_139"]

DIRECTION = -1


def alpha_139(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #139: 20日最大涨幅的10日衰减线性平均。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    return -1.0 * rank(decay_linear(delta(ctx.low, 5), 5))

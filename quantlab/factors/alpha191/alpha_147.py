"""
Alpha191 #147 — 12日动量的反转排名
========================================

公式:
    RANK(DECAYLINEAR(DELTA(CLOSE,12), 12)) * -1

公式解释:
    对12日收盘价差值进行12日衰减线性平均
    并取截面排名的相反数

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delta

背后逻辑:
    中期价格变化衰减平均的反向排名。

适用场景:
    中期动量反转策略。

变种与优化:
    - 调整窗口 12
    - 替换为 log 变化

注意事项:
    - 前 23 期返回 NaN (delay 12 + decay 12)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_147"]

DIRECTION = -1


def alpha_147(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #147: 12日动量的反转排名。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    return -1.0 * rank(decay_linear(delta(ctx.close, 12), 12))

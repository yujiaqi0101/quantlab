"""
Alpha191 #136 — RSI动量
========================================

公式:
    -1 * RANK(DELTA(RETURNS,3))

公式解释:
    计算3日收益率差值，并取其截面排名的相反数

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - rank
    - delta

背后逻辑:
    RSI反向排名，反映短期动量反向。

适用场景:
    短期反转策略。

变种与优化:
    - 调整差分窗口 3 → 5
    - 加入SMA平滑

注意事项:
    - 前 3 期返回 NaN (delay 1 + delta 3)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_136"]

DIRECTION = -1


def alpha_136(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #136: RSI动量。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    return -1.0 * rank(delta(returns, 3))

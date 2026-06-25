"""
Alpha191 #179 — 20日平均量与5日差值
========================================

公式:
    (LOW == HIGH) ? 0 : ((CLOSE - LOW) / (HIGH - LOW + 0.001) - 1)

公式解释:
    当 LOW == HIGH 时返回 0
    否则返回 (CLOSE - LOW) / (HIGH - LOW + 0.001) - 1

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW/CLOSE（日频，后复权）

算子依赖:
    无（仅算术运算）

背后逻辑:
    收盘价在当日价格区间中的相对位置 (K线形态)。

适用场景:
    短期均值回复策略。

变种与优化:
    - 调整常数 0.001
    - 替换为 (close-open)/(high-low)

注意事项:
    - 0.001 防止分母为零
    - 首期即可计算
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_179"]

DIRECTION = 1


def alpha_179(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #179: 20日平均量与5日差值。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    close = ctx.close

    numerator = close - low
    denominator = (high - low) + 0.001

    ratio = numerator / denominator - 1.0

    # 当 LOW == HIGH 时返回 0
    cond = (high == low)
    out = ratio.where(~cond, 0.0)
    return out

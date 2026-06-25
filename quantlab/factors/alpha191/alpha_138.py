"""
Alpha191 #138 — SMA2 时序方向判断
========================================

公式:
    (CLOSE - OPEN) / ((HIGH - LOW) + 0.001)

公式解释:
    当日实体与振幅的比值，类似于 K 线实体占比

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW/CLOSE（日频，后复权）

算子依赖:
    无（仅算术运算）

背后逻辑:
    通过实体与振幅的比值衡量 K 线形态。

适用场景:
    短期均值回复策略。

变种与优化:
    - 加入SMA平滑
    - 调整分母常数

注意事项:
    - 0.001 防止分母为零
    - 首期即可计算
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_138"]

DIRECTION = 1


def alpha_138(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #138: SMA2 时序方向判断。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low
    close = ctx.close

    return (close - open_) / ((high - low) + 0.001)

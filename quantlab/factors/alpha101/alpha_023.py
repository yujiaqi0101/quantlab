"""
Alpha101 #23 — 价格突破反转
========================================

公式:
    ((sum(high, 20) / 20) < high) ? -1 * delta(high, 2) : 0

公式解释:
    当最高价突破 20 日均线 (sum(high,20)/20) 时，取负的 2 日最高价变化量；否则为 0。
    突破后如果继续上涨则做空。

分类:
    价格突破 (price_breakout)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）

算子依赖:
    - ts_sum
    - delta

背后逻辑:
    突破 20 日均线后，若价格继续上涨 (delta(high,2)>0)，取负值看空 (反转)；
    若突破后下跌 (delta<0)，取正值看多。核心是突破后的均值回归。
    未突破时信号为 0，避免震荡市场的噪音。

适用场景:
    突破后反转策略，仅在突破时触发信号。

变种与优化:
    - 可使用 10/50 日均线替代 20 日
    - 可引入成交量突破条件
    - 可使用其他价格字段 (close/low)

注意事项:
    - 突破条件为布尔，信号不连续
    - 前 21 期返回 NaN (sum 20 + delta 2)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_sum

__all__ = ["alpha_023"]

DIRECTION = -1


def alpha_023(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #23: 价格突破反转。

    公式: (ma(high,20) < high) ? -1 * delta(high, 2) : 0

    Args:
        ctx: 因子数据上下文

    Returns:
        价格突破反转因子面板 (date × symbol)
    """
    ma20 = ts_sum(ctx.high, 20) / 20
    breakout = ma20 < ctx.high
    d_high = delta(ctx.high, 2)
    return (-1 * d_high).where(breakout, 0.0)

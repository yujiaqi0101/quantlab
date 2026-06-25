"""
Alpha191 #163 — 收益率方差时序平滑比
========================================

公式:
    3 * SMA(CLOSE, 5, 1) - 2 * SMA(SMA(CLOSE, 5, 1), 5, 1)

公式解释:
    计算5日SMA(close) 与 其自身的5日SMA 的3倍差值
    = 3*ema1 - 2*ema2 (类似DEMA)

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - sma (SMA(X, n, m))

背后逻辑:
    双重指数平滑差，减少价格滞后。

适用场景:
    短期趋势策略。

变种与优化:
    - 调整窗口 5
    - 替换为 TEMA

注意事项:
    - SMA 使用 ewm, 无 NaN 预热期
    - 首期即可计算
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_163"]

DIRECTION = 1


def alpha_163(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #163: 收益率方差时序平滑比。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    sma1 = sma(close, 5, 1)
    sma2 = sma(sma1, 5, 1)
    return 3.0 * sma1 - 2.0 * sma2

"""
Alpha191 #95 — 20日成交额波动率
========================================

公式:
    STD(AMOUNT, 20)

公式解释:
    计算 20 日成交额的滚动标准差。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - AMOUNT 成交额（日频）。缺失时由 VWAP*VOLUME 或 CLOSE*VOLUME 近似。

算子依赖:
    - ts_std

背后逻辑:
    与 Alpha70 类似但使用 20 日窗口期，反映中期成交额波动。
    更长窗口平滑了短期噪声，捕捉中期市场分歧度变化。

适用场景:
    中期成交额波动率策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 建议用成交额均值标准化 (变异系数) 以消除水平差异

注意事项:
    - 不同标的成交额水平差异大，标准差不具可比性，截面使用前应做标准化
    - AMOUNT 缺失时由 ctx.get_amount() 兜底近似，精度有限
    - 前 20 期数据不足返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_095"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_095(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #95: 20日成交额波动率。

    公式: STD(AMOUNT, period)

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 20)

    Returns:
        成交额波动率面板 (date × symbol)
    """
    amount = ctx.get_amount()
    return ts_std(amount, period)

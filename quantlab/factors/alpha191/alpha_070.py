"""
Alpha191 #70 — 6日成交额波动率
========================================

公式:
    STD(AMOUNT, 6)

公式解释:
    计算 6 日成交额的滚动标准差。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - AMOUNT 成交额（日频）。缺失时由 VWAP*VOLUME 或 CLOSE*VOLUME 近似。

算子依赖:
    - ts_std

背后逻辑:
    成交额标准差衡量近期成交活跃度的波动。高值表示成交额波动剧烈，
    可能反映市场分歧加大。正向偏好分歧加大、活跃度提升的股票。

适用场景:
    成交额波动率策略，捕捉市场分歧度上升的机会。

变种与优化:
    - 可调整窗口期 (6 → 10/20)
    - 建议用成交额均值标准化 (变异系数) 以消除水平差异

注意事项:
    - 不同标的成交额水平差异大，标准差不具可比性，截面使用前应做标准化
    - AMOUNT 缺失时由 ctx.get_amount() 兜底近似，精度有限
    - 前 6 期数据不足返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_070"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_070(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #70: 6日成交额波动率。

    公式: STD(AMOUNT, period)

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 6)

    Returns:
        成交额波动率面板 (date × symbol)
    """
    amount = ctx.get_amount()
    return ts_std(amount, period)

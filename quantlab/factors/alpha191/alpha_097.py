"""
Alpha191 #97 — 10日成交量波动率
========================================

公式:
    STD(VOLUME, 10)

公式解释:
    计算 10 日成交量的滚动标准差。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - ts_std

背后逻辑:
    成交量标准差衡量短期成交活跃度的波动。高值表示成交量波动剧烈，
    可能预示趋势启动或资金切换。正向偏好活跃度波动的股票。

适用场景:
    成交量波动率策略，捕捉短期资金活跃度变化。

变种与优化:
    - 可调整窗口期 (10 → 20)
    - 建议用成交量均值标准化 (变异系数) 以消除水平差异

注意事项:
    - 不同标的成交量水平差异大，标准差不具可比性，截面使用前应做标准化
    - 前 10 期数据不足返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_097"]

DIRECTION = 1
DEFAULT_PERIOD = 10


def alpha_097(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #97: 10日成交量波动率。

    公式: STD(VOLUME, period)

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 10)

    Returns:
        成交量波动率面板 (date × symbol)
    """
    return ts_std(ctx.volume, period)

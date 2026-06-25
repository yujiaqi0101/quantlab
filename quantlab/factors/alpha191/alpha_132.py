"""
Alpha191 #132 — 20日成交额均值
========================================

公式:
    MEAN(AMOUNT, 20)

公式解释:
    计算20日成交额均值。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - AMOUNT 成交额（日频）

算子依赖:
    - ts_mean (滚动均值)

背后逻辑:
    成交额均值衡量了股票的平均成交活跃度和流动性水平。
    高成交额表示市场关注度高，流动性好。

适用场景:
    流动性选股策略。

变种与优化:
    - 可调整窗口期 (20 → 10/30)
    - 做截面标准化
    - 使用对数变换处理规模差异

注意事项:
    - 成交额受股票规模影响大
    - 前 19 期返回 NaN (rolling 20)
    - 需做市值中性化处理 (当前未实现)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_132"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_132(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #132: 20日成交额均值。

    公式: MEAN(AMOUNT, period)

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 20)

    Returns:
        成交额均值因子面板 (date × symbol)
    """
    amount = ctx.get_amount()
    return ts_mean(amount, period)

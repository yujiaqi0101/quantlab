"""
Alpha101 #8 — 价格-收益乘积动量
========================================

公式:
    -1 * rank((sum(open, 5) * sum(returns, 5)) - delay((sum(open, 5) * sum(returns, 5)), 10))

公式解释:
    计算 5 日累计开盘价与 5 日累计收益率的乘积，再取 10 日变化量，截面排名取负。

分类:
    价格-收益乘积动量 (price_return_momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - ts_sum
    - delay
    - rank (截面)

背后逻辑:
    开盘价水平与收益率乘积反映"价格×收益"联合动量。
    取 10 日变化量捕捉该乘积的趋势变化，
    排名取负表示乘积动量反转 — 乘积上升的标的看空，下降的标的看多。

适用场景:
    开盘价与收益率联合动量反转策略。

变种与优化:
    - 可用 close 替代 open
    - 可调整窗口 (5/10 → 10/20)
    - 可用 decay_linear 平滑

注意事项:
    - 前 15 期返回 NaN (sum 5 + delay 10)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_008"]

DIRECTION = 1


def alpha_008(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #8: 价格-收益乘积动量。

    公式: -1 * rank(sum(open,5)*sum(returns,5) - delay(sum(open,5)*sum(returns,5),10))

    Args:
        ctx: 因子数据上下文

    Returns:
        价格-收益乘积动量因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    prod = ts_sum(ctx.open, 5) * ts_sum(returns, 5)
    return -1 * rank(prod - delay(prod, 10))

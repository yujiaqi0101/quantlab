"""
Alpha101 #19 — 价格动量-长期收益
========================================

公式:
    ((-1 * sign(((close - delay(close, 7)) + delta(close, 7)))) * (1 + rank((1 + sum(returns, 250)))))

公式解释:
    7 日价格变化方向符号取负，乘以 (1+250 日累计收益率排名)。
    结合短期价格方向与长期收益水平。

分类:
    价格动量-长期收益 (price_momentum_long_term_return)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - delay
    - delta
    - sign (内置)
    - ts_sum
    - rank (截面)

背后逻辑:
    sign 项提供短期价格方向 (7 日动量)，取负做反转；
    (1+rank(sum)) 项提供幅度调制 (长期收益水平)。
    短期反转叠加长期动量确认。

适用场景:
    短期反转与长期动量的结合策略。

变种与优化:
    - 可调整窗口 (7/250 → 5/120)
    - 可用 ts_rank 替代 rank
    - 可用 decay_linear 平滑 sign 项

注意事项:
    - 前 257 期返回 NaN (delay 7 + sum 250 - 重叠)
    - 250 日长窗口需足够历史数据
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, delay, ts_sum

__all__ = ["alpha_019"]

DIRECTION = 1


def alpha_019(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #19: 价格动量-长期收益。

    公式: -sign((close-delay(close,7))+delta(close,7)) * (1+rank(1+sum(returns,250)))

    Args:
        ctx: 因子数据上下文

    Returns:
        价格动量-长期收益因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    close = ctx.close
    d7 = delta(close, 7)
    sign_part = -1 * np.sign((close - delay(close, 7)) + d7)
    magnitude = 1 + rank(1 + ts_sum(returns, 250))
    return sign_part * magnitude

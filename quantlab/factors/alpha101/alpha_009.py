"""
Alpha101 #9 — 趋势一致性因子
========================================

公式:
    (0 < ts_min(delta(close,1), 5)) ? delta(close,1)
    : ((ts_max(delta(close,1), 5) < 0) ? delta(close,1) : (-1 * delta(close,1)))

公式解释:
    若过去 5 日价格变化最小值 > 0 (持续上涨)，取当日变化；
    若过去 5 日价格变化最大值 < 0 (持续下跌)，也取当日变化；
    否则取反向变化。趋势一致时顺势，不一致时反转。

分类:
    趋势一致性 (trend_consistency)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delta
    - ts_min
    - ts_max

背后逻辑:
    核心是趋势一致时顺势 (动量)，趋势不一致时反转 (均值回归)。
    持续上涨/下跌时动量有效，震荡时反转有效。
    这是一种自适应的动量-反转切换策略。

适用场景:
    趋势跟踪与反转的混合策略，适应不同市场状态。

变种与优化:
    - 可调整趋势判断窗口 (5 → 10/20)
    - Alpha#10 使用 4 日窗口并加外层 rank
    - 可引入成交量确认条件
    - 可使用平滑后的价格变化

注意事项:
    - 条件分支会产生不连续的因子值
    - 前 6 期数据不足返回 NaN (delta 1 + ts_min/max 5)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_min, ts_max

__all__ = ["alpha_009"]

DIRECTION = 1
DEFAULT_PERIOD = 5


def alpha_009(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #9: 趋势一致性因子。

    公式:
        if ts_min(delta(close,1), period) > 0: delta(close,1)
        elif ts_max(delta(close,1), period) < 0: delta(close,1)
        else: -1 * delta(close,1)

    Args:
        ctx: 因子数据上下文
        period: 趋势判断窗口 (默认 5)

    Returns:
        趋势一致性因子面板 (date × symbol)
    """
    d1 = delta(ctx.close, 1)
    min_d1 = ts_min(d1, period)
    max_d1 = ts_max(d1, period)
    # 条件分支
    cond_up = min_d1 > 0          # 持续上涨
    cond_down = max_d1 < 0        # 持续下跌
    result = d1.where(cond_up | cond_down, -1 * d1)
    return result

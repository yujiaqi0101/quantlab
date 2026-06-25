"""
Alpha101 #57 — 趋势一致性
============================

公式:
    (0 < ts_min(delta(close, 1), 4)) ? delta(close, 1) :
      ((ts_max(delta(close, 1), 4) < 0) ? delta(close, 1) : -1 * delta(close, 1))

公式解释:
    与 Alpha#9 结构相同但使用 4 日窗口。趋势一致时顺势，不一致时反转。
    - 当近 4 日最小涨幅 > 0 (持续上涨) 时，顺势取当日涨幅
    - 当近 4 日最大涨幅 < 0 (持续下跌) 时，顺势取当日涨幅
    - 否则 (趋势不一致) 反转，取负的当日涨幅

分类:
    趋势一致性 (trend_consistency)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delta (时序差分)
    - ts_min (滚动最小值)
    - ts_max (滚动最大值)

背后逻辑:
    与 Alpha#9/10 类似但无外层 rank。
    趋势一致时顺势，不一致时反转。

适用场景:
    与 Alpha#9/10 类似，适用于趋势跟踪与反转的混合策略。

变种与优化:
    - 可调整窗口参数 (4 → 9)
    - 可引入成交量确认

注意事项:
    - 与 Alpha#10 非常相似但无外层 rank
    - 前 5 期因 delta(1) + ts_min/ts_max(4) 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_max, ts_min

__all__ = ["alpha_057"]

DIRECTION = -1
DEFAULT_PERIOD = 4


def alpha_057(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #57: 趋势一致性。

    公式: (0 < ts_min(delta(close, 1), period)) ? delta(close, 1) : ((ts_max(delta(close, 1), period) < 0) ? delta(close, 1) : -1 * delta(close, 1))

    Args:
        ctx: 因子数据上下文
        period: 趋势判断窗口 (默认 4)

    Returns:
        趋势一致性因子面板 (date × symbol)
    """
    d = delta(ctx.close, 1)
    min_d = ts_min(d, period)
    max_d = ts_max(d, period)
    # 持续上涨: min_d > 0 → 顺势
    # 持续下跌: max_d < 0 → 顺势
    # 否则: 反转
    return d.where((min_d > 0) | (max_d < 0), -1.0 * d)

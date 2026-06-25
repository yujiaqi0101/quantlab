"""
Alpha191 #110 — 20日AR指标
========================================

公式:
    SUM(MAX(0, HIGH-DELAY(CLOSE,1)), 20) / SUM(MAX(0, DELAY(CLOSE,1)-LOW), 20) * 100

公式解释:
    AR (人气指标) 累积: 前收盘价与最高价之差为正的部分作分子，
    前收盘价与最低价之差为正的部分作分母。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW/CLOSE（日频，后复权）

算子依赖:
    - delay
    - ts_sum

背后逻辑:
    AR 衡量开盘动能多空力量，反映市场人气。

适用场景:
    短期动量策略。

变种与优化:
    - 调整窗口 (20 → 10/26)
    - 使用 TP 代替 prev_close

注意事项:
    - 分母为 0 时返回 NaN
    - 前 21 期返回 NaN (delay 1 + ts_sum 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_110"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_110(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #110: 20日AR指标。

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 20)

    Returns:
        AR 因子面板 (date × symbol)
    """
    prev_close = delay(ctx.close, 1)
    up = (ctx.high - prev_close).clip(lower=0.0)
    down = (prev_close - ctx.low).clip(lower=0.0)
    sum_up = ts_sum(up, period)
    sum_down = ts_sum(down, period)
    safe_down = sum_down.where(sum_down.abs() > 0, np.nan)
    return sum_up / safe_down * 100.0

"""
Alpha191 #112 — CMO钱德动量振荡器
========================================

公式:
    (SUM(上涨差, 12) - SUM(下跌差, 12)) / (SUM(上涨差, 12) + SUM(下跌差, 12)) * 100

公式解释:
    计算12日内上涨差值之和减去下跌差值之和，
    除以上涨差值与下跌差值之和，乘以100，即CMO。

    上涨差 = MAX(CLOSE - DELAY(CLOSE, 1), 0)
    下跌差 = MAX(DELAY(CLOSE, 1) - CLOSE, 0)

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay (1日延迟)
    - ts_sum (滚动求和)

背后逻辑:
    CMO衡量了上涨力量与下跌力量的对比。
    值域为 -100 到 100，正值表示上涨力量占优。

适用场景:
    动量振荡策略。

变种与优化:
    - 可调整窗口期 (12 → 14/20)
    - 结合超买超卖区间使用
    - 加入成交量加权

注意事项:
    - CMO与RSI类似但计算方式不同
    - 分母为零时需特殊处理
    - 前 12 期返回 NaN (delay 1 + ts_sum 12)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_112"]

DIRECTION = 1
DEFAULT_PERIOD = 12


def alpha_112(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #112: CMO钱德动量振荡器。

    公式: (SUM(up, period) - SUM(down, period)) / (SUM(up, period) + SUM(down, period)) * 100

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 12)

    Returns:
        CMO因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)
    diff = close - prev_close
    up = diff.where(diff > 0, 0.0)
    down = (-diff).where(diff < 0, 0.0)
    sum_up = ts_sum(up, period)
    sum_down = ts_sum(down, period)
    denominator = sum_up + sum_down
    # 分母为 0 时返回 NaN
    safe_denom = denominator.where(denominator > 0, np.nan)
    return (sum_up - sum_down) / safe_denom * 100.0

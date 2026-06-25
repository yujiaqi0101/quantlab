"""
Alpha191 #52 — 26日AR累积指标
========================================

公式:
    SUM(MAX(0, HIGH-DELAY((HIGH+LOW+CLOSE)/3, 1)), 26)
    / SUM(MAX(0, DELAY((HIGH+LOW+CLOSE)/3, 1)-LOW), 26) * 100

公式解释:
    使用典型价格(TP=(H+L+C)/3)的延迟值衡量多空力量：
    - 上推力: TP延迟值与最高价之差为正的部分
    - 下推力: TP延迟值与最低价之差为负的部分
    比值*100 即 AR 指标。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay
    - ts_sum

背后逻辑:
    AR (人气指标) 用典型价格的延迟衡量多空力量的累积比，反映价格动能。

适用场景:
    动量策略。

变种与优化:
    - 调整窗口 (26 → 14/20)
    - 用 TP 不延迟版本

注意事项:
    - 分母为 0 时返回 NaN
    - 前 27 期数据不足时返回 NaN (delay 1 + ts_sum 26)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_052"]

DIRECTION = 1
DEFAULT_PERIOD = 26


def alpha_052(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #52: 26日AR累积指标。

    公式: SUM(MAX(0,HIGH-DELAY(TP,1)),N) / SUM(MAX(0,DELAY(TP,1)-LOW),N) * 100
        其中 TP = (HIGH+LOW+CLOSE)/3

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 26)

    Returns:
        AR 因子面板 (date × symbol)
    """
    tp = (ctx.high + ctx.low + ctx.close) / 3.0
    tp_prev = delay(tp, 1)

    up_force = (ctx.high - tp_prev).clip(lower=0.0)
    down_force = (tp_prev - ctx.low).clip(lower=0.0)

    sum_up = ts_sum(up_force, period)
    sum_down = ts_sum(down_force, period)

    # 分母为 0 时置 NaN
    safe_down = sum_down.where(sum_down.abs() > 0, np.nan)
    return sum_up / safe_down * 100.0

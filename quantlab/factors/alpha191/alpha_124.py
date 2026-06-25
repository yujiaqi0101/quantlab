"""
Alpha191 #124 — VWAP标准化偏离
========================================

公式:
    (close - vwap) / decaylinear(rank(ts_max(close, 30)), 2)

公式解释:
    计算收盘价与VWAP之差，除以30日最高收盘价
    截面排名的2日线性衰减移动平均。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VWAP 成交量加权均价（日频）

算子依赖:
    - ts_max (滚动最大值)
    - rank (截面排名)
    - decay_linear (线性衰减加权平均)

背后逻辑:
    将收盘价与VWAP的偏离用近期价格排名的
    衰减平均进行标准化。标准化后的偏离更具可比性。

适用场景:
    标准化量价偏离策略。

变种与优化:
    - 可调整窗口期 (30 → 20/60)
    - 使用不同的标准化方式
    - 加入成交额加权

注意事项:
    - 分母为 0 时返回 NaN
    - 衰减平均引入滞后
    - 前 30 期返回 NaN (ts_max 30)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.ts import ts_max

__all__ = ["alpha_124"]

DIRECTION = 1
DEFAULT_MAX_PERIOD = 30
DEFAULT_DECAY_PERIOD = 2


def alpha_124(
    ctx: FactorContext,
    max_period: int = DEFAULT_MAX_PERIOD,
    decay_period: int = DEFAULT_DECAY_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #124: VWAP标准化偏离。

    公式: (close - vwap) / decaylinear(rank(ts_max(close, max_period)), decay_period)

    Args:
        ctx: 因子数据上下文
        max_period: ts_max 窗口期 (默认 30)
        decay_period: 衰减平均窗口期 (默认 2)

    Returns:
        标准化偏离因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    numerator = ctx.close - vwap
    max_close = ts_max(ctx.close, max_period)
    denominator = decay_linear(rank(max_close), decay_period)
    # 分母为 0 时返回 NaN
    safe_denom = denominator.where(denominator > 0, np.nan)
    return numerator / safe_denom

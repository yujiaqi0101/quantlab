"""
Alpha191 #41 — VWAP 3日变化5日最大值排名反转
========================================

公式:
    RANK(MAX(DELTA(VWAP, 3), 5)) * -1

公式解释:
    计算 VWAP 3日变化量的5日最大值的截面排名，取负值。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好 VWAP 变化幅度小的标的）

数据来源与频率:
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - delta
    - ts_max
    - rank (截面)

背后逻辑:
    该因子捕捉 VWAP 短期变化的最大幅度。取负值偏好 VWAP 变化幅度小的
    股票，即价格相对稳定的标的，类似低波动反转逻辑。

适用场景:
    低波动选股策略。

变种与优化:
    - 可调整 delta 窗口期 (3 → 5)
    - 调整 ts_max 窗口期 (5 → 10)
    - 使用不同的价格基准 (CLOSE 代替 VWAP)

注意事项:
    - ts_max 易受极端值影响，需做极值处理
    - VWAP 缺失时用 amount/volume 近似，可能引入误差
    - 前 7 期数据不足时返回 NaN (delta 3 + ts_max 5 - 1)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_max

__all__ = ["alpha_041"]

DIRECTION = -1
DEFAULT_DELTA_PERIOD = 3
DEFAULT_MAX_PERIOD = 5


def alpha_041(
    ctx: FactorContext,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    max_period: int = DEFAULT_MAX_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #41: VWAP 3日变化5日最大值排名反转。

    公式: -1 * RANK(ts_max(delta(VWAP, delta_period), max_period))

    Args:
        ctx: 因子数据上下文
        delta_period: VWAP 变化窗口期 (默认 3)
        max_period: 最大值窗口期 (默认 5)

    Returns:
        反向动量因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    change = delta(vwap, delta_period)
    return -1.0 * rank(ts_max(change, max_period))

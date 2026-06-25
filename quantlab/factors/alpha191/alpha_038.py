"""
Alpha191 #38 — 突破回落反转
========================================

公式:
    ((SUM(HIGH,20)/20) < HIGH) ? (-1 * DELTA(HIGH, 2)) : 0

公式解释:
    当20日均价最高价小于当前最高价时（即突破20日高点），
    取2日最高价变化量的负值；否则为0。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好突破后短期回落标的）

数据来源与频率:
    - HIGH 最高价（日频，后复权）

算子依赖:
    - ts_sum
    - delta

背后逻辑:
    该因子在价格突破20日高点时触发，取2日变化量的负值意味着
    偏好突破后短期回落的股票。本质上是一个突破失败的反转信号，
    捕捉假突破后的均值回复机会。

适用场景:
    突破反转策略。

变种与优化:
    - 可调整均线窗口期 (20 → 10/30)
    - 调整变化量窗口期 (2 → 3/5)
    - 使用不同的突破判断条件 (如收盘价突破)

注意事项:
    - 突破信号触发频率较低
    - 需关注假突破的情况
    - 前 20 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_sum

__all__ = ["alpha_038"]

DIRECTION = -1
DEFAULT_MA_PERIOD = 20
DEFAULT_DELTA_PERIOD = 2


def alpha_038(
    ctx: FactorContext,
    ma_period: int = DEFAULT_MA_PERIOD,
    delta_period: int = DEFAULT_DELTA_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #38: 突破回落反转。

    公式: where(MA(HIGH,ma_period) < HIGH, -1*DELTA(HIGH,delta_period), 0)

    Args:
        ctx: 因子数据上下文
        ma_period: 均线窗口期 (默认 20)
        delta_period: 变化量窗口期 (默认 2)

    Returns:
        突破反转因子面板 (date × symbol)
    """
    high = ctx.high
    ma_high = ts_sum(high, ma_period) / ma_period
    change = delta(high, delta_period)
    # 突破时取 -change，否则 0；预热期 (ma_high NaN) 返回 NaN
    result = (-change).where(ma_high < high, 0.0)
    return result.where(ma_high.notna())

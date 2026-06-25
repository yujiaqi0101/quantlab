"""
Alpha101 #24 — 长期均值回归
========================================

公式:
    (((delta((sum(close, 100) / 100), 100) / delay(close, 100)) < 0.05)
     || ((delta((sum(close, 100) / 100), 100) / delay(close, 100)) == 0.05))
    ? -1 * (close - ts_min(close, 100))
    : -1 * delta(close, 3)

公式解释:
    如果 100 日均线的变化率不超过 5%，则做空 (收盘价-100日最低价)；
    否则做空 3 日价格变化。
    低趋势环境下做均值回归，高趋势环境下做短期反转。

分类:
    长期均值回归 (long_term_mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看空

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_sum
    - delta
    - delay
    - ts_min

背后逻辑:
    100 日均线变化率衡量长期趋势强度。
    趋势弱 (≤5%) 时市场处于震荡，做均值回归 (收盘价 vs 100 日最低)；
    趋势强 (>5%) 时做短期反转 (3 日变化)。
    自适应区分趋势和震荡市场。

适用场景:
    区分趋势和震荡市场的自适应策略。

变种与优化:
    - 可调整阈值 (0.05 → 动态分位数)
    - 可用不同窗口 (100/100/3)
    - 可引入波动率确认

注意事项:
    - 前 200 期返回 NaN (sum 100 + delay 100)
    - 100 日长窗口需足够历史数据
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, delay, ts_min, ts_sum

__all__ = ["alpha_024"]

DIRECTION = -1


def alpha_024(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #24: 长期均值回归。

    公式: 若 100 日均线变化率 <= 5% 则 -1*(close-ts_min(close,100)) 否则 -1*delta(close,3)

    Args:
        ctx: 因子数据上下文

    Returns:
        长期均值回归因子面板 (date × symbol)
    """
    close = ctx.close
    ma100 = ts_sum(close, 100) / 100
    change_rate = delta(ma100, 100) / delay(close, 100)
    low_trend = change_rate <= 0.05
    result = (-1 * (close - ts_min(close, 100))).where(
        low_trend, -1 * delta(close, 3)
    )
    return result.where(change_rate.notna())

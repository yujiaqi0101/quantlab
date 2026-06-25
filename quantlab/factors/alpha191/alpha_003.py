"""
Alpha191 #3 — 考虑跳空缺口的累积价格变动
========================================

公式:
    SUM((CLOSE=DELAY(CLOSE,1) ? 0
         : CLOSE - (CLOSE>DELAY(CLOSE,1) ? MIN(LOW,DELAY(CLOSE,1))
                                          : MAX(HIGH,DELAY(CLOSE,1)))), 6)

公式解释:
    计算6日内每日的真实价格变化（考虑跳空缺口）。若收盘价高于前一日，
    取当日收盘价减去前一日收盘价与前一日最低价的较小者；若低于前一日，
    取差值的绝对值；平盘则为0，最后求和。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、HIGH 最高价、LOW 最低价（日频，后复权）

算子依赖:
    - delay
    - ts_sum
    - numpy.minimum / maximum

背后逻辑:
    该因子衡量考虑跳空缺口后的累积价格变动。上涨日取较小值（保守估计涨幅），
    下跌日取较大值（充分估计跌幅），本质上是不对称的价格变动度量，反映
    价格的真实推进力度。

适用场景:
    趋势跟踪策略，累积真实推进力度大的股票更可能延续趋势。

变种与优化:
    - 可调整窗口期 (6 → 10/20)
    - 加入成交量加权
    - 使用不同的缺口处理方式

注意事项:
    - 跳空缺口处理方式对结果影响较大
    - 需注意除权除息日的价格调整
    - 前 6 期数据不足时返回 NaN (delay 1 + ts_sum 6)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_003"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_003(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #3: 考虑跳空缺口的累积价格变动。

    公式: SUM(true_change, period)
          true_change = 0 if CLOSE=prev else
                        CLOSE - (CLOSE>prev ? MIN(LOW,prev) : MAX(HIGH,prev))

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 6)

    Returns:
        累积推进因子面板 (date × symbol)
    """
    close = ctx.close
    prev = delay(close, 1)
    # 上涨日：CLOSE - MIN(LOW, prev)
    up_part = close - np.minimum(ctx.low, prev)
    # 下跌日：CLOSE - MAX(HIGH, prev)（结果为负，绝对值由符号自然处理）
    down_part = close - np.maximum(ctx.high, prev)
    true_change = up_part.where(close > prev, down_part.where(close < prev, 0.0))
    true_change = true_change.where(prev.notna())
    return ts_sum(true_change, period)

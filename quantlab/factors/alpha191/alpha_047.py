"""
Alpha191 #47 — 6日高低区间位置SMA平滑
========================================

公式:
    SMA((TSMAX(HIGH,6) - CLOSE) / (TSMAX(HIGH,6) - TSMIN(LOW,6)) * 100, 9, 1)

公式解释:
    计算收盘价在6日高低区间中的相对位置（类似RSV，但反向），进行9日SMA平滑。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好超卖标的）

数据来源与频率:
    - CLOSE 收盘价、HIGH 最高价、LOW 最低价（日频，后复权）

算子依赖:
    - ts_max
    - ts_min
    - sma (指数平滑)

背后逻辑:
    该因子类似于随机指标的平滑版本。当收盘价接近近期低点时，因子值较高，
    表示超卖。反向选择意味着偏好因子值高的股票（超卖反弹）。

适用场景:
    均值回复策略。

变种与优化:
    - 可调整窗口期 (6/9)
    - 使用不同的平滑方法
    - 结合其他超卖指标

注意事项:
    - SMA 平滑会引入滞后
    - 需关注高低区间为零的情况
    - 前 5 期数据不足时返回 NaN (6日高低点预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import ts_max, ts_min

__all__ = ["alpha_047"]

DIRECTION = -1
DEFAULT_RANGE_PERIOD = 6
DEFAULT_SMA_N = 9
DEFAULT_SMA_M = 1


def alpha_047(
    ctx: FactorContext,
    range_period: int = DEFAULT_RANGE_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #47: 6日高低区间位置SMA平滑。

    公式: SMA((TSMAX(HIGH,range_period)-CLOSE)/(TSMAX(HIGH,range_period)-TSMIN(LOW,range_period))*100, sma_n, sma_m)

    Args:
        ctx: 因子数据上下文
        range_period: 高低区间窗口期 (默认 6)
        sma_n: SMA 分母参数 (默认 9)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        超卖反弹因子面板 (date × symbol)
    """
    close = ctx.close
    hhv = ts_max(ctx.high, range_period)
    llv = ts_min(ctx.low, range_period)
    rng = (hhv - llv).replace(0, np.nan)
    pos = (hhv - close) / rng * 100.0
    return sma(pos, sma_n, sma_m)

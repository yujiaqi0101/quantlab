"""
Alpha191 #96 — KDJ-D值
========================================

公式:
    SMA(SMA(RSV, 3, 1), 3, 1)

公式解释:
    计算 RSV 的3日SMA的再3日SMA，即KDJ指标中的D值。

    RSV = (CLOSE - MIN(LOW, 9)) / (MAX(HIGH, 9) - MIN(LOW, 9)) * 100

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - ts_max (滚动最大值)
    - ts_min (滚动最小值)
    - sma (指数平滑)

背后逻辑:
    D值是K值的平滑版本，更加稳定。
    D值高表示价格处于近期高位区域。

适用场景:
    动量策略。

变种与优化:
    - 可调整KDJ参数 (9/3/3 → 其他)
    - 结合K值和J值使用
    - 加入超买超卖区间判断

注意事项:
    - D值响应较慢
    - 需结合K值判断趋势变化
    - ewm 从首期开始计算, 无 NaN 预热
    - (HIGH - LOW) 为 0 时 RSV 返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import ts_max, ts_min

__all__ = ["alpha_096"]

DIRECTION = 1
DEFAULT_PERIOD = 9
DEFAULT_SMA_N = 3
DEFAULT_SMA_M = 1


def alpha_096(
    ctx: FactorContext,
    period: int = DEFAULT_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #96: KDJ-D值。

    公式: SMA(SMA(RSV, sma_n, sma_m), sma_n, sma_m)
        RSV = (CLOSE - ts_min(LOW, period)) / (ts_max(HIGH, period) - ts_min(LOW, period)) * 100

    Args:
        ctx: 因子数据上下文
        period: RSV 窗口期 (默认 9)
        sma_n: SMA 分母参数 (默认 3)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        KDJ-D值因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    close = ctx.close
    highest = ts_max(high, period)
    lowest = ts_min(low, period)
    hl_range = highest - lowest
    safe_range = hl_range.where(hl_range > 0, np.nan)
    rsv = (close - lowest) / safe_range * 100.0
    k = sma(rsv, sma_n, sma_m)
    d = sma(k, sma_n, sma_m)
    return d

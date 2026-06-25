"""
Alpha191 #22 — 偏离均值度3日变化SMA平滑
========================================

公式:
    SMA(DELTA((CLOSE-MEAN(CLOSE,6))/MEAN(CLOSE,6), 3), 12, 1)

公式解释:
    计算收盘价偏离6日均值的比率，再取其3日变化量，最后进行12日SMA平滑。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean
    - delta
    - sma (指数平滑)

背后逻辑:
    该因子衡量价格偏离均值程度的变化趋势。当偏离度在扩大时（变化量为正），
    说明价格正在远离均值；缩小时则相反。反向意味着偏好偏离度缩小的股票
    （均值回复逻辑）。

适用场景:
    均值回复策略，捕捉价格回归均值的信号。

变种与优化:
    - 可调整各窗口期 (6/3/12)
    - 使用不同的均值计算方式 (WMA/EMA)
    - 结合波动率标准化

注意事项:
    - 文档公式含省略号，此处按解释实现为偏离度的3日变化量
    - SMA 平滑会引入滞后
    - 前 8 期数据不足时返回 NaN (6日均值 + 3日变化)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delta, ts_mean

__all__ = ["alpha_022"]

DIRECTION = -1
DEFAULT_MEAN_PERIOD = 6
DEFAULT_DELTA_PERIOD = 3
DEFAULT_SMA_N = 12
DEFAULT_SMA_M = 1


def alpha_022(
    ctx: FactorContext,
    mean_period: int = DEFAULT_MEAN_PERIOD,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #22: 偏离均值度3日变化SMA平滑。

    公式: SMA(DELTA((CLOSE-MEAN(CLOSE,mean_period))/MEAN(CLOSE,mean_period), delta_period), sma_n, sma_m)

    Args:
        ctx: 因子数据上下文
        mean_period: 均值窗口期 (默认 6)
        delta_period: 变化量窗口期 (默认 3)
        sma_n: SMA 分母参数 (默认 12)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        均值回复因子面板 (date × symbol)
    """
    close = ctx.close
    ma = ts_mean(close, mean_period)
    deviation = (close - ma) / ma
    change = delta(deviation, delta_period)
    return sma(change, sma_n, sma_m)

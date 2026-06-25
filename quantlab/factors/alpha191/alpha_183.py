"""
Alpha191 #183 — 24日累积偏离极差波动率
========================================

公式:
    MAX(SUMAC(CLOSE - MA24)) - MIN(SUMAC(CLOSE - MA24)) / STD(CLOSE, 24)

公式解释:
    计算收盘价与24日均线之差的累积和 (SUMAC) 的最大值减去最小值，
    除以24日收盘价标准差。
    与 Alpha165 类似但使用24日窗口期。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean (MA24)
    - sumac (累积和)
    - ts_max, ts_min
    - ts_std

背后逻辑:
    与 Alpha165 类似但使用24日窗口期。
    衡量价格偏离均值的累积波动，用标准差标准化。

适用场景:
    累积偏离波动率策略，中短期累积偏离。

变种与优化:
    - 可调整窗口期 (24 → 其他)
    - 使用不同的均值计算方式
    - 与其他波动率因子组合

注意事项:
    - 累积和可能随时间发散
    - 前 47 期返回 NaN (MA24 + SUMAC 24)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import sumac
from quantlab.factors.operators.ts import ts_max, ts_mean, ts_min, ts_std

__all__ = ["alpha_183"]

DIRECTION = 1


def alpha_183(ctx: FactorContext, period: int = 24) -> pd.DataFrame:
    """Alpha191 #183: 24日累积偏离极差波动率。

    公式: MAX(SUMAC(CLOSE-MA24)) - MIN(SUMAC(CLOSE-MA24)) / STD(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: 窗口期 (默认 24)

    Returns:
        累积偏离极差波动率因子面板 (date × symbol)
    """
    close = ctx.close
    ma = ts_mean(close, period)
    dev = close - ma
    cum_dev = sumac(dev, period)
    spread = ts_max(cum_dev, period) - ts_min(cum_dev, period)
    std = ts_std(close, period)
    std = std.replace(0, np.nan)
    return spread / std

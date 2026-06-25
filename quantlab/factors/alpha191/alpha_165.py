"""
Alpha191 #165 — 48日累积偏离极差波动率
========================================

公式:
    MAX(SUMAC(CLOSE - MA48)) - MIN(SUMAC(CLOSE - MA48)) / STD(CLOSE, 48)

公式解释:
    计算收盘价与48日均线之差的累积和 (SUMAC) 的最大值减去最小值，
    除以48日收盘价标准差。
    MA48 = MEAN(CLOSE, 48)。
    SUMAC(x, n) 为窗口 n 内累积和。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean (MA48)
    - sumac (累积和)
    - ts_max, ts_min
    - ts_std

背后逻辑:
    该因子衡量价格偏离均值的累积幅度的极差，
    用标准差标准化。
    高值表示价格偏离均值的累积波动大。

适用场景:
    累积偏离波动率策略，捕捉长期累积偏离。

变种与优化:
    - 可调整窗口期 (48 → 其他)
    - 使用不同的均值计算方式 (如 EMA)
    - 与其他波动率因子组合

注意事项:
    - 累积和可能随时间发散，需做适当处理
    - 前 95 期返回 NaN (MA48 + SUMAC 48)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import sumac
from quantlab.factors.operators.ts import ts_max, ts_mean, ts_min, ts_std

__all__ = ["alpha_165"]

DIRECTION = 1


def alpha_165(ctx: FactorContext, period: int = 48) -> pd.DataFrame:
    """Alpha191 #165: 48日累积偏离极差波动率。

    公式: MAX(SUMAC(CLOSE-MA48)) - MIN(SUMAC(CLOSE-MA48)) / STD(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: 窗口期 (默认 48)

    Returns:
        累积偏离极差波动率因子面板 (date × symbol)
    """
    close = ctx.close
    ma = ts_mean(close, period)
    dev = close - ma
    cum_dev = sumac(dev, period)
    # MAX(SUMAC) - MIN(SUMAC)
    spread = ts_max(cum_dev, period) - ts_min(cum_dev, period)
    std = ts_std(close, period)
    std = std.replace(0, np.nan)
    return spread / std

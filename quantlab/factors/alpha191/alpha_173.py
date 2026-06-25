"""
Alpha191 #173 — 3日SMA的最小值
========================================

公式:
    SMA(DELAY(CLOSE/DELAY(CLOSE,3),1), 3, 1)

公式解释:
    计算3日前收盘价比率
    延迟1期后进行SMA(3,1)平滑

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - sma (SMA(X, n, m))
    - delay

背后逻辑:
    短期价格比率的平滑趋势。

适用场景:
    短期动量策略。

变种与优化:
    - 调整窗口 3
    - 替换为对数收益率

注意事项:
    - 分母为 0 时返回 NaN
    - 前 4 期返回 NaN (delay 3 + delay 1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_173"]

DIRECTION = 1


def alpha_173(ctx: FactorContext, period: int = 3) -> pd.DataFrame:
    """Alpha191 #173: 3日SMA的最小值。

    Args:
        ctx: 因子数据上下文
        period: 比率窗口期 (默认 3)

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, period)
    ratio = close / prev_close.where(prev_close.abs() > 0, np.nan)
    return sma(delay(ratio, 1), 3, 1)

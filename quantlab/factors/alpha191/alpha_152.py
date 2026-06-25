"""
Alpha191 #152 — SMA延迟的15日差值
========================================

公式:
    SMA(DELAY(CLOSE/DELAY(CLOSE,20),1), 20, 1)

公式解释:
    计算 close 与20日前收盘价的比率
    对该比率延迟1期后进行SMA(20,1)平滑

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
    长期价格比率的平滑趋势。

适用场景:
    长期动量策略。

变种与优化:
    - 调整窗口 20
    - 替换为 ts_mean

注意事项:
    - 前 21 期返回 NaN (delay 20 + delay 1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_152"]

DIRECTION = 1


def alpha_152(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #152: SMA延迟的15日差值。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close_20 = delay(close, 20)
    ratio = close / prev_close_20.where(prev_close_20.abs() > 0, np.nan)
    return sma(delay(ratio, 1), 20, 1)

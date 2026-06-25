"""
Alpha191 #162 — 12日SMA的最小值
========================================

公式:
    SMA(SMA(SMA(MAX(CLOSE-DELAY(CLOSE,1),0),2,1),2,1),2,1)
    / SMA(SMA(SMA(MIN(CLOSE-DELAY(CLOSE,1),0),2,1),2,1),2,1)
    - 1

公式解释:
    分子: 正收益的三重SMA(2,1)平滑
    分母: 负收益的三重SMA(2,1)平滑
    结果: 分子/分母 - 1

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
    通过正负收益平滑比率的相对强弱判断趋势。

适用场景:
    短期动量策略。

变种与优化:
    - 调整窗口 2
    - 调整平滑次数

注意事项:
    - 分母为 0 时返回 NaN
    - 前 1 期返回 NaN (delay 1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_162"]

DIRECTION = 1


def alpha_162(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #162: 12日SMA的最小值。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    diff = close - delay(close, 1)
    up = diff.clip(lower=0.0)
    down = diff.clip(upper=0.0)

    up_smooth = sma(sma(sma(up, 2, 1), 2, 1), 2, 1)
    down_smooth = sma(sma(sma(down, 2, 1), 2, 1), 2, 1)

    safe_down = down_smooth.where(down_smooth.abs() > 0, np.nan)
    return up_smooth / safe_down - 1.0

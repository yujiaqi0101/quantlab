"""
Alpha191 #151 — 复杂多窗口量价结构
========================================

公式:
    SMA(CLOSE>DELAY(CLOSE,1),12,1) - SMA(CLOSE<=DELAY(CLOSE,1),12,1) / (SMA(CLOSE>DELAY(CLOSE,1),12,1)
        + SMA(CLOSE<=DELAY(CLOSE,1),12,1))

公式解释:
    up_sma = SMA((CLOSE>prev_CLOSE), 12, 1)
    down_sma = SMA((CLOSE<=prev_CLOSE), 12, 1)
    结果 = (up_sma - down_sma) / (up_sma + down_sma)

    实质上是 RSI 式的相对强弱指标，但用 SMA(12,1) 而非 SMA(alpha=1/n)

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - sma
    - delay

背后逻辑:
    上涨天数与下跌天数的平滑比率，类似于 RSI。

适用场景:
    短期动量策略。

变种与优化:
    - 调整窗口 12
    - 用 ts_rank 替代 sma

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

__all__ = ["alpha_151"]

DIRECTION = 1


def alpha_151(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #151: 复杂多窗口量价结构。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)

    up = (close > prev_close).astype(float)
    down = (close <= prev_close).astype(float)

    # NaN 保护: prev_close 为 NaN 时(idx 0) indicator 也应为 NaN
    mask = prev_close.notna()
    up = up.where(mask)
    down = down.where(mask)

    up_sma = sma(up, 12, 1)
    down_sma = sma(down, 12, 1)

    denom = up_sma + down_sma
    safe_denom = denom.where(denom.abs() > 0, np.nan)
    return (up_sma - down_sma) / safe_denom

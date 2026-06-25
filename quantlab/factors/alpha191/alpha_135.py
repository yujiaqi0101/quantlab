"""
Alpha191 #135 — SMA 平滑价格比
========================================

公式:
    SMA(CLOSE<DELAY(CLOSE,1), 5, 1) - 0.5

公式解释:
    当 收盘价 < 前一日收盘价 时取1，否则取0
    对该0/1序列进行SMA(5,1)平滑
    最后减去0.5作为平衡

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - sma (SMA(x, n, m))
    - delay

背后逻辑:
    下跌概率平均，越接近1代表持续下跌概率越大。

适用场景:
    短期均值回复选股。

变种与优化:
    - 调整窗口 5
    - 调整SMA权重

注意事项:
    - 前 5 期返回 NaN (delay 1 + sma 5)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_135"]

DIRECTION = -1


def alpha_135(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #135: SMA 平滑价格比。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)
    indicator = (close < prev_close).astype(float)
    # NaN 保护: prev_close 为 NaN 时(idx 0) indicator 也应为 NaN
    mask = prev_close.notna()
    indicator = indicator.where(mask)
    return sma(indicator, 5, 1) - 0.5

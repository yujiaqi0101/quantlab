"""
Alpha191 #109 — 振幅RSI
========================================

公式:
    SMA(H-L, 10, 2) / SMA(SMA(H-L, 10, 2), 10, 2)

公式解释:
    计算10日振幅（H-L）的SMA除以其再10日SMA，即振幅的RSI形式。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    该因子将 RSI 的逻辑应用于振幅而非价格。分子为当前振幅平滑值，
    分母为其再平滑值。比值大于1表示振幅在扩大，小于1表示振幅在缩小。
    正向选择偏好振幅扩大的标的。

适用场景:
    振幅变化策略，偏好波动率扩张的标的。

变种与优化:
    - 可调整窗口期 (10 → 5/20)
    - 调整 SMA 参数 (m/n)
    - 使用不同的振幅定义 (TR/收盘价标准差)

注意事项:
    - 振幅 RSI 的解读与价格 RSI 不同，比值围绕 1 波动
    - 分母接近0时因子值会异常放大
    - 前 20 期数据不足时返回 NaN (双层 SMA 预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_109"]

DIRECTION = 1
DEFAULT_N = 10
DEFAULT_M = 2


def alpha_109(
    ctx: FactorContext,
    n: int = DEFAULT_N,
    m: int = DEFAULT_M,
) -> pd.DataFrame:
    """Alpha191 #109: 振幅RSI。

    公式: SMA(H-L, n, m) / SMA(SMA(H-L, n, m), n, m)

    Args:
        ctx: 因子数据上下文
        n: SMA 窗口期 (默认 10)
        m: SMA 分子参数 (默认 2)

    Returns:
        振幅RSI因子面板 (date × symbol)
    """
    amplitude = ctx.high - ctx.low
    smoothed = sma(amplitude, n, m)
    double_smoothed = sma(smoothed, n, m)
    # 分母保护：振幅接近0时置 NaN，避免除零产生 inf
    safe_denom = double_smoothed.where(double_smoothed.abs() > 0, np.nan)
    return smoothed / safe_denom

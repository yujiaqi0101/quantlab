"""
Alpha191 #109 — 振幅RSI
========================================

公式:
    SMA(H - L, 10, 2) / SMA(SMA(H - L, 10, 2), 10, 2)

公式解释:
    计算10日振幅（H-L）的SMA除以其再10日SMA，
    即振幅的RSI形式。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - sma (指数平滑)

背后逻辑:
    将RSI的逻辑应用于振幅而非价格。
    高值表示振幅在扩大，低值表示振幅在缩小。
    正向选择偏好振幅扩大的股票。

适用场景:
    振幅变化策略。

变种与优化:
    - 可调整窗口期 (10 → 20)
    - 使用不同的振幅定义 (如 TR)
    - 结合价格趋势使用

注意事项:
    - 振幅RSI的解读与价格RSI不同
    - ewm 从首期开始计算, 无 NaN 预热
    - 分母为 0 时返回 NaN
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
    ctx: FactorContext, n: int = DEFAULT_N, m: int = DEFAULT_M
) -> pd.DataFrame:
    """Alpha191 #109: 振幅RSI。

    公式: SMA(H - L, n, m) / SMA(SMA(H - L, n, m), n, m)

    Args:
        ctx: 因子数据上下文
        n: SMA 分母参数 (默认 10)
        m: SMA 分子参数 (默认 2)

    Returns:
        振幅RSI因子面板 (date × symbol)
    """
    amplitude = ctx.high - ctx.low
    sma1 = sma(amplitude, n, m)
    sma2 = sma(sma1, n, m)
    # 分母为 0 时返回 NaN
    safe_sma2 = sma2.where(sma2 > 0, np.nan)
    return sma1 / safe_sma2

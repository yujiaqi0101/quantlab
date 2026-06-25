"""
Alpha191 #111 — A/D线MACD
========================================

公式:
    SMA(A/D, 11, 2) - SMA(A/D, 4, 2)

公式解释:
    计算累积/派发线（A/D Line）的11日SMA减去4日SMA，
    即 A/D 线的 MACD。

    A/D Line 定义:
        A/D = ((CLOSE - LOW) - (HIGH - CLOSE)) / (HIGH - LOW) * VOLUME
            = (2*CLOSE - HIGH - LOW) / (HIGH - LOW) * VOLUME

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - sma (指数平滑)

背后逻辑:
    A/D Line 衡量了量价累积关系，
    其 MACD 形式捕捉了量价累积趋势的变化。
    正值表示量价累积趋势向上。

适用场景:
    量价累积趋势策略。

变种与优化:
    - 可调整 MACD 参数 (11/4 → 12/26)
    - 使用不同的 A/D 计算方式
    - 加入 DEA 信号线

注意事项:
    - A/D Line 的计算需要完整的 OHLCV 数据
    - (HIGH - LOW) 为 0 时 A/D 返回 NaN
    - ewm 从首期开始计算, 无 NaN 预热
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_111"]

DIRECTION = 1
DEFAULT_LONG = 11
DEFAULT_SHORT = 4
DEFAULT_M = 2


def alpha_111(
    ctx: FactorContext,
    long_n: int = DEFAULT_LONG,
    short_n: int = DEFAULT_SHORT,
    m: int = DEFAULT_M,
) -> pd.DataFrame:
    """Alpha191 #111: A/D线MACD。

    公式: SMA(A/D, long_n, m) - SMA(A/D, short_n, m)

    Args:
        ctx: 因子数据上下文
        long_n: 长期SMA窗口 (默认 11)
        short_n: 短期SMA窗口 (默认 4)
        m: SMA 分子参数 (默认 2)

    Returns:
        A/D线MACD因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    close = ctx.close
    volume = ctx.volume
    # A/D Line = (2*CLOSE - HIGH - LOW) / (HIGH - LOW) * VOLUME
    hl = high - low
    safe_hl = hl.where(hl > 0, np.nan)
    ad = (2.0 * close - high - low) / safe_hl * volume
    sma_long = sma(ad, long_n, m)
    sma_short = sma(ad, short_n, m)
    return sma_long - sma_short

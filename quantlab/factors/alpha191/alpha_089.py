"""
Alpha191 #89 — MACD柱
========================================

公式:
    2 * (SMA(CLOSE, 13, 2) - SMA(CLOSE, 27, 2)
          - SMA(SMA(CLOSE, 13, 2) - SMA(CLOSE, 27, 2), 10, 2))

公式解释:
    计算13日SMA减去27日SMA的差值（DIF），
    再减去 DIF 的10日SMA（DEA），乘以2得到MACD柱。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - sma (指数平滑)

背后逻辑:
    MACD 是最经典的技术指标之一。
    MACD柱衡量了短期和长期趋势的收敛/发散程度。
    正值表示短期趋势强于长期趋势。

适用场景:
    趋势跟踪策略。

变种与优化:
    - 可调整MACD参数 (13/27/10 → 12/26/9)
    - 结合信号线交叉使用
    - 加入成交量确认

注意事项:
    - MACD在震荡市中容易产生虚假信号
    - 存在滞后性
    - ewm 从首期开始计算, 无 NaN 预热
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_089"]

DIRECTION = 1
DEFAULT_SHORT = 13
DEFAULT_LONG = 27
DEFAULT_SIGNAL = 10
DEFAULT_M = 2


def alpha_089(
    ctx: FactorContext,
    short: int = DEFAULT_SHORT,
    long: int = DEFAULT_LONG,
    signal: int = DEFAULT_SIGNAL,
    m: int = DEFAULT_M,
) -> pd.DataFrame:
    """Alpha191 #89: MACD柱。

    公式: 2 * (DIF - DEA)
        DIF = SMA(CLOSE, short, m) - SMA(CLOSE, long, m)
        DEA = SMA(DIF, signal, m)

    Args:
        ctx: 因子数据上下文
        short: 短期SMA窗口 (默认 13)
        long: 长期SMA窗口 (默认 27)
        signal: 信号线SMA窗口 (默认 10)
        m: SMA 分子参数 (默认 2)

    Returns:
        MACD柱因子面板 (date × symbol)
    """
    close = ctx.close
    sma_short = sma(close, short, m)
    sma_long = sma(close, long, m)
    dif = sma_short - sma_long
    dea = sma(dif, signal, m)
    return 2.0 * (dif - dea)

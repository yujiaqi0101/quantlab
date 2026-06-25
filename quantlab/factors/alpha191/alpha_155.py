"""
Alpha191 #155 — 成交量MACD
========================================

公式:
    SMA(VOL, 13, 2) - SMA(VOL, 27, 2)
    - SMA(SMA(VOL, 13, 2) - SMA(VOL, 27, 2), 10, 2)

公式解释:
    计算成交量13日SMA减去27日SMA的差值（DIF），
    再减去 DIF 的10日SMA（DEA），
    即成交量的 MACD 柱。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - sma (指数平滑)

背后逻辑:
    与 Alpha89 类似但应用于成交量。
    成交量MACD衡量了短期和长期成交量趋势的
    收敛/发散程度。

适用场景:
    成交量趋势策略。

变种与优化:
    - 可调整 MACD 参数 (13/27/10 → 12/26/9)
    - 使用成交额替代成交量
    - 加入零轴交叉信号

注意事项:
    - 成交量MACD的解读与价格MACD类似
    - ewm 从首期开始计算, 无 NaN 预热
    - 建议结合价格趋势使用
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_155"]

DIRECTION = 1
DEFAULT_SHORT = 13
DEFAULT_LONG = 27
DEFAULT_SIGNAL = 10
DEFAULT_M = 2


def alpha_155(
    ctx: FactorContext,
    short: int = DEFAULT_SHORT,
    long: int = DEFAULT_LONG,
    signal: int = DEFAULT_SIGNAL,
    m: int = DEFAULT_M,
) -> pd.DataFrame:
    """Alpha191 #155: 成交量MACD。

    公式: DIF - DEA
        DIF = SMA(VOL, short, m) - SMA(VOL, long, m)
        DEA = SMA(DIF, signal, m)

    Args:
        ctx: 因子数据上下文
        short: 短期SMA窗口 (默认 13)
        long: 长期SMA窗口 (默认 27)
        signal: 信号线SMA窗口 (默认 10)
        m: SMA 分子参数 (默认 2)

    Returns:
        成交量MACD柱因子面板 (date × symbol)
    """
    vol = ctx.volume
    sma_short = sma(vol, short, m)
    sma_long = sma(vol, long, m)
    dif = sma_short - sma_long
    dea = sma(dif, signal, m)
    return dif - dea

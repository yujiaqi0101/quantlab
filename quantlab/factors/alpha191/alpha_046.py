"""
Alpha191 #46 — BBI多均线均值回复
========================================

公式:
    (MA3 + MA6 + MA12 + MA24) / (4 * CLOSE)

公式解释:
    计算3日、6日、12日、24日均线之和除以4倍收盘价。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    该因子是 BBI（Bull and Bear Index）的变体。当多条均线高于收盘价时，
    因子值大于1，表示价格低于多条均线（超卖）。反向选择偏好因子值大的股票。

适用场景:
    多周期均值回复策略。

变种与优化:
    - 可调整均线周期组合
    - 使用不同的均线类型 (EMA、WMA)
    - 加权平均替代简单平均

注意事项:
    - 多条均线简单平均可能不是最优组合
    - 需优化权重
    - 前 23 期数据不足时返回 NaN (受24日均线约束)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_046"]

DIRECTION = -1
DEFAULT_MA3 = 3
DEFAULT_MA6 = 6
DEFAULT_MA12 = 12
DEFAULT_MA24 = 24


def alpha_046(
    ctx: FactorContext,
    ma3: int = DEFAULT_MA3,
    ma6: int = DEFAULT_MA6,
    ma12: int = DEFAULT_MA12,
    ma24: int = DEFAULT_MA24,
) -> pd.DataFrame:
    """Alpha191 #46: BBI多均线均值回复。

    公式: (MA(CLOSE,ma3)+MA(CLOSE,ma6)+MA(CLOSE,ma12)+MA(CLOSE,ma24)) / (4*CLOSE)

    Args:
        ctx: 因子数据上下文
        ma3: 短期均线窗口期 (默认 3)
        ma6: 中短期均线窗口期 (默认 6)
        ma12: 中期均线窗口期 (默认 12)
        ma24: 长期均线窗口期 (默认 24)

    Returns:
        BBI 因子面板 (date × symbol)
    """
    close = ctx.close
    return (
        ts_mean(close, ma3)
        + ts_mean(close, ma6)
        + ts_mean(close, ma12)
        + ts_mean(close, ma24)
    ) / (4.0 * close)

"""
Alpha191 #27 — 3/6日复合动量WMA平滑
========================================

公式:
    WMA((CLOSE-DELAY(CLOSE,3))/DELAY(CLOSE,3)*100
        + (CLOSE-DELAY(CLOSE,6))/DELAY(CLOSE,6)*100, 12)

公式解释:
    计算3日和6日收益率的加权和，然后进行12日加权移动平均。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay
    - wma (线性加权移动平均)

背后逻辑:
    将短期（3日）和中期（6日）动量信号等权相加，再通过 WMA 平滑。
    WMA 给予近期数据更高权重，能更快响应动量变化。

适用场景:
    多周期动量策略。

变种与优化:
    - 可调整各窗口期 (3/6 → 5/10)
    - 使用不同的平滑方式 (decay_linear/sma)
    - 对短期/中期动量赋不同权重

注意事项:
    - 多窗口期动量简单相加可能非最优组合
    - 需优化权重分配
    - 前 6 期数据不足时返回 NaN（受6日动量预热约束）
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import wma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_027"]

DIRECTION = 1
DEFAULT_SHORT_PERIOD = 3
DEFAULT_LONG_PERIOD = 6
DEFAULT_WMA_PERIOD = 12


def alpha_027(
    ctx: FactorContext,
    short_period: int = DEFAULT_SHORT_PERIOD,
    long_period: int = DEFAULT_LONG_PERIOD,
    wma_period: int = DEFAULT_WMA_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #27: 3/6日复合动量WMA平滑。

    公式: WMA(RET_3*100 + RET_6*100, wma_period)

    Args:
        ctx: 因子数据上下文
        short_period: 短期动量窗口期 (默认 3)
        long_period: 长期动量窗口期 (默认 6)
        wma_period: WMA 平滑窗口期 (默认 12)

    Returns:
        复合动量因子面板 (date × symbol)
    """
    close = ctx.close
    ret3 = (close - delay(close, short_period)) / delay(close, short_period) * 100
    ret6 = (close - delay(close, long_period)) / delay(close, long_period) * 100
    combined = ret3 + ret6
    return wma(combined, wma_period)

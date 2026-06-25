"""
Alpha191 #24 — 5日动量SMA平滑
========================================

公式:
    SMA(CLOSE - DELAY(CLOSE, 5), 5, 1)

公式解释:
    计算5日价格变动（收盘价减去5日前收盘价），然后进行5日SMA平滑。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    在 Alpha14 (5日动量) 基础上增加 SMA 平滑，减少日间噪声。
    平滑后的动量信号更加稳定，适合捕捉中期趋势。

适用场景:
    中期动量策略。

变种与优化:
    - 可调整动量窗口期（5日 → 10日/20日）
    - 调整 SMA 平滑参数 (n, m)
    - 使用 WMA 或 decay_linear 替代 SMA

注意事项:
    - SMA 平滑会引入滞后
    - 双重窗口期选择需优化
    - 前 5 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_024"]

DIRECTION = 1
DEFAULT_PERIOD = 5
DEFAULT_SMA_N = 5
DEFAULT_SMA_M = 1


def alpha_024(
    ctx: FactorContext,
    period: int = DEFAULT_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #24: 5日动量SMA平滑。

    公式: SMA(CLOSE - DELAY(CLOSE, period), sma_n, sma_m)

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 5)
        sma_n: SMA 分母参数 (默认 5)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        平滑动量因子面板 (date × symbol)，前 period 期为 NaN
    """
    momentum = ctx.close - delay(ctx.close, period)
    return sma(momentum, sma_n, sma_m)

"""
Alpha191 #82 — 1-RSV的20日SMA
========================================

公式:
    SMA(1 - RSV, 20, 1)

    其中 RSV = (CLOSE - LLV(LOW,9)) / (HHV(HIGH,9) - LLV(LOW,9))

公式解释:
    计算1减RSV的20日SMA。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、HIGH 最高价、LOW 最低价（日频，后复权）

算子依赖:
    - ts_max (HHV)
    - ts_min (LLV)
    - sma (指数平滑)

背后逻辑:
    与 Alpha72 类似但使用20日窗口期。更长的平滑期使信号更稳定，
    反映中期超卖程度。

适用场景:
    中期均值回复策略。

变种与优化:
    - 可调整 RSV 和 SMA 窗口期
    - 结合其他超卖指标
    - 与 Alpha72 组合使用

注意事项:
    - 与 Alpha72 逻辑相同，仅参数不同
    - 文档未明确 RSV 窗口期，此处采用 KDJ 标准 9 日
    - 前 8 期数据不足时返回 NaN (RSV 预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import ts_max, ts_min

__all__ = ["alpha_082"]

DIRECTION = -1
DEFAULT_RSV_PERIOD = 9
DEFAULT_SMA_N = 20
DEFAULT_SMA_M = 1


def alpha_082(
    ctx: FactorContext,
    rsv_period: int = DEFAULT_RSV_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #82: 1-RSV的20日SMA。

    公式: SMA(1 - RSV, sma_n, sma_m)
          RSV = (CLOSE-LLV(LOW,rsv_period))/(HHV(HIGH,rsv_period)-LLV(LOW,rsv_period))

    Args:
        ctx: 因子数据上下文
        rsv_period: RSV 高低点窗口期 (默认 9)
        sma_n: SMA 分母参数 (默认 20)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        超卖反弹因子面板 (date × symbol)
    """
    close = ctx.close
    llv = ts_min(ctx.low, rsv_period)
    hhv = ts_max(ctx.high, rsv_period)
    rng = (hhv - llv).replace(0, np.nan)
    rsv = (close - llv) / rng
    return sma(1.0 - rsv, sma_n, sma_m)

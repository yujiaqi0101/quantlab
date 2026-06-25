"""
Alpha191 #68 — 中间价加速度量价效率SMA
========================================

公式:
    SMA(中间价加速度 × 振幅 / VOLUME, 15, 2)

公式解释:
    计算中间价加速度乘以振幅除以成交量，然后进行15日SMA平滑
    （alpha=2/15）。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价、LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delta
    - sma

背后逻辑:
    中间价加速度衡量价格变化的变化率（二阶差分），乘以振幅得到加权后的
    加速度，除以成交量标准化。该因子衡量单位成交量驱动的价格加速度。

适用场景:
    价格效率选股策略，偏好单位成交量能驱动更大价格加速度的股票。

变种与优化:
    - 可调整窗口期和SMA参数 (15/2)
    - 使用不同的价格基准 (CLOSE vs (H+L)/2)
    - 加入成交额替代成交量

注意事项:
    - 加速度的计算可能引入额外噪声
    - 需对成交量做下限处理
    - 前 15 期数据不足时返回 NaN (sma 预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_068"]

DIRECTION = 1
DEFAULT_SMA_N = 15
DEFAULT_SMA_M = 2


def alpha_068(
    ctx: FactorContext,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #68: 中间价加速度量价效率SMA。

    公式: SMA(DELTA(DELTA((HIGH+LOW)/2, 1), 1) * (HIGH-LOW) / VOLUME, sma_n, sma_m)

    Args:
        ctx: 因子数据上下文
        sma_n: SMA 分母参数 (默认 15)
        sma_m: SMA 分子参数 (默认 2)

    Returns:
        量价效率因子面板 (date × symbol)
    """
    mid = (ctx.high + ctx.low) / 2.0
    accel = delta(delta(mid, 1), 1)
    amplitude = ctx.high - ctx.low
    vol = ctx.volume.replace(0, np.nan)
    raw = accel * amplitude / vol
    return sma(raw, sma_n, sma_m)

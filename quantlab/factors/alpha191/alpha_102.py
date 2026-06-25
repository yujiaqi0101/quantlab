"""
Alpha191 #102 — 6日成交量RSI
========================================

公式:
    SMA(MAX(dV,0),6,1) / SMA(|dV|,6,1) * 100 — 成交量RSI

公式解释:
    计算成交量变化量中正值部分的6日SMA除以绝对变化量的6日SMA乘以100，
    即成交量RSI。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - delta
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    与价格 RSI 类似，但应用于成交量变化。成交量 RSI 衡量了放量与缩量的
    相对强度。高值表示近期放量占主导，正向选择偏好近期放量的标的。

适用场景:
    成交量动量策略，偏好放量标的。

变种与优化:
    - 可调整窗口期 (6 → 12/24)
    - 结合超买超卖区间使用
    - 使用成交额 RSI 替代

注意事项:
    - 成交量变化可能比价格变化更不稳定
    - SMA(dV) 分母为 0 时因子值置 NaN
    - 前 7 期数据不足时返回 NaN (delta 1 + SMA 6 预热)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_102"]

DIRECTION = 1
DEFAULT_N = 6
DEFAULT_M = 1


def alpha_102(
    ctx: FactorContext,
    n: int = DEFAULT_N,
    m: int = DEFAULT_M,
) -> pd.DataFrame:
    """Alpha191 #102: 6日成交量RSI。

    公式: SMA(MAX(dV,0),n,m) / SMA(|dV|,n,m) * 100
        其中 dV = delta(VOLUME, 1)

    Args:
        ctx: 因子数据上下文
        n: SMA 窗口期 (默认 6)
        m: SMA 分子参数 (默认 1)

    Returns:
        成交量RSI因子面板 (date × symbol)，值域 [0, 100]
    """
    dv = delta(ctx.volume, 1)
    up_dv = dv.where(dv > 0, 0.0)
    abs_dv = dv.abs()
    avg_up = sma(up_dv, n, m)
    avg_abs = sma(abs_dv, n, m)
    rs = avg_up / avg_abs
    rs = rs.replace([np.inf, -np.inf], np.nan)
    return rs * 100.0

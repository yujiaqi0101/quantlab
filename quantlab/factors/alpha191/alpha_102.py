"""
Alpha191 #102 — 成交量RSI
========================================

公式:
    SMA(MAX(dV, 0), 6, 1) / SMA(|dV|, 6, 1) * 100

公式解释:
    计算成交量变化量中正值部分的6日SMA除以
    绝对变化量的6日SMA乘以100，即成交量RSI。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - delta (1日差分, 得到 dV)
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    与价格RSI类似，但应用于成交量变化。
    成交量RSI衡量了放量与缩量的相对强度。
    高值表示近期放量占主导。

适用场景:
    成交量动量策略。

变种与优化:
    - 可调整窗口期 (6 → 14)
    - 结合超买超卖区间使用
    - 加入价格RSI交叉确认

注意事项:
    - 成交量变化可能比价格变化更不稳定
    - delta(1) 预热 1 期, sma 从首个非NaN开始
    - 分母为 0 时返回 NaN
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
    ctx: FactorContext, n: int = DEFAULT_N, m: int = DEFAULT_M
) -> pd.DataFrame:
    """Alpha191 #102: 成交量RSI。

    公式: SMA(MAX(dV, 0), n, m) / SMA(|dV|, n, m) * 100

    Args:
        ctx: 因子数据上下文
        n: SMA 分母参数 (默认 6)
        m: SMA 分子参数 (默认 1)

    Returns:
        成交量RSI因子面板 (date × symbol)
    """
    dv = delta(ctx.volume, 1)
    up = dv.where(dv > 0, 0.0)
    abs_dv = dv.abs()
    sma_up = sma(up, n, m)
    sma_abs = sma(abs_dv, n, m)
    # 分母为 0 时返回 NaN
    safe_abs = sma_abs.where(sma_abs > 0, np.nan)
    return sma_up / safe_abs * 100.0

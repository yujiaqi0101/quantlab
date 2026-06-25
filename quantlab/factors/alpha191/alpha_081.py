"""
Alpha191 #81 — 21日SMA平滑成交量
========================================

公式:
    SMA(VOLUME, 21, 2)

公式解释:
    计算成交量的21日SMA平滑（alpha=2/21）。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - sma (指数平滑, alpha=m/n)

背后逻辑:
    直接使用平滑后的成交量水平作为选股信号。
    大成交量表示市场关注度高，流动性好。

适用场景:
    流动性/关注度选股策略。

变种与优化:
    - 可调整SMA参数 (21/2 → 20/1)
    - 使用不同的平滑方法 (如 ts_mean)
    - 做截面标准化处理

注意事项:
    - 成交量水平受股票规模影响较大
    - ewm 从首期开始计算, 无 NaN 预热
    - 建议做截面标准化或对数变换
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_081"]

DIRECTION = 1
DEFAULT_N = 21
DEFAULT_M = 2


def alpha_081(
    ctx: FactorContext, n: int = DEFAULT_N, m: int = DEFAULT_M
) -> pd.DataFrame:
    """Alpha191 #81: 21日SMA平滑成交量。

    公式: SMA(VOLUME, n, m)

    Args:
        ctx: 因子数据上下文
        n: SMA 分母参数 (默认 21)
        m: SMA 分子参数 (默认 2)

    Returns:
        平滑成交量因子面板 (date × symbol)
    """
    return sma(ctx.volume, n, m)

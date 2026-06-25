"""
Alpha191 #189 — 6日绝对偏差均值 (MAD)
========================================

公式:
    MEAN(ABS(CLOSE - MA6), 6)

公式解释:
    计算收盘价与6日均线绝对偏差的6日均值，
    即 MAD (Mean Absolute Deviation)。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean (MA6, MAD 均值)

背后逻辑:
    MAD 是稳健的波动率度量，对异常值不敏感。
    高 MAD 表示价格偏离均线幅度大，波动剧烈。

适用场景:
    稳健波动率策略，对异常值不敏感的波动率度量。

变种与优化:
    - 可调整窗口期 (6 → 其他)
    - 使用不同的均值计算方式 (如 EMA)
    - 与标准差对比使用

注意事项:
    - MAD 比标准差更稳健，但信息含量可能较低
    - 前 11 期返回 NaN (MA6 + mean6 - 1 重叠)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_189"]

DIRECTION = 1


def alpha_189(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #189: 6日绝对偏差均值 (MAD)。

    公式: MEAN(ABS(CLOSE - MA6), 6)

    Args:
        ctx: 因子数据上下文

    Returns:
        MAD 因子面板 (date × symbol)
    """
    close = ctx.close
    ma6 = ts_mean(close, 6)
    abs_dev = (close - ma6).abs()
    return ts_mean(abs_dev, 6)

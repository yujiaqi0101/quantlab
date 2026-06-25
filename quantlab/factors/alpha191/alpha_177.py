"""
Alpha191 #177 — 价格20日均值偏差比率
========================================

公式:
    (20日MAX(CLOSE))^1.5 / ((CLOSE - 20日MEAN(CLOSE))^2 + 0.001)

公式解释:
    分子: 20日最高收盘价的1.5次幂
    分母: 当日收盘价与20日均值之差的平方 + 0.001
    结果: 分子 / 分母

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - ts_max
    - ts_mean

背后逻辑:
    通过价格极值与均值偏差平方的比率衡量结构。

适用场景:
    均值回复策略。

变种与优化:
    - 调整窗口 20
    - 调整幂次 1.5

注意事项:
    - 分母为 0 时返回 NaN (0.001 防止)
    - 前 19 期返回 NaN (ts_max/ts_mean 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_max, ts_mean

__all__ = ["alpha_177"]

DIRECTION = 1


def alpha_177(ctx: FactorContext, period: int = 20) -> pd.DataFrame:
    """Alpha191 #177: 价格20日均值偏差比率。

    Args:
        ctx: 因子数据上下文
        period: 窗口期 (默认 20)

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close

    numerator = ts_max(close, period) ** 1.5
    denominator = (close - ts_mean(close, period)) ** 2 + 0.001

    return numerator / denominator

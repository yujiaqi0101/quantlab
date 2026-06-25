"""
Alpha191 #171 — 价格排序条件数
========================================

公式:
    -1 * ((CLOSE - MEAN(CLOSE, 24)) / MEAN(CLOSE, 24)) * 100

公式解释:
    计算 (收盘价 - 24日均值收盘价) / 24日均值收盘价 * 100
    取相反数

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - ts_mean

背后逻辑:
    价格相对均值的偏离百分比的反向。

适用场景:
    均值回复策略。

变种与优化:
    - 调整窗口 24
    - 替换为 z-score

注意事项:
    - 分母为 0 时返回 NaN
    - 前 23 期返回 NaN (ts_mean 24)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_171"]

DIRECTION = -1
DEFAULT_PERIOD = 24


def alpha_171(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #171: 价格排序条件数。

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 24)

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    mean_close = ts_mean(close, period)
    safe_mean = mean_close.where(mean_close.abs() > 0, np.nan)
    return -1.0 * (close - mean_close) / safe_mean * 100.0

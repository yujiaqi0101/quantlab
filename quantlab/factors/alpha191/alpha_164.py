"""
Alpha191 #164 — 价格突破与排名的复合
========================================

公式:
    RANK((-1 * RANK(((HIGH-CLOSE)*VOL)/(HIGH-LOW))) - RANK(DELAY(((CLOSE-LOW)*VOL)/(CLOSE-LOW),1)))

公式解释:
    左项: ((HIGH-CLOSE)*VOL)/(HIGH-LOW) 排名的负数
    右项: ((CLOSE-LOW)*VOL)/(CLOSE-LOW) 延迟1期的排名
    结果: 左 - 右

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW/CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - delay

背后逻辑:
    通过上影线和下影线的成交量加权比率排名差。

适用场景:
    量价结构选股。

变种与优化:
    - 调整延迟窗口
    - 加入SMA平滑

注意事项:
    - 分母为 0 时返回 NaN
    - 前 1 期返回 NaN (delay 1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_164"]

DIRECTION = 1


def alpha_164(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #164: 价格突破与排名的复合。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    close = ctx.close
    vol = ctx.volume

    upper = (high - close) * vol
    denom_upper = (high - low).where((high - low).abs() > 0, np.nan)
    upper_ratio = upper / denom_upper

    lower = (close - low) * vol
    denom_lower = (close - low).where((close - low).abs() > 0, np.nan)
    lower_ratio = lower / denom_lower

    left = -1.0 * rank(upper_ratio)
    right = rank(delay(lower_ratio, 1))

    return left - right

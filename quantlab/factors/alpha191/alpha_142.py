"""
Alpha191 #142 — 20日反转: 收益反向再排名
========================================

公式:
    (CLOSE>DELAY(CLOSE,1)) ? 1 : ((CLOSE<DELAY(CLOSE,1)) ? -1 : 0)

公式解释:
    如果当日收盘价 > 前日收盘价 → 1
    如果当日收盘价 < 前日收盘价 → -1
    否则 → 0

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    当日涨跌方向的离散信号。

适用场景:
    短期动量策略。

变种与优化:
    - 加入累积窗口
    - 替换为相对阈值

注意事项:
    - 前 1 期返回 NaN (delay 1)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_142"]

DIRECTION = 1


def alpha_142(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #142: 20日反转。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)

    up = close > prev_close
    down = close < prev_close

    result = np.where(up, 1.0, np.where(down, -1.0, 0.0))
    out = pd.DataFrame(result, index=close.index, columns=close.columns)
    mask = prev_close.notna()
    return out.where(mask)

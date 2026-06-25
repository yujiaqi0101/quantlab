"""
Alpha191 #159 — 量价相关性与价格变化的反向排名差
========================================

公式:
    (CLOSE<DELAY(CLOSE,1)) ? 1 : ((CLOSE>DELAY(CLOSE,1)) ? -1 : 0)

公式解释:
    当 收盘价 < 前一日收盘价 → 1
    当 收盘价 > 前一日收盘价 → -1
    否则 → 0

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好 (与 #142 相反)

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    当日涨跌方向的反向离散信号（短期反转）。

适用场景:
    短期反转策略。

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

__all__ = ["alpha_159"]

DIRECTION = -1


def alpha_159(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #159: 量价相关性与价格变化的反向排名差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)

    down = close < prev_close
    up = close > prev_close

    result = np.where(down, 1.0, np.where(up, -1.0, 0.0))
    out = pd.DataFrame(result, index=close.index, columns=close.columns)
    mask = prev_close.notna()
    return out.where(mask)

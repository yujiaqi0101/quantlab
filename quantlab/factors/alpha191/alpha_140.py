"""
Alpha191 #140 — 5日最小值10日时序排名与5日最大值20日时序排名的最小值
========================================

公式:
    MIN(RANK(TSMIN(LOW,5)), RANK(TSMAX(HIGH,5)))

公式解释:
    左侧: 5日最低价的截面排名
    右侧: 5日最高价的截面排名
    结果: 取二者较小者

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW（日频，后复权）

算子依赖:
    - rank
    - ts_min
    - ts_max

背后逻辑:
    通过高低点的截面排名最小值，识别价格相对位置。

适用场景:
    价格动量选股。

变种与优化:
    - 调整窗口 5
    - 替换为 ts_mean

注意事项:
    - 前 4 期返回 NaN (ts_min/ts_max 5)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_max, ts_min

__all__ = ["alpha_140"]

DIRECTION = 1


def alpha_140(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #140: 5日最小值与5日最大值排名的最小值。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    left = rank(ts_min(ctx.low, 5))
    right = rank(ts_max(ctx.high, 5))

    # NaN 保护: 任一为 NaN 时取另一侧
    mask = left.notna() & right.notna()
    out = np.minimum(left, right)
    return out.where(mask)

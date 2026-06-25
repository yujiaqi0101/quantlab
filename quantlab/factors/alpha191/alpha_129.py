"""
Alpha191 #129 — VWAP排名累积时序相关性
========================================

公式:
    SUM(RANK(RANK(CORR((CLOSE - MIN(CLOSE,20)), MAX(CLOSE,20), 10))), 10) / 10

公式解释:
    内层:
    - (close - ts_min(close, 20))
    - ts_max(close, 20)
    - 二者的10日相关性
    - 双重截面排名
    外层: 10日累积 / 10

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - rank
    - ts_min
    - ts_max
    - corr
    - ts_sum

背后逻辑:
    价格相对20日最低/最高的相关性的双重排名累积。

适用场景:
    价格动量选股。

变种与优化:
    - 调整窗口 20/10

注意事项:
    - 分母为 0 时返回 NaN
    - 前 29 期返回 NaN (ts_min 20 + corr 10)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_max, ts_min, ts_sum

__all__ = ["alpha_129"]

DIRECTION = 1


def alpha_129(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #129: VWAP排名累积时序相关性。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close

    inner = rank(rank(corr(close - ts_min(close, 20), ts_max(close, 20), 10)))
    return ts_sum(inner, 10) / 10.0

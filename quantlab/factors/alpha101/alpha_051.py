"""
Alpha101 #51 — 最低价时序排名极值
========================================

公式:
    -1 * ts_min(rank(low), 9)

公式解释:
    最低价的截面排名的 9 日时序最小值，取负。
    与 Alpha#4 类似但使用 ts_min 而非 ts_rank。

分类:
    最低价时序排名极值 (low_rank_timeseries_min)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - LOW 最低价（日频，后复权）

算子依赖:
    - rank (截面)
    - ts_min

背后逻辑:
    rank(low) 反映当日最低价的截面相对位置。
    ts_min(rank(low), 9) 取 9 日内最低排名 (即最低价相对最低的日子)。
    取负后，当近期最低价排名有极小值时因子值大 → 看多 (低价股反转)。

适用场景:
    短期反转策略，捕捉低价股排名极值的反转机会。

变种与优化:
    - 可使用 ts_max 构建范围因子
    - 可调整窗口 (9 → 5/20)
    - 可结合 ts_rank (#4) 形成组合

注意事项:
    - ts_min 对异常值敏感
    - 前 9 期返回 NaN (ts_min)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_min

__all__ = ["alpha_051"]

DIRECTION = -1


def alpha_051(ctx: FactorContext, period: int = 9) -> pd.DataFrame:
    """Alpha101 #51: 最低价时序排名极值。

    公式: -1 * ts_min(rank(low), period)

    Args:
        ctx: 因子数据上下文
        period: 时序窗口 (默认 9)

    Returns:
        最低价时序排名极值因子面板 (date × symbol)
    """
    return -1 * ts_min(rank(ctx.low), period)

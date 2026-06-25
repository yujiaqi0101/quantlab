"""
Alpha101 #44 — 价格-成交量排名相关
========================================

公式:
    -1 * correlation(high, rank(volume), 5)

公式解释:
    最高价与成交量截面排名的 5 日相关系数，取负。
    注意这里只对 volume 做 rank，不对 high 做 rank。

分类:
    价格-成交量排名相关 (price_volume_rank_corr)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - corr

背后逻辑:
    当 high 与 rank(volume) 正相关 (价格上涨伴随成交量排名上升) 时，
    corr 高，取负后看空 (量价齐升见顶)。
    当负相关 (价格上涨但成交量排名下降) 时，看多 (量价背离)。

适用场景:
    量价背离策略，捕捉价格与成交量排名的反向关系。

变种与优化:
    - 可对 high 也做 rank (Spearman 秩相关)
    - 可使用其他价格字段 (close/low/open)
    - 可调整窗口 (5 → 10/20)

注意事项:
    - 仅对 volume 做 rank，high 用原始值，受极端值影响
    - 前 5 期返回 NaN (corr)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr

__all__ = ["alpha_044"]

DIRECTION = -1


def alpha_044(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #44: 价格-成交量排名相关。

    公式: -1 * corr(high, rank(volume), 5)

    Args:
        ctx: 因子数据上下文

    Returns:
        价格-成交量排名相关因子面板 (date × symbol)
    """
    return -1 * corr(ctx.high, rank(ctx.volume), 5)

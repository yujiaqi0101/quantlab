"""
Alpha101 #33 — 日内涨跌幅排名
========================================

公式:
    rank(-1 * ((1 - (open / close))^1))

公式解释:
    1 减去开盘价/收盘价比的负值排名，即 rank(open/close - 1)。
    衡量日内从开盘到收盘的涨跌幅度。

分类:
    日内涨跌幅 (intraday_return)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rank (截面)

背后逻辑:
    日内涨幅 (close > open) 时 open/close < 1，open/close-1 < 0，rank 低，取负后看多；
    日内跌幅 (close < open) 时 open/close > 1，open/close-1 > 0，rank 高，取负后看空。
    即日内上涨的标的看多，日内下跌的标的看空 (动量延续)。

适用场景:
    日内动量延续策略，捕捉开盘到收盘的趋势。

变种与优化:
    - 可引入成交量权重
    - 可结合多日累积涨跌
    - 可使用对数收益替代比率

注意事项:
    - 公式中的 ^1 是恒等变换，无实际影响
    - close 为 0 时需处理除零
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank

__all__ = ["alpha_033"]

DIRECTION = -1


def alpha_033(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #33: 日内涨跌幅排名。

    公式: rank(-1 * (1 - open/close)) = rank(open/close - 1)

    Args:
        ctx: 因子数据上下文

    Returns:
        日内涨跌幅排名因子面板 (date × symbol)
    """
    close_safe = ctx.close.where(ctx.close.abs() > 1e-12)
    return rank(ctx.open / close_safe - 1)

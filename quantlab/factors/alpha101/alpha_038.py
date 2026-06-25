"""
Alpha101 #38 — 价格时序排名-日内比率
========================================

公式:
    -1 * rank(Ts_Rank(close, 10)) * rank(close / open)

公式解释:
    收盘价 10 日时序排名取负，乘以收盘价/开盘价比率的截面排名。
    近期收盘价相对较高且日内涨幅较小时因子值较低。

分类:
    价格时序排名-日内比率 (price_ts_rank_intraday_ratio)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_rank
    - rank (截面)

背后逻辑:
    收盘价时序排名高 (近期相对历史高) 且日内涨幅大 (close/open 大) 时，
    两个 rank 都高，乘积大，取负后看空 (动量反转)。
    反之看多。捕捉价格位置与日内动量的联合反转。

适用场景:
    短期价格反转策略，结合时序位置与日内动量。

变种与优化:
    - 可调整时序窗口 (10 → 5/20)
    - 可使用对数收益替代比率
    - 可引入成交量权重

注意事项:
    - open 为 0 时需处理除零
    - 前 10 期返回 NaN (ts_rank)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_rank

__all__ = ["alpha_038"]

DIRECTION = -1


def alpha_038(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #38: 价格时序排名-日内比率。

    公式: -1 * rank(ts_rank(close, 10)) * rank(close / open)

    Args:
        ctx: 因子数据上下文

    Returns:
        价格时序排名-日内比率因子面板 (date × symbol)
    """
    open_safe = ctx.open.where(ctx.open.abs() > 1e-12)
    return -1 * rank(ts_rank(ctx.close, 10)) * rank(ctx.close / open_safe)

"""
Alpha101 #34 — 波动率比率-价格变化
========================================

公式:
    rank(((1 - rank(stddev(returns, 2) / stddev(returns, 5))) + (1 - rank(delta(close, 1)))))

公式解释:
    两部分之和：
    1. 1 减去 2 日/5 日收益率标准差之比的截面排名；
    2. 1 减去 1 日价格变化的截面排名。
    低短期波动率 (相对长期) 且价格下跌时因子值较高。

分类:
    波动率比率-价格变化 (volatility_ratio_price_change)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - ts_std (stddev)
    - delta
    - rank (截面)

背后逻辑:
    低短期波动率 (相对长期) 意味着市场平稳，价格下跌时可能是买入机会。
    两个维度 (波动率 + 价格变化) 的联合排名，寻找平稳下跌的标的。

适用场景:
    波动率调整后的反转策略，在平稳市场中捕捉价格回归。

变种与优化:
    - 可使用 GARCH 模型替代简单标准差
    - 可引入成交量波动率
    - 可调整波动率窗口 (2/5 → 5/20)

注意事项:
    - 嵌套 rank 使因子分布均匀但丢失幅度信息
    - 前 6 期返回 NaN (returns 1 + ts_std 5)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_std

__all__ = ["alpha_034"]

DIRECTION = 1


def alpha_034(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #34: 波动率比率-价格变化。

    公式: rank((1 - rank(stddev(ret,2)/stddev(ret,5))) + (1 - rank(delta(close,1))))

    Args:
        ctx: 因子数据上下文

    Returns:
        波动率比率-价格变化因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    std2 = ts_std(returns, 2)
    std5 = ts_std(returns, 5)
    std5_safe = std5.where(std5.abs() > 1e-12)
    vol_ratio_rank = rank(std2 / std5_safe)
    price_chg_rank = rank(delta(ctx.close, 1))
    return rank((1 - vol_ratio_rank) + (1 - price_chg_rank))

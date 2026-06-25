"""
Alpha101 #35 — 多因子时序排名
========================================

公式:
    (Ts_Rank(volume, 32) * (1 - Ts_Rank((close + high - low), 16))) * (1 - Ts_Rank(returns, 32))

公式解释:
    三因子乘积：
    1. 成交量 32 日时序排名；
    2. 1 减去 (close+high-low) 的 16 日时序排名；
    3. 1 减去收益率 32 日时序排名。
    高成交量 + 低价格位置 + 低收益时因子值较高。

分类:
    多因子时序排名 (multi_factor_ts_rank)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）
    - RETURNS 日收益率（由 close 派生）

算子依赖:
    - ts_rank

背后逻辑:
    高成交量反映市场关注，
    低价格位置 (close+high-low 低) 反映超卖，
    低收益率反映前期弱势。
    三者叠加捕捉"放量超卖"的反转机会。

适用场景:
    放量超卖反转策略。

变种与优化:
    - 可引入横截面排名
    - 可使用加权乘积
    - 可调整窗口 (32/16 → 20/10)

注意事项:
    - 前 32 期返回 NaN (ts_rank 32)
    - 乘积结构对 NaN 敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_rank

__all__ = ["alpha_035"]

DIRECTION = 1


def alpha_035(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #35: 多因子时序排名。

    公式: Ts_Rank(volume,32) * (1-Ts_Rank(close+high-low,16)) * (1-Ts_Rank(returns,32))

    Args:
        ctx: 因子数据上下文

    Returns:
        多因子时序排名因子面板 (date × symbol)
    """
    returns = ctx.get_returns()
    r1 = ts_rank(ctx.volume, 32)
    r2 = 1 - ts_rank(ctx.close + ctx.high - ctx.low, 16)
    r3 = 1 - ts_rank(returns, 32)
    return r1 * r2 * r3

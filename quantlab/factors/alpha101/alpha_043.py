"""
Alpha101 #43 — 量比-价格反转 (adv20)
========================================

公式:
    ts_rank(volume / adv20, 20) * ts_rank(-1 * delta(close, 7), 8)

公式解释:
    成交量与 20 日均量之比的 20 日时序排名，
    乘以 7 日价格变化负值的 8 日时序排名。
    高量比 + 价格下跌时因子值较大。

分类:
    量比-价格反转 (volume_ratio_price_reversal)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - ADV20 20 日平均成交量（由 volume 派生）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_rank
    - delta
    - ctx.get_adv

背后逻辑:
    量比时序排名高反映近期放量，
    价格下跌时序排名高反映近期下跌，
    两者叠加捕捉"放量下跌"的反转机会。

适用场景:
    放量下跌反转策略。

变种与优化:
    - 可用 amount 替代 volume
    - 可调整窗口 (20/8 → 10/5)
    - 可引入横截面排名

注意事项:
    - 前 27 期返回 NaN (adv20 20 + ts_rank 20 - 重叠 + delta 7)
    - 乘积结构对 NaN 敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta, ts_rank

__all__ = ["alpha_043"]

DIRECTION = 1


def alpha_043(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #43: 量比-价格反转 (adv20)。

    公式: ts_rank(volume/adv20, 20) * ts_rank(-delta(close,7), 8)

    Args:
        ctx: 因子数据上下文

    Returns:
        量比-价格反转因子面板 (date × symbol)
    """
    adv20 = ctx.get_adv(20)
    vol_ratio = ctx.volume / adv20
    return ts_rank(vol_ratio, 20) * ts_rank(-1 * delta(ctx.close, 7), 8)

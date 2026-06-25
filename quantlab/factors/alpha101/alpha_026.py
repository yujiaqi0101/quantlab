"""
Alpha101 #26 — 量价时序相关极值
========================================

公式:
    -1 * ts_max(correlation(ts_rank(volume, 5), ts_rank(high, 5), 5), 3)

公式解释:
    成交量 5 日时序排名与最高价 5 日时序排名的 5 日相关系数，
    取 3 日最大值再取负。

分类:
    量价时序相关 (volume_price_ts_corr)

信号方向:
    反向 (-1) — 因子值越大越看空

数据来源与频率:
    - VOLUME 成交量（日频）
    - HIGH 最高价（日频，后复权）

算子依赖:
    - ts_rank
    - corr
    - ts_max

背后逻辑:
    量价时序排名相关性的极端值代表量价同向/反向运动的最强状态。
    取 3 日最大值捕捉近期最强的量价正相关，
    取负表示量价强正相关时看空 (反转逻辑)。

适用场景:
    量价极端相关反转策略。

变种与优化:
    - 可使用均值替代最大值
    - 可引入其他价格字段 (low/close)
    - 可调整窗口 (5/5/3 → 10/10/5)

注意事项:
    - 前 12 期返回 NaN (ts_rank 5 + corr 5 + ts_max 3 - 重叠)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_max, ts_rank

__all__ = ["alpha_026"]

DIRECTION = -1


def alpha_026(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #26: 量价时序相关极值。

    公式: -1 * ts_max(corr(ts_rank(volume,5), ts_rank(high,5), 5), 3)

    Args:
        ctx: 因子数据上下文

    Returns:
        量价时序相关极值因子面板 (date × symbol)
    """
    c = corr(ts_rank(ctx.volume, 5), ts_rank(ctx.high, 5), 5)
    return -1 * ts_max(c, 3)

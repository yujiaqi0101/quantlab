"""
Alpha101 #15 — 量价相关性-累积
==================================

公式:
    -1 * sum(rank(correlation(rank(high), rank(volume), 3)), 3)

公式解释:
    最高价排名与成交量排名的 3 日相关系数排名，再取 3 日累积和取负。

分类:
    量价相关性-累积 (volume_price_correlation_cumulative)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - rank (截面)
    - corr (滚动相关)
    - ts_sum (滚动求和)

背后逻辑:
    捕捉量价相关性的短期趋势。
    sum(rank(...), 3) 本质上是 3 日移动求和，增加了信号的稳定性。

适用场景:
    适用于检测量价关系的变化趋势。

变种与优化:
    - 可调整两个窗口参数 (3, 3)
    - 可使用指数加权移动平均替代简单求和

注意事项:
    - 前 5 期因 corr(3) + ts_sum(3) 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_015"]

DIRECTION = -1
DEFAULT_CORR_PERIOD = 3
DEFAULT_SUM_PERIOD = 3


def alpha_015(
    ctx: FactorContext,
    corr_period: int = DEFAULT_CORR_PERIOD,
    sum_period: int = DEFAULT_SUM_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #15: 量价相关性-累积。

    公式: -1 * sum(rank(correlation(rank(high), rank(volume), corr_period)), sum_period)

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口 (默认 3)
        sum_period: 累积求和窗口 (默认 3)

    Returns:
        量价相关性-累积因子面板 (date × symbol)
    """
    inner = rank(corr(rank(ctx.high), rank(ctx.volume), corr_period))
    return -1.0 * ts_sum(inner, sum_period)

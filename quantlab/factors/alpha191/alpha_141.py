"""
Alpha191 #141 — 20日最大涨幅的20日时序排名
========================================

公式:
    (RANK(CORR(RANK(HIGH), RANK(MEAN(VOL,15)), 9))^5) / 10

公式解释:
    内层: HIGH排名 与 15日均量排名 的9日相关性
    外层: 相关性排名5次幂除以10

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/VOLUME（日频，后复权）

算子依赖:
    - rank
    - ts_mean
    - corr
    - signed_power

背后逻辑:
    高价与成交量相关性排名的非线性放大。

适用场景:
    量价结构选股。

变种与优化:
    - 调整窗口 15/9
    - 调整幂次 5

注意事项:
    - 前 23 期返回 NaN (ts_mean 15 + corr 9)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_141"]

DIRECTION = 1


def alpha_141(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #141: 20日最大涨幅的20日时序排名。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    corr_val = corr(rank(ctx.high), rank(ts_mean(ctx.volume, 15)), 9)
    return signed_power(rank(corr_val), 5) / 10.0

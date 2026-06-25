"""
Alpha191 #42 — 高价波动率与量价相关复合
========================================

公式:
    (-1 * RANK(STD(HIGH, 10))) * CORR(HIGH, VOLUME, 10)

公式解释:
    计算10日最高价标准差的截面排名的负值，乘以最高价与成交量10日相关系数。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好（低波动+正量价相关）

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_std
    - rank (截面)
    - corr (滚动)

背后逻辑:
    该因子将最高价波动率（取负排名，偏好低波动）与量价相关性相结合。
    当低波动股票呈现正量价相关性时，因子值为正，反映稳定的量价配合。

适用场景:
    低波动量价确认策略。

变种与优化:
    - 可调整窗口期 (10 → 20)
    - 使用不同的波动率度量
    - 加权组合两个子信号

注意事项:
    - 两个子信号量纲不同，需做标准化处理
    - 前 9 期数据不足时返回 NaN (10日标准差/相关)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_042"]

DIRECTION = -1
DEFAULT_PERIOD = 10


def alpha_042(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #42: 高价波动率与量价相关复合。

    公式: (-1 * RANK(STD(HIGH, period))) * CORR(HIGH, VOLUME, period)

    Args:
        ctx: 因子数据上下文
        period: 标准差与相关系数窗口期 (默认 10)

    Returns:
        复合因子面板 (date × symbol)
    """
    vol = -1.0 * rank(ts_std(ctx.high, period))
    vp_corr = corr(ctx.high, ctx.volume, period)
    return vol * vp_corr

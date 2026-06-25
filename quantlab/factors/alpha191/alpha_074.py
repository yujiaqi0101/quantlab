"""
Alpha191 #74 — 双量价相关排名复合
========================================

公式:
    RANK(CORR(加权价, MA(VOLUME,40), 7)) + RANK(CORR(RANK(VWAP), RANK(VOLUME), 6))

公式解释:
    计算加权价与40日成交量均值7日相关系数的截面排名，加上VWAP排名与
    成交量排名6日相关系数的截面排名。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价、LOW 最低价、CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - ts_mean
    - corr
    - rank (截面)

背后逻辑:
    该因子将两个量价相关性信号相加。第一个衡量价格水平与成交量均值的
    关联，第二个衡量VWAP与成交量的排名关联。两者正相关表示量价配合
    良好。

适用场景:
    量价趋势确认策略。

变种与优化:
    - 可调整窗口期 (40/7/6)
    - 使用不同的加权价定义
    - 加权组合两个子信号

注意事项:
    - 两个子信号的相关性需关注
    - 简单相加可能不是最优组合
    - 前 39 期数据不足时返回 NaN (40日量均值最长)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_074"]

DIRECTION = 1
DEFAULT_VOL_PERIOD = 40
DEFAULT_CORR1 = 7
DEFAULT_CORR2 = 6


def alpha_074(
    ctx: FactorContext,
    vol_period: int = DEFAULT_VOL_PERIOD,
    corr1: int = DEFAULT_CORR1,
    corr2: int = DEFAULT_CORR2,
) -> pd.DataFrame:
    """Alpha191 #74: 双量价相关排名复合。

    公式: RANK(CORR((HIGH+LOW+CLOSE)/3, MA(V, vol_period), corr1))
          + RANK(CORR(RANK(VWAP), RANK(V), corr2))

    Args:
        ctx: 因子数据上下文
        vol_period: 成交量均值窗口期 (默认 40)
        corr1: 第一相关窗口期 (默认 7)
        corr2: 第二相关窗口期 (默认 6)

    Returns:
        量价复合因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    weighted_price = (ctx.high + ctx.low + ctx.close) / 3.0
    vol_mean = ts_mean(ctx.volume, vol_period)
    part1 = rank(corr(weighted_price, vol_mean, corr1))
    part2 = rank(corr(rank(vwap), rank(ctx.volume), corr2))
    return part1 + part2

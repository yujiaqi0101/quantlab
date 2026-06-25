"""
Alpha191 #44 — 量价相关衰减与VWAP动量复合
========================================

公式:
    TSRANK(DECAYLINEAR(CORR(LOW, MEAN(VOLUME,10), 7), 6), 4)
    + TSRANK(DECAYLINEAR(DELTA(VWAP, 3), 10), 15)

公式解释:
    计算最低价与10日成交量均值7日相关系数的6日衰减平均的时间序列排名，
    加上VWAP 3日变化量的10日衰减平均的15日时间序列排名。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - ts_mean
    - corr
    - decay_linear
    - delta
    - ts_rank

背后逻辑:
    该因子将量价相关性信号与VWAP动量信号相结合。第一个子因子衡量低价与
    成交量均值的关联度，第二个子因子衡量VWAP的短期趋势。两者相加形成
    综合信号。

适用场景:
    量价趋势跟踪策略。

变种与优化:
    - 可调整各窗口期 (10/7/6/4/3/10/15)
    - 使用不同的价格基准
    - 加权组合两个子信号

注意事项:
    - 多个窗口期参数需要优化
    - 衰减平均的计算可能引入滞后
    - 前 18 期数据不足时返回 NaN (15日 ts_rank 最长)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_mean, ts_rank

__all__ = ["alpha_044"]

DIRECTION = 1
DEFAULT_VOL_PERIOD = 10
DEFAULT_CORR_PERIOD = 7
DEFAULT_DECAY1 = 6
DEFAULT_RANK1 = 4
DEFAULT_DELTA_PERIOD = 3
DEFAULT_DECAY2 = 10
DEFAULT_RANK2 = 15


def alpha_044(
    ctx: FactorContext,
    vol_period: int = DEFAULT_VOL_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
    decay1: int = DEFAULT_DECAY1,
    rank1: int = DEFAULT_RANK1,
    delta_period: int = DEFAULT_DELTA_PERIOD,
    decay2: int = DEFAULT_DECAY2,
    rank2: int = DEFAULT_RANK2,
) -> pd.DataFrame:
    """Alpha191 #44: 量价相关衰减与VWAP动量复合。

    公式: TSRANK(DECAYLINEAR(CORR(LOW, MEAN(V,vol_period), corr_period), decay1), rank1)
          + TSRANK(DECAYLINEAR(DELTA(VWAP, delta_period), decay2), rank2)

    Args:
        ctx: 因子数据上下文
        vol_period: 成交量均值窗口期 (默认 10)
        corr_period: 相关系数窗口期 (默认 7)
        decay1: 第一衰减窗口期 (默认 6)
        rank1: 第一时序排名窗口期 (默认 4)
        delta_period: VWAP变化窗口期 (默认 3)
        decay2: 第二衰减窗口期 (默认 10)
        rank2: 第二时序排名窗口期 (默认 15)

    Returns:
        复合因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    vol_mean = ts_mean(ctx.volume, vol_period)
    vp_corr = corr(ctx.low, vol_mean, corr_period)
    part1 = ts_rank(decay_linear(vp_corr, decay1), rank1)
    vwap_change = delta(vwap, delta_period)
    part2 = ts_rank(decay_linear(vwap_change, decay2), rank2)
    return part1 + part2

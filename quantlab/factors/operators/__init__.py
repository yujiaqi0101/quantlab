"""
算子库 (operators)
==================

统一实现 Alpha191 与 Alpha101 两套文档的算子体系。
命名风格: 小写下划线 (ts_rank)，与 STRATEGY_DEV_GUIDE 因子函数规范一致。

子模块:
    ts.py            — 时序算子 (delay/delta/ts_rank/ts_max/ts_min/ts_argmax/ts_argmin/ts_sum/ts_mean/ts_std/product)
    cross_section.py — 截面算子 (rank/scale/ind_neutralize)
    stats.py         — 统计算子 (corr/cov)
    smooth.py        — 平滑算子 (sma/wma/decay_linear)
    regression.py    — 回归算子 (regbeta)
    misc.py          — 工具算子 (signed_power/sum_if/cumsum/highday/lowday/sequence)

输入输出约定:
    所有算子输入输出均为 pd.DataFrame (index=date, columns=symbol)
    纯函数，无副作用，可组合
"""
from quantlab.factors.operators.ts import (
    delay, delta, ts_rank, ts_max, ts_min, ts_argmax, ts_argmin,
    ts_sum, ts_mean, ts_std, product,
)
from quantlab.factors.operators.cross_section import rank, scale, ind_neutralize
from quantlab.factors.operators.stats import corr, cov
from quantlab.factors.operators.smooth import decay_linear, sma, wma
from quantlab.factors.operators.regression import regbeta
from quantlab.factors.operators.misc import (
    signed_power, sum_if, cumsum, highday, lowday, sequence, tr, sumac,
)

__all__ = [
    # ts
    "delay", "delta", "ts_rank", "ts_max", "ts_min", "ts_argmax",
    "ts_argmin", "ts_sum", "ts_mean", "ts_std", "product",
    # cross_section
    "rank", "scale", "ind_neutralize",
    # stats
    "corr", "cov",
    # smooth
    "decay_linear", "sma", "wma",
    # regression
    "regbeta",
    # misc
    "signed_power", "sum_if", "cumsum", "highday", "lowday", "sequence",
    "tr", "sumac",
]

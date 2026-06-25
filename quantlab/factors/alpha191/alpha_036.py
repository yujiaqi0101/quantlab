"""
Alpha191 #36 — 量价排名相关累积
========================================

公式:
    RANK(SUM(CORR(RANK(VOLUME), RANK(VWAP), 5), 6))

公式解释:
    计算成交量排名与VWAP排名的5日相关系数，求6日和后进行截面排名。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - rank (截面)
    - corr (滚动)
    - ts_sum

背后逻辑:
    该因子衡量量价相关性的累积强度。持续的正相关表示量价齐升或齐跌，
    负相关表示量价背离。正向选择意味着偏好量价关系稳定的股票。

适用场景:
    量价关系分析策略。

变种与优化:
    - 可调整窗口期 (5/6)
    - 使用不同的相关性度量
    - 标准化处理累积和

注意事项:
    - 累积和可能使因子值随时间发散，需做标准化
    - 文档公式 CORR 未明确窗口期，此处取5日
    - 前 10 期数据不足时返回 NaN (5日相关 + 6日累积)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_036"]

DIRECTION = 1
DEFAULT_CORR_PERIOD = 5
DEFAULT_SUM_PERIOD = 6


def alpha_036(
    ctx: FactorContext,
    corr_period: int = DEFAULT_CORR_PERIOD,
    sum_period: int = DEFAULT_SUM_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #36: 量价排名相关累积。

    公式: RANK(SUM(CORR(RANK(VOLUME), RANK(VWAP), corr_period), sum_period))

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口期 (默认 5)
        sum_period: 累积窗口期 (默认 6)

    Returns:
        量价相关累积因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    vol_rank = rank(ctx.volume)
    vwap_rank = rank(vwap)
    return rank(ts_sum(corr(vol_rank, vwap_rank, corr_period), sum_period))

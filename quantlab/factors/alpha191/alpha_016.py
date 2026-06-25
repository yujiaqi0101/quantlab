"""
Alpha191 #16 — 量价截面排名相关性反转
========================================

公式:
    -1 * TSMAX(RANK(CORR(RANK(VOLUME), RANK(VWAP), 5)), 5)

公式解释:
    计算成交量截面排名与VWAP截面排名的5日相关系数的截面排名，
    取5日最大值后取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - rank (截面)
    - corr (滚动)
    - ts_max

背后逻辑:
    该因子衡量量价相关性的极端状态。当成交量排名与VWAP排名高度相关时，
    说明量价齐升或齐跌的趋势明显。取5日最大值捕捉趋势极端，取负值偏好
    趋势减弱的股票。

适用场景:
    量价趋势反转策略。

变种与优化:
    - 可调整各窗口期 (5/5)
    - 使用不同的相关性度量
    - 结合成交额确认

注意事项:
    - RANK 操作会损失绝对值信息
    - 短期相关性可能不稳定
    - 前 9 期数据不足时返回 NaN (5日相关 + 5日最大值)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_max

__all__ = ["alpha_016"]

DIRECTION = -1
DEFAULT_CORR_PERIOD = 5
DEFAULT_MAX_PERIOD = 5


def alpha_016(
    ctx: FactorContext,
    corr_period: int = DEFAULT_CORR_PERIOD,
    max_period: int = DEFAULT_MAX_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #16: 量价截面排名相关性反转。

    公式: -1 * TSMAX(RANK(CORR(RANK(VOLUME), RANK(VWAP), corr_period)), max_period)

    Args:
        ctx: 因子数据上下文
        corr_period: 相关系数窗口期 (默认 5)
        max_period: 最大值窗口期 (默认 5)

    Returns:
        量价反转因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    vol_rank = rank(ctx.volume)
    vwap_rank = rank(vwap)
    return -1.0 * ts_max(rank(corr(vol_rank, vwap_rank, corr_period)), max_period)

"""
Alpha191 #5 — 量价时序排名相关性反转
========================================

公式:
    -1 * TSMAX(CORR(TSRANK(VOLUME, 5), TSRANK(HIGH, 5), 5), 3)

公式解释:
    计算成交量5日时间序列排名与最高价5日时间序列排名的5日相关系数，
    再取3日内的最大值，最后取负值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_rank
    - corr
    - ts_max

背后逻辑:
    当成交量排名与最高价排名高度相关时，说明放量创新高的趋势明显。
    取3日最大值捕捉趋势极端状态，取负值偏好趋势减弱或逆转的信号。

适用场景:
    短期反转策略，在量价趋势过热时寻找反转机会。

变种与优化:
    - 可调整各窗口期参数 (5/5/3)
    - 用 RANK 替代 TSRANK 进行截面比较
    - 结合成交额确认

注意事项:
    - TSRANK 在窗口期较短时可能不稳定
    - 需关注成交量异常值的影响
    - 前 12 期数据不足时返回 NaN (5+5+3-2 预热)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_max, ts_rank

__all__ = ["alpha_005"]

DIRECTION = -1
DEFAULT_RANK_PERIOD = 5
DEFAULT_CORR_PERIOD = 5
DEFAULT_MAX_PERIOD = 3


def alpha_005(
    ctx: FactorContext,
    rank_period: int = DEFAULT_RANK_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
    max_period: int = DEFAULT_MAX_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #5: 量价时序排名相关性反转。

    公式: -1 * TSMAX(CORR(TSRANK(VOLUME,rank_period), TSRANK(HIGH,rank_period), corr_period), max_period)

    Args:
        ctx: 因子数据上下文
        rank_period: 时序排名窗口期 (默认 5)
        corr_period: 相关系数窗口期 (默认 5)
        max_period: 最大值窗口期 (默认 3)

    Returns:
        量价反转因子面板 (date × symbol)
    """
    vol_rank = ts_rank(ctx.volume, rank_period)
    high_rank = ts_rank(ctx.high, rank_period)
    return -1.0 * ts_max(corr(vol_rank, high_rank, corr_period), max_period)

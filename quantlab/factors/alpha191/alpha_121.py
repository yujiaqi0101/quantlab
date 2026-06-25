"""
Alpha191 #121 — VWAP 排名幂次时序
========================================

公式:
    (RANK(VWAP - MIN(VWAP, 12))^TSRANK(CORR(TSRANK(VWAP,20), TSRANK(MEAN(VOL,60),2), 18), 3)) * -1

公式解释:
    左侧: VWAP 与12日最低的差值截面排名
    右侧: (VWAP 20日时序排名 与 60日均量2日时序排名 的18日相关性) 的3日时序排名
    结果: 左^右 * -1

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - VWAP/VOLUME（日频，后复权）

算子依赖:
    - rank
    - ts_min
    - ts_mean
    - ts_rank
    - corr
    - signed_power

背后逻辑:
    VWAP 与历史低点的相对位置，幂次受量价时序相关性影响。

适用场景:
    量价背离选股。

变种与优化:
    - 调整窗口参数

注意事项:
    - 前 ~80 期返回 NaN (复杂多层预热)
    - 负数次幂在底数为 0 时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_min, ts_mean, ts_rank

__all__ = ["alpha_121"]

DIRECTION = -1


def alpha_121(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #121: VWAP 排名幂次时序。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    vol = ctx.volume
    vwap = ctx.get_vwap()

    left = rank(vwap - ts_min(vwap, 12))
    right = ts_rank(
        corr(ts_rank(vwap, 20), ts_rank(ts_mean(vol, 60), 2), 18),
        3,
    )

    return signed_power(left, right) * -1.0

"""
Alpha191 #115 — 排名相关性幂
========================================

公式:
    RANK(CORR((HIGH*0.9+CLOSE*0.1), MEAN(VOL,30), 10))
    ^ RANK(CORR(TSRANK((HIGH+LOW)/2, 4), TSRANK(VOL,10), 7))

公式解释:
    左侧排名: (H*0.9+C*0.1) 与 30日均量的10日相关性的截面排名
    右侧排名: (H+L)/2 的4日时序排名 与 成交量10日时序排名 的7日相关性截面排名
    结果: 左^右 (幂次)

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH/LOW/CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - ts_mean
    - ts_rank
    - corr

背后逻辑:
    两层量价相关性的幂次组合。

适用场景:
    量价背离选股。

变种与优化:
    - 调整权重 0.9/0.1
    - 调整窗口参数

注意事项:
    - 负数次幂在底数为 0 时返回 NaN
    - 前 39 期返回 NaN (ts_mean 30 + corr 10)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean, ts_rank

__all__ = ["alpha_115"]

DIRECTION = 1


def alpha_115(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #115: 排名相关性幂。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    high = ctx.high
    low = ctx.low
    close = ctx.close
    vol = ctx.volume

    left_corr = corr(high * 0.9 + close * 0.1, ts_mean(vol, 30), 10)
    left = rank(left_corr)

    right_corr = corr(ts_rank((high + low) / 2.0, 4), ts_rank(vol, 10), 7)
    right = rank(right_corr)

    # RANK ^ RANK: 用带符号幂处理
    return signed_power(left, right)

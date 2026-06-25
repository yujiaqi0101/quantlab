"""
Alpha191 #113 — 复杂排名相关性
========================================

公式:
    -1 * RANK(SUM(DELAY(CLOSE,5),20)/20) * CORR(CLOSE, VOLUME, 2)
        * RANK(CORR(SUM(CLOSE,5), SUM(CLOSE,20), 2))

公式解释:
    三个排名/相关性的乘积取负:
    1) 前收盘5日的20日和均值截面排名
    2) 收盘价与成交量的2日相关系数
    3) 5日和20日累积收盘价的2日相关性排名

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - delay
    - ts_sum
    - corr

背后逻辑:
    多层排名与相关性的乘积，反映价格、量能、自相关性的综合状态。

适用场景:
    多因子综合打分。

变种与优化:
    - 调整窗口参数
    - 简化乘积为加权

注意事项:
    - 前 25 期返回 NaN (delay 5 + ts_sum 20)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_113"]

DIRECTION = -1


def alpha_113(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #113: 复杂排名相关性。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume

    part1 = rank(ts_sum(delay(close, 5), 20) / 20.0)
    part2 = corr(close, vol, 2)
    part3 = rank(corr(ts_sum(close, 5), ts_sum(close, 20), 2))

    return -1.0 * part1 * part2 * part3

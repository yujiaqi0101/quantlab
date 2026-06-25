"""
Alpha191 #148 — 排名累积与排名差比率
========================================

公式:
    (RANK(CORR((OPEN), SUM(MEAN(VOL,60),9), 6))
     + RANK(DECAYLINEAR(DELTA((CLOSE*0.95+OPEN*0.05),2),3))) / 2

公式解释:
    左项: 开盘价 与 60日均量9日和 的6日相关性排名
    右项: 0.95*收盘+0.05*开盘 的2日差值的3日衰减线性平均排名
    结果: 二者平均

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - delta
    - ts_mean
    - ts_sum
    - corr

背后逻辑:
    通过开盘-量相关性 与 价格变化的衰减平均的排名平均。

适用场景:
    量价综合选股。

变种与优化:
    - 调整权重 0.95/0.05
    - 调整窗口参数

注意事项:
    - 前 74 期返回 NaN (ts_mean 60 + ts_sum 9 + corr 6)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_mean, ts_sum

__all__ = ["alpha_148"]

DIRECTION = 1


def alpha_148(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #148: 排名累积与排名差比率。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    close = ctx.close
    vol = ctx.volume

    term1 = rank(corr(open_, ts_sum(ts_mean(vol, 60), 9), 6))
    hybrid = close * 0.95 + open_ * 0.05
    term2 = rank(decay_linear(delta(hybrid, 2), 3))

    return (term1 + term2) / 2.0

"""
Alpha191 #146 — 20日收盘价与成交量的时序排名相关性
========================================

公式:
    RANK(DECAYLINEAR(CORR(MEAN(CLOSE,20), MEAN(VOL,20), 12), 10))
    / RANK((OPEN^5) + (CLOSE^5) + (HIGH^5) + (LOW^5))

公式解释:
    分子: 20日均值收盘价与20日均量12日相关性的10日衰减平均排名
    分母: 开/收/高/低各自5次幂之和的排名
    结果: 分子 / 分母

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW/CLOSE/VOLUME（日频，后复权）

算子依赖:
    - rank
    - decay_linear
    - ts_mean
    - corr
    - signed_power

背后逻辑:
    通过20日量价相关性与价格极值的比率衡量结构。

适用场景:
    量价综合选股。

变种与优化:
    - 调整窗口 20/12
    - 调整幂次 5

注意事项:
    - 分母为 0 时返回 NaN
    - 前 41 期返回 NaN (ts_mean 20 + corr 12 + decay 10)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.smooth import decay_linear
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_146"]

DIRECTION = 1


def alpha_146(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #146: 20日收盘价与成交量的时序排名相关性。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low
    close = ctx.close
    vol = ctx.volume

    numerator = rank(decay_linear(corr(ts_mean(close, 20), ts_mean(vol, 20), 12), 10))
    denominator = rank(
        signed_power(open_, 5) + signed_power(close, 5)
        + signed_power(high, 5) + signed_power(low, 5)
    )

    safe_denom = denominator.where(denominator.abs() > 0, np.nan)
    return numerator / safe_denom

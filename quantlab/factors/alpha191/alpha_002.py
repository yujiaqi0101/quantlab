"""
Alpha191 #2 — K线实体位置1日变化反转
========================================

公式:
    -1 * DELTA(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW), 1)

公式解释:
    计算当日K线实体在振幅中的相对位置（(C-L)-(H-C)）/(H-L)，
    取其1日变化量的负值。

分类:
    均值回复 (mean_reversion)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、HIGH 最高价、LOW 最低价（日频，后复权）

算子依赖:
    - delay
    - delta

背后逻辑:
    该值衡量收盘价在当日高低价区间中的相对位置变化。当收盘价从接近
    最高价的位置回落时（DELTA为负，取负后为正），说明上涨动能衰减，
    预示可能的均值回复。

适用场景:
    日内均值回复策略，捕捉短期价格偏离后的回归机会。

变种与优化:
    - 可使用多日 DELTA 替代1日
    - 加入成交量加权
    - 结合 VWAP 位置

注意事项:
    - HIGH=LOW 时分母为0，需置 NaN
    - 涨跌停板会影响K线形态
    - 前 2 期数据不足时返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, delta

__all__ = ["alpha_002"]

DIRECTION = -1
DEFAULT_PERIOD = 1


def alpha_002(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #2: K线实体位置1日变化反转。

    公式: -1 * DELTA(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW), period)

    Args:
        ctx: 因子数据上下文
        period: 变化量窗口期 (默认 1)

    Returns:
        均值回复因子面板 (date × symbol)
    """
    rng = ctx.high - ctx.low
    rng = rng.replace(0, np.nan)
    body_pos = ((ctx.close - ctx.low) - (ctx.high - ctx.close)) / rng
    return -1.0 * delta(body_pos, period)

"""
Alpha101 #30 — 价格方向一致性-成交量比
========================================

公式:
    ((1.0 - rank((sign(close-delay(close,1)) + sign(delay(close,1)-delay(close,2))
                  + sign(delay(close,2)-delay(close,3))))) * sum(volume,5)) / sum(volume,20)

公式解释:
    连续 3 天价格变化方向符号之和的截面排名，
    用 1 减去该排名，再乘以 5 日成交量与 20 日成交量之比。
    价格方向不一致且短期成交量相对较高时因子值较大。

分类:
    价格方向一致性-成交量比 (direction_consistency_volume_ratio)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay
    - sign (内置)
    - rank (截面)
    - ts_sum

背后逻辑:
    价格方向一致性衡量趋势强度。
    方向不一致 (符号和接近 0) 时 1-rank 较大，
    叠加短期放量 (5 日/20 日量比高)，
    表示"震荡放量"状态，可能是反转机会。

适用场景:
    震荡放量反转策略。

变种与优化:
    - 可引入更多天的方向判断
    - 可使用加权方向一致性
    - 可用 decay_linear 替代简单求和

注意事项:
    - 前 20 期返回 NaN (delay 3 + ts_sum 20)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_030"]

DIRECTION = 1


def alpha_030(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #30: 价格方向一致性-成交量比。

    公式: ((1-rank(sign(d1)+sign(d2)+sign(d3)))*sum(volume,5))/sum(volume,20)

    Args:
        ctx: 因子数据上下文

    Returns:
        价格方向一致性-成交量比因子面板 (date × symbol)
    """
    close = ctx.close
    d1 = close - delay(close, 1)
    d2 = delay(close, 1) - delay(close, 2)
    d3 = delay(close, 2) - delay(close, 3)
    direction_sum = np.sign(d1) + np.sign(d2) + np.sign(d3)
    vol_ratio = ts_sum(ctx.volume, 5) / ts_sum(ctx.volume, 20)
    return (1.0 - rank(direction_sum)) * vol_ratio

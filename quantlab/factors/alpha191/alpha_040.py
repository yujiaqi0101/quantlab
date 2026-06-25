"""
Alpha191 #40 — 上涨下跌日量比
========================================

公式:
    SUM(上涨日VOLUME, 26) / SUM(下跌日VOLUME, 26) * 100

公式解释:
    计算26日内上涨日成交量之和与下跌日成交量之和的比值乘以100。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_sum

背后逻辑:
    该因子衡量上涨和下跌日的成交量对比。比值大于100表示上涨日成交量更大
    （放量上涨），小于100表示下跌日成交量更大（放量下跌）。正向选择偏好
    放量上涨的股票。

适用场景:
    量价确认策略，经典的 GRIN 指标变体。

变种与优化:
    - 可调整窗口期 (26 → 10/60)
    - 使用成交额替代成交量
    - 加入涨跌幅加权

注意事项:
    - 上涨/下跌日定义：此处采用 CLOSE>OPEN
    - 需注意累积期内停牌影响
    - 前 25 期数据不足时返回 NaN (26日累积)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_040"]

DIRECTION = 1
DEFAULT_PERIOD = 26


def alpha_040(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #40: 上涨下跌日量比。

    公式: SUM(VOLUME[up], period) / SUM(VOLUME[down], period) * 100

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 26)

    Returns:
        量比因子面板 (date × symbol)，单位 %
    """
    up = ctx.volume.where(ctx.close > ctx.open, 0.0)
    down = ctx.volume.where(ctx.close < ctx.open, 0.0)
    up_sum = ts_sum(up, period)
    down_sum = ts_sum(down, period).replace(0, np.nan)
    return up_sum / down_sum * 100.0

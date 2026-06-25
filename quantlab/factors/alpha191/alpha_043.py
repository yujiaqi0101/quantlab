"""
Alpha191 #43 — 6日带方向成交量累积 (OBV简化版)
========================================

公式:
    SUM(带方向VOLUME, 6) — OBV简化版

公式解释:
    计算6日内带方向成交量之和。上涨日取正成交量，下跌日取负成交量，
    平盘取零。

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
    该因子是 OBV（On Balance Volume）的简化版本，衡量累积的量价方向。
    正向累积表示买方力量占优。

适用场景:
    量价趋势跟踪策略。

变种与优化:
    - 可调整窗口期 (6 → 10/20)
    - 使用不同的方向判断标准 (CLOSE vs PREV_CLOSE)
    - 加入涨跌幅加权

注意事项:
    - OBV 在震荡市中效果有限，需结合价格趋势使用
    - 前 5 期数据不足时返回 NaN (ts_sum 6)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_043"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_043(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #43: 6日带方向成交量累积 (OBV简化版)。

    公式: SUM(SIGN(CLOSE-OPEN)*VOLUME, period)

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 6)

    Returns:
        带方向成交量累积因子面板 (date × symbol)
    """
    signed_vol = ctx.volume.where(ctx.close > ctx.open,
                                  -ctx.volume.where(ctx.close < ctx.open, 0.0))
    return ts_sum(signed_vol, period)

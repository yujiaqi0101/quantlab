"""
Alpha191 #187 — 价格SMA比率的20日和
========================================

公式:
    SUM(((CLOSE>DELAY(CLOSE,1)) ? 1 : 0), 20)

公式解释:
    当 收盘价 > 前日收盘价 时取1，否则取0
    对该0/1序列进行20日累积和

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - delay
    - ts_sum

背后逻辑:
    20日内上涨天数。

适用场景:
    短期动量策略。

变种与优化:
    - 调整窗口 20
    - 加入权重衰减

注意事项:
    - 前 20 期返回 NaN (delay 1 + ts_sum 20)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_187"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_187(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #187: 价格SMA比率的20日和。

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 20)

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)
    indicator = (close > prev_close).astype(float)
    # NaN 保护
    mask = prev_close.notna()
    indicator = indicator.where(mask)
    return ts_sum(indicator, period)

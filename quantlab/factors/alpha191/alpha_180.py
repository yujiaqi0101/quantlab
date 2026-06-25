"""
Alpha191 #180 — 复杂多窗口量价排名差
========================================

公式:
    (MEAN(VOL,20)<VOL) ? ((CLOSE - DELAY(CLOSE,5)) / DELAY(CLOSE,5)) * -1 : 0

公式解释:
    当 20日均量 < 当日成交量 时:
        返回 (收盘价 - 5日前收盘价) / 5日前收盘价 * -1
    否则: 返回 0

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好 (公式中的 -1)

数据来源与频率:
    - CLOSE/VOLUME（日频，后复权）

算子依赖:
    - ts_mean
    - delay

背后逻辑:
    放量时的5日价格动量反转。

适用场景:
    量价反转策略。

变种与优化:
    - 调整窗口 20/5
    - 替换为对数收益率

注意事项:
    - 分母为 0 时返回 NaN
    - 前 24 期返回 NaN (ts_mean 20 + delay 5 取大)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_mean

__all__ = ["alpha_180"]

DIRECTION = -1


def alpha_180(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #180: 复杂多窗口量价排名差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume

    mean_vol_20 = ts_mean(vol, 20)
    prev_close_5 = delay(close, 5)
    safe_prev = prev_close_5.where(prev_close_5.abs() > 0, np.nan)
    ret_5 = (close - prev_close_5) / safe_prev * -1.0

    cond = mean_vol_20 < vol
    out = ret_5.where(cond, 0.0)
    mask = mean_vol_20.notna() & prev_close_5.notna()
    return out.where(mask)

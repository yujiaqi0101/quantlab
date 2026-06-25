"""
Alpha191 #19 — 不对称5日收益率
========================================

公式:
    若 CLOSE < DELAY(CLOSE,5):
        (CLOSE - DELAY(CLOSE,5)) / DELAY(CLOSE,5)
    若 CLOSE = DELAY(CLOSE,5):
        0
    若 CLOSE > DELAY(CLOSE,5):
        (CLOSE - DELAY(CLOSE,5)) / CLOSE

公式解释:
    三重条件判断：若当前收盘价低于5日前，用5日前价格做分母计算收益率；
    若相等返回0；若高于5日前，用当前价格做分母计算收益率。

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    使用不对称分母计算收益率。下跌时用较小分母（5日前价格），放大下跌
    幅度；上涨时用较大分母（当前价格），缩小上涨幅度。这种不对称设计
    使下跌信号更强，正向选择偏好跌幅被放大的股票（超卖反弹逻辑）。

适用场景:
    超卖反弹策略。

变种与优化:
    - 可调整窗口期 (5 → 10/20)
    - 调整不对称比例
    - 使用不同的条件判断逻辑

注意事项:
    - 不对称设计可能引入偏差
    - 需关注分母为零或接近零的情况
    - 前 5 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_019"]

DIRECTION = 1
DEFAULT_PERIOD = 5


def alpha_019(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #19: 不对称5日收益率。

    公式:
        CLOSE<prev → (CLOSE-prev)/prev
        CLOSE=prev → 0
        CLOSE>prev → (CLOSE-prev)/CLOSE

    Args:
        ctx: 因子数据上下文
        period: 比较窗口期 (默认 5)

    Returns:
        不对称收益率因子面板 (date × symbol)
    """
    close = ctx.close
    prev = delay(close, period)
    diff = close - prev
    down = diff / prev  # 下跌：用前价做分母（放大）
    up = diff / close  # 上涨：用现价做分母（缩小）
    result = down.where(close < prev, up.where(close > prev, 0.0))
    return result.where(prev.notna())

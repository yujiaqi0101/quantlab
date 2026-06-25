"""
Alpha191 #18 — 5日收盘价比值动量
========================================

公式:
    CLOSE / DELAY(CLOSE, 5)

公式解释:
    计算当前收盘价与5日前收盘价的比值。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    与 Alpha14 类似，但使用比值而非差值，衡量的是5日相对收益率。
    比值形式在价格水平差异较大的股票间更具可比性。正向意味着偏好
    近期上涨的股票（动量效应）。

适用场景:
    短期动量策略。

变种与优化:
    - 可调整窗口期（5日 → 10日/20日）
    - 使用对数收益率 log(CLOSE/DELAY(CLOSE,5))
    - 加入成交量确认

注意事项:
    - 简单动量因子噪声较大，需结合其他因子使用
    - 前 5 期数据不足时返回 NaN
    - 需使用后复权价格以避免除权造成的虚假跳动
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_018"]

DIRECTION = 1
DEFAULT_PERIOD = 5


def alpha_018(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #18: 5日收盘价比值动量。

    公式: CLOSE / DELAY(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 5)

    Returns:
        动量因子面板 (date × symbol)，前 period 期为 NaN
    """
    close = ctx.close
    prev = delay(close, period)
    return close / prev

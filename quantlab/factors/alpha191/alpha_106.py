"""
Alpha191 #106 — 20日价格动量
========================================

公式:
    CLOSE - DELAY(CLOSE, 20)

公式解释:
    计算当前收盘价与20日前收盘价的差值。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    与 Alpha14 类似但使用20日窗口期，衡量中期价格变动幅度。
    经典中期动量因子，偏好中期上涨的标的。

适用场景:
    中期动量策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 使用对数收益率 log(CLOSE/DELAY(CLOSE,n))
    - 标准化为百分比变动 (CLOSE-DELAY(CLOSE,n))/DELAY(CLOSE,n)

注意事项:
    - 绝对价格差受价格水平影响，跨标的比较需做标准化
    - 前 20 期数据不足时返回 NaN
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_106"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_106(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #106: 20日价格动量。

    公式: CLOSE - DELAY(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 20)

    Returns:
        价格动量因子面板 (date × symbol)，前 period 期为 NaN
    """
    close = ctx.close
    return close - delay(close, period)

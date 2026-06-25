"""
Alpha191 #20 — 6日百分比动量
========================================

公式:
    (CLOSE - DELAY(CLOSE, 6)) / DELAY(CLOSE, 6) * 100

公式解释:
    计算6日收益率（百分比形式）。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    标准的6日动量因子，以百分比形式表示，便于不同价格水平股票间的比较。
    正向意味着偏好近期上涨的股票。

适用场景:
    短期动量策略。

变种与优化:
    - 可调整窗口期（6日 → 12日/20日）
    - 使用对数收益率 log(CLOSE/DELAY(CLOSE,6))

注意事项:
    - 简单动量因子效果有限，需结合其他因子使用
    - 前 6 期数据不足时返回 NaN
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_020"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_020(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #20: 6日百分比动量。

    公式: (CLOSE - DELAY(CLOSE, period)) / DELAY(CLOSE, period) * 100

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 6)

    Returns:
        百分比动量因子面板 (date × symbol)，前 period 期为 NaN
    """
    close = ctx.close
    prev = delay(close, period)
    return (close - prev) / prev * 100.0

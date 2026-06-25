"""
Alpha191 #88 — 20日百分比动量
========================================

公式:
    (CLOSE - DELAY(CLOSE, 20)) / DELAY(CLOSE, 20) * 100

公式解释:
    计算20日收益率（百分比形式）。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay (20日延迟)

背后逻辑:
    标准的20日（约1个月）动量因子，
    衡量中期价格变动幅度。

适用场景:
    中期动量策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 使用对数收益率
    - 加入成交量确认

注意事项:
    - 经典动量因子，效果已被广泛研究
    - 前 20 期返回 NaN (delay 20)
    - 分母为 0 时需处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_088"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_088(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #88: 20日百分比动量。

    公式: (CLOSE - DELAY(CLOSE, period)) / DELAY(CLOSE, period) * 100

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 20)

    Returns:
        百分比动量因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, period)
    safe_prev = prev_close.where(prev_close > 0, np.nan)
    return (close - prev_close) / safe_prev * 100.0

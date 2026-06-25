"""
Alpha191 #190 — 收益率20日和
========================================

公式:
    LOG(CLOSE) - LOG(DELAY(CLOSE,20))

公式解释:
    计算当日与20日前收盘价的对数差
    即对数收益率(20日)

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    20日对数收益率。

适用场景:
    长期动量策略。

变种与优化:
    - 调整窗口 20
    - 替换为简单收益率

注意事项:
    - 价格 <=0 时返回 NaN
    - 前 20 期返回 NaN (delay 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_190"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_190(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #190: 收益率20日和。

    Args:
        ctx: 因子数据上下文
        period: 对数收益率窗口期 (默认 20)

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    log_close = np.log(close.where(close > 0, np.nan))
    prev_log_close = delay(log_close, period)
    return log_close - prev_log_close

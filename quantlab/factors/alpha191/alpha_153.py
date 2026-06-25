"""
Alpha191 #153 — 20日均值与5日相关性排名差
========================================

公式:
    SMA(BEGIN_VALUE / END_VALUE - 1, 5, 1)
    其中 BEGIN_VALUE = 20日收盘价的第一个值
         END_VALUE = 20日收盘价的最后一个值

公式解释:
    计算20日窗口内首尾收盘价比率
    对该比率-1进行SMA(5,1)平滑

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE（日频，后复权）

算子依赖:
    - sma (SMA(X, n, m))
    - delay (用于获取窗口起始值)

背后逻辑:
    20日窗口内价格变化率的短期平滑。

适用场景:
    中期动量策略。

变种与优化:
    - 调整窗口 20/5
    - 替换为对数收益率

注意事项:
    - 分母为 0 时返回 NaN
    - 前 24 期返回 NaN (delay 20 + sma 5)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_153"]

DIRECTION = 1


def alpha_153(ctx: FactorContext, period: int = 20) -> pd.DataFrame:
    """Alpha191 #153: 20日均值与5日相关性排名差。

    Args:
        ctx: 因子数据上下文
        period: 价格窗口期 (默认 20)

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    # 窗口起始值 = delay(close, period-1)
    begin_value = delay(close, period - 1)
    safe_begin = begin_value.where(begin_value.abs() > 0, np.nan)
    ratio_minus_1 = close / safe_begin - 1.0
    return sma(ratio_minus_1, 5, 1)

"""
Alpha191 #134 — 12日收益率乘以成交量
========================================

公式:
    (c - prev_c12) / prev_c12 * VOLUME

公式解释:
    计算12日收益率乘以成交量。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay (12日延迟)

背后逻辑:
    与 Alpha29 类似但使用12日窗口期。
    衡量中期量价共振强度。

适用场景:
    中期量价共振策略。

变种与优化:
    - 可调整窗口期 (12 → 6/20)
    - 使用成交额替代成交量
    - 做标准化处理

注意事项:
    - 收益率与成交量的乘积量纲不一致
    - 前 12 期返回 NaN (delay 12)
    - 分母为 0 时需处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_134"]

DIRECTION = 1
DEFAULT_PERIOD = 12


def alpha_134(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #134: 12日收益率乘以成交量。

    公式: (CLOSE - DELAY(CLOSE, period)) / DELAY(CLOSE, period) * VOLUME

    Args:
        ctx: 因子数据上下文
        period: 收益率窗口期 (默认 12)

    Returns:
        量价共振因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, period)
    # 分母为 0 时返回 NaN
    safe_prev = prev_close.where(prev_close > 0, np.nan)
    returns = (close - prev_close) / safe_prev
    return returns * ctx.volume

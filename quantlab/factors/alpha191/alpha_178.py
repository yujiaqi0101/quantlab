"""
Alpha191 #178 — 1日收益率乘以成交量
========================================

公式:
    (CLOSE - DELAY(CLOSE, 1)) / DELAY(CLOSE, 1) * VOLUME

公式解释:
    计算1日收益率乘以成交量。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay (1日延迟)

背后逻辑:
    与 Alpha29/134 类似但使用1日窗口期。
    衡量日频量价共振强度。

适用场景:
    日频量价共振策略。

变种与优化:
    - 可使用成交额替代成交量
    - 做标准化处理
    - 加入平滑窗口

注意事项:
    - 日频信号噪声较大，建议平滑处理
    - 前 1 期返回 NaN (delay 1)
    - 分母为 0 时需处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_178"]

DIRECTION = 1


def alpha_178(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #178: 1日收益率乘以成交量。

    公式: (CLOSE - DELAY(CLOSE, 1)) / DELAY(CLOSE, 1) * VOLUME

    Args:
        ctx: 因子数据上下文

    Returns:
        量价共振因子面板 (date × symbol)
    """
    close = ctx.close
    prev_close = delay(close, 1)
    # 分母为 0 时返回 NaN
    safe_prev = prev_close.where(prev_close > 0, np.nan)
    returns = (close - prev_close) / safe_prev
    return returns * ctx.volume

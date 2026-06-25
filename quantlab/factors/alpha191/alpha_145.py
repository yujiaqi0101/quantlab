"""
Alpha191 #145 — 成交量偏离率
========================================

公式:
    (mean(v, 9) - mean(v, 26)) / mean(v, 12) * 100

公式解释:
    计算9日成交量均值与26日成交量均值之差，
    除以12日成交量均值乘以100。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - ts_mean (滚动均值)

背后逻辑:
    衡量短期成交量相对中期成交量的偏离程度。
    正值表示短期放量，负值表示短期缩量。

适用场景:
    成交量偏离策略。

变种与优化:
    - 可调整各窗口期 (9/26/12 → 其他)
    - 使用成交额替代成交量
    - 做平滑处理

注意事项:
    - 与成交量MACD逻辑类似
    - 前 25 期返回 NaN (max(9,26,12) - 1)
    - 分母为 0 时需处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_145"]

DIRECTION = 1
DEFAULT_SHORT = 9
DEFAULT_LONG = 26
DEFAULT_MID = 12


def alpha_145(
    ctx: FactorContext,
    short: int = DEFAULT_SHORT,
    long: int = DEFAULT_LONG,
    mid: int = DEFAULT_MID,
) -> pd.DataFrame:
    """Alpha191 #145: 成交量偏离率。

    公式: (mean(v, short) - mean(v, long)) / mean(v, mid) * 100

    Args:
        ctx: 因子数据上下文
        short: 短期窗口期 (默认 9)
        long: 长期窗口期 (默认 26)
        mid: 中期窗口期 (默认 12)

    Returns:
        成交量偏离率因子面板 (date × symbol)
    """
    vol = ctx.volume
    ma_short = ts_mean(vol, short)
    ma_long = ts_mean(vol, long)
    ma_mid = ts_mean(vol, mid)
    # 分母为 0 时返回 NaN
    safe_mid = ma_mid.where(ma_mid > 0, np.nan)
    return (ma_short - ma_long) / safe_mid * 100.0

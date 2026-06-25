"""
Alpha191 #67 — 24日RSI
========================================

公式:
    24日RSI

公式解释:
    计算24日 RSI（相对强弱指标）。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rsi (基于 SMA 指数平滑)

背后逻辑:
    RSI 衡量一段时期内上涨幅度占总波动的比例，值域 [0, 100]。
    24日窗口期使 RSI 更平滑，反映中期动量状态。
    正向选择偏好 RSI 较高（强势）的标的。

适用场景:
    中期动量策略。

变种与优化:
    - 可调整窗口期 (24 → 6/12/14)
    - 结合超买(>70)/超卖(<30)区间使用
    - 使用不同的平滑方式 (WMA/EMA)

注意事项:
    - 24日 RSI 响应较慢，可能错过短期机会
    - 极端行情下 RSI 可能长期处于超买/超卖区
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import rsi

__all__ = ["alpha_067"]

DIRECTION = 1
DEFAULT_PERIOD = 24


def alpha_067(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #67: 24日RSI。

    公式: RSI(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: RSI 窗口期 (默认 24)

    Returns:
        RSI 因子面板 (date × symbol)，值域 [0, 100]
    """
    return rsi(ctx.close, period)

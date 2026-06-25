"""
Alpha191 #63 — 6日RSI
========================================

公式:
    SMA(MAX(RET,0),6,1) / SMA(|RET|,6,1) * 100 — 6日RSI

公式解释:
    计算6日内正收益率的SMA除以6日内绝对收益率的SMA乘以100，即6日RSI。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rsi (基于 SMA 指数平滑)

背后逻辑:
    RSI（Relative Strength Index）是经典动量指标，衡量近期上涨力量
    占总力量的比例。6日窗口期使 RSI 响应迅速，反映短期动量状态。
    RSI>70 为超买，RSI<30 为超卖。正向选择偏好 RSI 高（强势）的标的。

适用场景:
    短期动量策略。

变种与优化:
    - 可调整窗口期 (6 → 12/14/24)
    - 结合超买(>70)/超卖(<30)区间使用
    - 使用不同的平滑方式 (WMA/EMA)

注意事项:
    - 6日 RSI 噪声较大，可能频繁触发超买超卖
    - 强趋势中 RSI 可能长期处于超买/超卖区
    - 前若干期因 SMA 预热不足返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import rsi

__all__ = ["alpha_063"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_063(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #63: 6日RSI。

    公式: RSI(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: RSI 窗口期 (默认 6)

    Returns:
        RSI 因子面板 (date × symbol)，值域 [0, 100]
    """
    return rsi(ctx.close, period)

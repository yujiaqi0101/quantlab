"""
Alpha191 #79 — 12日RSI
========================================

公式:
    12日RSI

公式解释:
    计算12日 RSI（相对强弱指标）。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rsi (基于 SMA 指数平滑)

背后逻辑:
    与 Alpha63/67 类似但使用12日窗口期。12日是 RSI 的常用参数之一，
    平衡了敏感度和稳定性。

适用场景:
    动量策略。

变种与优化:
    - 可调整窗口期 (12 → 6/14/24)
    - 结合超买超卖区间使用
    - 与其他动量因子组合

注意事项:
    - 12日 RSI 是较为均衡的选择
    - 需结合市场状态判断超买超卖有效性
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import rsi

__all__ = ["alpha_079"]

DIRECTION = 1
DEFAULT_PERIOD = 12


def alpha_079(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #79: 12日RSI。

    公式: RSI(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: RSI 窗口期 (默认 12)

    Returns:
        RSI 因子面板 (date × symbol)，值域 [0, 100]
    """
    return rsi(ctx.close, period)

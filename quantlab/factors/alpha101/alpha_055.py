"""
Alpha101 #55 — 开盘价偏离-日内变化
========================================

公式:
    -1 * rank((open - ts_sum(close, 10)) * (open - close) / open)

公式解释:
    开盘价与 10 日收盘价之和的差，乘以日内涨跌幅 (open-close)，除以开盘价，截面排名取负。

分类:
    开盘价偏离-日内变化 (open_deviation_intraday_change)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_sum
    - rank (截面)

背后逻辑:
    (open - ts_sum(close,10)): 开盘价相对 10 日收盘总和的偏离 (正值表示高开)
    (open - close): 日内涨跌 (正值表示收跌)
    两者乘积 / open 归一化后排名取负。
    高开且收跌时因子值大，取负看空 (弱势)。

适用场景:
    开盘价偏离与日内动量联合反转策略。

变种与优化:
    - 可使用 ts_mean 替代 ts_sum
    - 可调整窗口 (10 → 5/20)
    - 可引入成交量权重

注意事项:
    - open 为 0 时需处理除零
    - 前 10 期返回 NaN (ts_sum)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_055"]

DIRECTION = -1


def alpha_055(ctx: FactorContext, period: int = 10) -> pd.DataFrame:
    """Alpha101 #55: 开盘价偏离-日内变化。

    公式: -1 * rank((open - ts_sum(close, period)) * (open - close) / open)

    Args:
        ctx: 因子数据上下文
        period: 求和窗口 (默认 10)

    Returns:
        开盘价偏离-日内变化因子面板 (date × symbol)
    """
    open_safe = ctx.open.where(ctx.open.abs() > 1e-12)
    dev = ctx.open - ts_sum(ctx.close, period)
    intraday = ctx.open - ctx.close
    return -1 * rank(dev * intraday / open_safe)

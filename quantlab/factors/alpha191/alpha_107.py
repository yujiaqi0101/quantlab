"""
Alpha191 #107 — 开盘跳空排名乘积反转
========================================

公式:
    -rank(open - delay(high, 1)) * rank(open - delay(close, 1)) * rank(open - delay(low, 1))

公式解释:
    计算开盘价分别减去前一日最高价、收盘价、最低价的
    截面排名的乘积，取负值。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay (1日延迟)
    - rank (截面排名)

背后逻辑:
    综合衡量了开盘价相对于前一日价格区间的位置。
    三个排名的乘积在开盘价远低于前一日价格时为较大的正值
    （取负后为较大的负值）。

适用场景:
    开盘跳空分析策略。

变种与优化:
    - 可调整参考价格
    - 使用不同的组合方式 (如加法)
    - 加入成交量确认

注意事项:
    - 三个排名的乘积可能过于极端
    - 需做标准化
    - 前 1 期返回 NaN (delay 1)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_107"]

DIRECTION = -1


def alpha_107(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #107: 开盘跳空排名乘积反转。

    公式: -rank(open - delay(high, 1)) * rank(open - delay(close, 1)) * rank(open - delay(low, 1))

    Args:
        ctx: 因子数据上下文

    Returns:
        跳空排名乘积因子面板 (date × symbol)
    """
    open_ = ctx.open
    prev_high = delay(ctx.high, 1)
    prev_close = delay(ctx.close, 1)
    prev_low = delay(ctx.low, 1)
    r1 = rank(open_ - prev_high)
    r2 = rank(open_ - prev_close)
    r3 = rank(open_ - prev_low)
    return -1.0 * r1 * r2 * r3

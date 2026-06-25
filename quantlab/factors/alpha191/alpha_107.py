"""
Alpha191 #107 — 开盘跳空三排名乘积
========================================

公式:
    -rank(OPEN - DELAY(HIGH,1)) * rank(OPEN - DELAY(CLOSE,1)) * rank(OPEN - DELAY(LOW,1))

公式解释:
    计算开盘价分别减去前一日最高价、收盘价、最低价的截面排名的乘积，
    取负值。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - HIGH 最高价、LOW 最低价、CLOSE 收盘价（日频，后复权）

算子依赖:
    - rank (截面排名)
    - delay

背后逻辑:
    该因子综合衡量了开盘价相对于前一日价格区间的位置。
    - OPEN - DELAY(HIGH,1)：向上跳空程度
    - OPEN - DELAY(CLOSE,1)：相对前收的跳空
    - OPEN - DELAY(LOW,1)：向下跳空程度
    三个截面排名的乘积在开盘价远低于前一日价格时为较大的负值（取负后为正），
    反向选择偏好低开后反弹的标的。

适用场景:
    开盘跳空分析策略。

变种与优化:
    - 可调整参考价格（前一日 VWAP / 均价）
    - 使用不同的组合方式（加和替代乘积）
    - 加入跳空幅度加权

注意事项:
    - 三个排名的乘积可能过于极端，需做极值处理
    - 跳空信号在低流动性标的上噪声大
    - 前 1 期数据不足时返回 NaN (delay 1)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_107"]

DIRECTION = -1


def alpha_107(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #107: 开盘跳空三排名乘积。

    公式: -rank(OPEN-DELAY(HIGH,1)) * rank(OPEN-DELAY(CLOSE,1)) * rank(OPEN-DELAY(LOW,1))

    Args:
        ctx: 因子数据上下文

    Returns:
        开盘跳空因子面板 (date × symbol)
    """
    open_ = ctx.open
    gap_high = open_ - delay(ctx.high, 1)
    gap_close = open_ - delay(ctx.close, 1)
    gap_low = open_ - delay(ctx.low, 1)
    return -1.0 * rank(gap_high) * rank(gap_close) * rank(gap_low)

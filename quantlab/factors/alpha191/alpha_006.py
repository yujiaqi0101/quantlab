"""
Alpha191 #6 — 加权开盘价4日符号动量反转
========================================

公式:
    (RANK(SIGN(DELTA(((OPEN*0.85) + (HIGH*0.15)), 4)))) * -1

公式解释:
    计算加权开盘价（85%开盘价 + 15%最高价）的4日变化量的符号，
    进行截面排名后取负值。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好短期下跌标的）

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）

算子依赖:
    - rank (截面排名)
    - delta
    - sign (符号函数，numpy 内置)

背后逻辑:
    该因子本质上是短期动量反转因子。加权开盘价偏向开盘价但考虑了
    最高价的影响，4日变化量的符号捕捉了短期方向，取负值意味着偏好
    短期下跌的股票（均值回复逻辑）。SIGN 函数仅保留方向信息，丢弃幅度。

适用场景:
    短期反转策略，在市场过度反应后寻找反弹机会。

变种与优化:
    - 可调整加权比例（85%/15% → 70%/30%）
    - 调整变化周期（4日 → 6日/10日）
    - 加入成交量确认，避免低流动性假信号

注意事项:
    - SIGN 函数丢失了幅度信息，仅保留方向
    - 加权比例的选择需根据市场特征优化
    - 短期反转策略换手率较高，需关注交易成本
    - 前 4 期数据不足时返回 NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_006"]

DIRECTION = -1
DEFAULT_PERIOD = 4


def alpha_006(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #6: 加权开盘价4日符号动量反转。

    公式: -1 * RANK(SIGN(DELTA(OPEN*0.85 + HIGH*0.15, period)))

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 4)

    Returns:
        动量反转因子面板 (date × symbol)，前 period 期为 NaN
    """
    weighted_open = ctx.open * 0.85 + ctx.high * 0.15
    change = delta(weighted_open, period)
    return -1.0 * rank(np.sign(change))

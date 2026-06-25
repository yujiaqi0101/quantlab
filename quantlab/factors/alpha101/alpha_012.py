"""
Alpha101 #12 — 量价方向符号因子
========================================

公式:
    sign(delta(volume, 1)) * (-1 * delta(close, 1))

公式解释:
    成交量变化方向的符号乘以负的价格变化。放量时做空上涨、做多下跌；缩量时相反。

分类:
    量价方向 (volume_price_direction)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delta
    - sign (符号函数)

背后逻辑:
    最简洁的量价因子之一，仅使用符号信息。
    - 放量 (Δvol>0) + 上涨 (Δclose>0): sign(+)*(-（+)) = -，看空 (放量上涨=派发)
    - 放量 + 下跌: sign(+)*(-(-)) = +，看多 (放量下跌=吸筹)
    - 缩量 + 上涨: sign(-)*(-（+)) = +，看多 (缩量上涨=空头回补)
    - 缩量 + 下跌: sign(-)*(-(-)) = -，看空 (缩量下跌=无量阴跌)

适用场景:
    简单的量价背离策略，捕捉成交量与价格方向的背离信号。

变种与优化:
    - Alpha#60 结构相同
    - 可使用多日变化 (delta volume, 3)
    - 可引入变化幅度权重 (替代纯符号)
    - 可使用成交额替代成交量

注意事项:
    - 仅使用符号信息，丢失了幅度信息
    - 前 2 期数据不足返回 NaN (delta 1)
    - 成交量恒定时 sign(0)=0，因子值为 0
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delta

__all__ = ["alpha_012"]

DIRECTION = 1


def alpha_012(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #12: 量价方向符号因子。

    公式: sign(delta(volume, 1)) * (-1 * delta(close, 1))

    Args:
        ctx: 因子数据上下文

    Returns:
        量价方向因子面板 (date × symbol)
    """
    d_vol = delta(ctx.volume, 1)
    d_close = delta(ctx.close, 1)
    return np.sign(d_vol) * (-1 * d_close)

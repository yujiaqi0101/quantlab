"""
Alpha191 #17 — VWAP回落与5日动量非线性组合
========================================

公式:
    RANK((VWAP - MAX(VWAP, 15))) ^ DELTA(CLOSE, 5)

公式解释:
    计算 VWAP 与15日VWAP最大值之差的截面排名，再取5日收盘价变化量的幂次。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - VWAP 成交量加权均价（日频）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rank
    - ts_max
    - delta

背后逻辑:
    VWAP 偏离近期高点衡量了价格从高点的回落程度，DELTA(CLOSE,5) 衡量了
    5日动量。幂次运算将两个信号非线性组合，形成复杂的动量反转信号。
    底数 RANK 结果落在 [0,1]，指数为价格变化量，组合后放大了
    "回落 + 下跌" 标的的反转信号。

适用场景:
    动量反转策略，偏好从高点回落且近期下跌的股票。

变种与优化:
    - 可调整 VWAP 窗口期（15日 → 10日/20日）
    - 调整动量窗口期（5日 → 3日/10日）
    - 使用 signed_power 保留底数符号

注意事项:
    - 幂次运算可能导致数值不稳定：底数为0且指数为负时返回 NaN
    - 需确保底数和指数的符号一致性问题已被 NaN 保护
    - 前 15 期数据不足时返回 NaN（受 ts_max 预热约束）
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_max

__all__ = ["alpha_017"]

DIRECTION = -1
DEFAULT_VWAP_PERIOD = 15
DEFAULT_MOMENTUM_PERIOD = 5


def alpha_017(
    ctx: FactorContext,
    vwap_period: int = DEFAULT_VWAP_PERIOD,
    momentum_period: int = DEFAULT_MOMENTUM_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #17: VWAP回落与5日动量非线性组合。

    公式: RANK(VWAP - ts_max(VWAP, vwap_period)) ^ DELTA(CLOSE, momentum_period)

    Args:
        ctx: 因子数据上下文
        vwap_period: VWAP 高点窗口期 (默认 15)
        momentum_period: 收盘价动量窗口期 (默认 5)

    Returns:
        动量反转因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    base = rank(vwap - ts_max(vwap, vwap_period))
    exponent = delta(ctx.close, momentum_period)
    # 底数在 [0,1]，指数可正可负；底数为 0 且指数为负 → inf → 置 NaN
    result = np.power(base, exponent)
    result = result.replace([np.inf, -np.inf], np.nan)
    return result

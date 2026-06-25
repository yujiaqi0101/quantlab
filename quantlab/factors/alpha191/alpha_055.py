"""
Alpha191 #55 — 20日复杂波动率累积
========================================

公式:
    SUM(16*(CLOSE-DELAY(CLOSE,1)+(CLOSE-OPEN)/2+DELAY(CLOSE,1)-DELAY(OPEN,1)) /
        (IF(ABS(HIGH-DELAY(CLOSE,1))>ABS(LOW-DELAY(CLOSE,1)) &
               ABS(HIGH-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1)),
           ABS(HIGH-DELAY(CLOSE,1))+ABS(LOW-DELAY(CLOSE,1))/2
               +ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4,
         IF(ABS(LOW-DELAY(CLOSE,1))>ABS(HIGH-DELAY(LOW,1)) &
               ABS(LOW-DELAY(CLOSE,1))>ABS(HIGH-DELAY(CLOSE,1)),
           ABS(LOW-DELAY(CLOSE,1))+ABS(HIGH-DELAY(CLOSE,1))/2
               +ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4,
           ABS(HIGH-DELAY(LOW,1))+ABS(DELAY(CLOSE,1)-DELAY(OPEN,1))/4)))
        * MAX(ABS(HIGH-DELAY(CLOSE,1)), ABS(LOW-DELAY(CLOSE,1))), 20)

公式解释:
    类似 CSI 指标，根据多种价格波动幅度条件选择不同分母，
    最终累积20日波动率强度。

分类:
    波动率 (volatility)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW/CLOSE（日频，后复权）

算子依赖:
    - delay
    - ts_sum
    - max (逐元素)

背后逻辑:
    类 CSI 多条件波动率累积，反映市场活跃程度。反向选择偏好低波动标的。

适用场景:
    低波动选股策略。

变种与优化:
    - 调整窗口 (20 → 10/40)
    - 简化分母条件

注意事项:
    - 分母为 0 时返回 NaN
    - 前 21 期返回 NaN (delay 1 + ts_sum 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_055"]

DIRECTION = -1
DEFAULT_PERIOD = 20


def alpha_055(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #55: 20日复杂波动率累积。

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 20)

    Returns:
        波动率累积因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low
    close = ctx.close

    prev_close = delay(close, 1)
    prev_open = delay(open_, 1)
    prev_low = delay(low, 1)

    # 分子: 16*(CLOSE-prevC+(CLOSE-OPEN)/2+prevC-prevO)
    numerator = 16.0 * (close - prev_close + (close - open_) / 2.0
                        + prev_close - prev_open)

    # 三种条件对应的分母
    abs_h_pc = (high - prev_close).abs()
    abs_l_pc = (low - prev_close).abs()
    abs_h_pl = (high - prev_low).abs()
    abs_pc_po = (prev_close - prev_open).abs()

    cond1 = (abs_h_pc > abs_l_pc) & (abs_h_pc > abs_h_pl)
    denom1 = abs_h_pc + abs_l_pc / 2.0 + abs_pc_po / 4.0

    cond2 = (abs_l_pc > abs_h_pl) & (abs_l_pc > abs_h_pc)
    denom2 = abs_l_pc + abs_h_pc / 2.0 + abs_pc_po / 4.0

    denom3 = abs_h_pl + abs_pc_po / 4.0

    # 嵌套 IF: cond1 ? denom1 : (cond2 ? denom2 : denom3)
    denom = np.where(cond2, denom2, denom3)
    denom = np.where(cond1, denom1, denom)
    denom = pd.DataFrame(denom, index=close.index, columns=close.columns)

    # MAX(|H-prevC|, |L-prevC|)
    max_part = np.maximum(abs_h_pc, abs_l_pc)

    # 分母保护
    safe_denom = denom.where(denom.abs() > 0, np.nan)
    raw = numerator / safe_denom * max_part

    return ts_sum(raw, period)

"""
Alpha191 #123 — VWAP 与高收盘5日排名幂
========================================

公式:
    (RANK(CORR(SUM(((HIGH*0.8) + (LOW*0.2)), 20), SUM(DELAY(CLOSE,5), 20), 20))^5) / RANK((OPEN^5))

公式解释:
    左侧: 高低混合价的20日和 与 前收盘5日的20日和 的20日相关性排名5次幂
    右侧: 开盘价的5次幂的截面排名
    结果: 左 / 右

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/HIGH/LOW/CLOSE（日频，后复权）

算子依赖:
    - rank
    - ts_sum
    - delay
    - corr
    - signed_power

背后逻辑:
    长期价格相关性的排名与开盘价波动幅度的比率。

适用场景:
    长期趋势选股。

变种与优化:
    - 调整权重 0.8/0.2
    - 调整窗口20

注意事项:
    - 分母为 0 时返回 NaN
    - 前 44 期返回 NaN (delay 5 + ts_sum 20 + corr 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.misc import signed_power
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_123"]

DIRECTION = 1


def alpha_123(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #123: VWAP 与高收盘5日排名幂。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    high = ctx.high
    low = ctx.low
    close = ctx.close

    hl_mix = high * 0.8 + low * 0.2
    left_corr = corr(ts_sum(hl_mix, 20), ts_sum(delay(close, 5), 20), 20)
    left = signed_power(rank(left_corr), 5)

    right = rank(signed_power(open_, 5))

    safe_right = right.where(right.abs() > 0, np.nan)
    return left / safe_right

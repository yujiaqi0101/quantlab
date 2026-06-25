"""
Alpha191 #80 — 5日成交量变化率
========================================

公式:
    (V - DELAY(V, 5)) / DELAY(V, 5) * 100

公式解释:
    计算5日成交量变化率（百分比形式）。
    衡量短期成交量的变化幅度。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - delay (5日延迟)

背后逻辑:
    正值表示放量，负值表示缩量。
    正向选择偏好放量的股票。

适用场景:
    成交量变化策略。

变种与优化:
    - 可调整窗口期 (5 → 10/20)
    - 使用成交额替代成交量
    - 做平滑或标准化处理

注意事项:
    - 成交量变化率波动较大
    - 前 5 期返回 NaN (delay 5)
    - 分母为 0 时需处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_080"]

DIRECTION = 1
DEFAULT_PERIOD = 5


def alpha_080(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #80: 5日成交量变化率。

    公式: (V - DELAY(V, period)) / DELAY(V, period) * 100

    Args:
        ctx: 因子数据上下文
        period: 延迟窗口期 (默认 5)

    Returns:
        成交量变化率因子面板 (date × symbol)
    """
    vol = ctx.volume
    prev_vol = delay(vol, period)
    # 分母为 0 时返回 NaN
    safe_prev = prev_vol.where(prev_vol > 0, np.nan)
    return (vol - prev_vol) / safe_prev * 100.0

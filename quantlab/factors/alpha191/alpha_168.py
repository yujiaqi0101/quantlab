"""
Alpha191 #168 — 成交量相对均值比反转
========================================

公式:
    -1 * VOLUME / MEAN(VOLUME, 20)

公式解释:
    计算成交量与20日成交量均值之比的负值。

分类:
    成交量 (volume)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - VOLUME 成交量（日频）

算子依赖:
    - ts_mean (滚动均值)

背后逻辑:
    衡量当前成交量相对近期均值的水平。
    取负值偏好成交量低于均值的股票（缩量），
    反映市场关注度降低后的反转机会。

适用场景:
    成交量反转策略。

变种与优化:
    - 可调整窗口期 (20 → 10/30)
    - 使用成交额替代成交量
    - 使用中位数替代均值 (更稳健)

注意事项:
    - 成交量均值可能受异常值影响
    - 前 19 期返回 NaN (rolling 20)
    - 分母为 0 时需处理
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_168"]

DIRECTION = -1
DEFAULT_PERIOD = 20


def alpha_168(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #168: 成交量相对均值比反转。

    公式: -1 * VOLUME / MEAN(VOLUME, period)

    Args:
        ctx: 因子数据上下文
        period: 均值窗口期 (默认 20)

    Returns:
        成交量相对均值比因子面板 (date × symbol)
    """
    vol = ctx.volume
    mean_vol = ts_mean(vol, period)
    # 分母为 0 时返回 NaN
    safe_mean = mean_vol.where(mean_vol > 0, np.nan)
    return -1.0 * vol / safe_mean

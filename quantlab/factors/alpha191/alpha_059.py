"""
Alpha191 #59 — 20日真实波动幅度累积
========================================

公式:
    SUM(TR, 20)

公式解释:
    计算20日内真实波动幅度（TR）的累积值。

分类:
    量价 (volume_price)

信号方向:
    反向 (-1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - tr (真实波幅)
    - ts_sum

背后逻辑:
    TR 累积值衡量了近期的总体波动水平。反向选择偏好低波动的股票，
    这与低波动异象（Low Volatility Anomaly）一致。

适用场景:
    低波动选股策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 使用 ATR (MEAN(TR,n)) 替代累积
    - 与价格标准化 (SUM(TR,n)/CLOSE)

注意事项:
    - TR 累积值随价格水平发散，跨标的比较需做标准化
    - 前 21 期返回 NaN (TR 预热 1 + ts_sum 20)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import tr
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_059"]

DIRECTION = -1
DEFAULT_PERIOD = 20


def alpha_059(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #59: 20日真实波动幅度累积。

    公式: SUM(TR, period)

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 20)

    Returns:
        TR 累积因子面板 (date × symbol)
    """
    close = ctx.close
    true_range = tr(ctx.high, ctx.low, delay(close, 1))
    return ts_sum(true_range, period)

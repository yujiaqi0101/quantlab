"""
Alpha191 #84 — 20日带方向成交量累积 (OBV简化版)
========================================

公式:
    SUM(带方向VOLUME, 20)

公式解释:
    计算20日内带方向成交量之和。上涨日取正成交量，下跌日取负成交量，
    平盘取零。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_sum

背后逻辑:
    与 Alpha43 类似但使用20日窗口期。更长的窗口期反映中期量价趋势。

适用场景:
    中期量价趋势跟踪策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 使用不同的方向判断标准
    - 加入涨跌幅加权

注意事项:
    - 与 Alpha43、#60 逻辑相同，仅参数不同
    - 前 19 期数据不足时返回 NaN (ts_sum 20)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_084"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_084(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #84: 20日带方向成交量累积 (OBV简化版)。

    公式: SUM(SIGN(CLOSE-OPEN)*VOLUME, period)

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 20)

    Returns:
        带方向成交量累积因子面板 (date × symbol)
    """
    signed_vol = ctx.volume.where(ctx.close > ctx.open,
                                  -ctx.volume.where(ctx.close < ctx.open, 0.0))
    return ts_sum(signed_vol, period)

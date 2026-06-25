"""
Alpha191 #11 — K线实体位置量价累积
========================================

公式:
    SUM(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW)*VOLUME, 6)

公式解释:
    计算6日内每日的K线实体位置（(C-L)-(H-C)）乘以成交量的累积值。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价、HIGH 最高价、LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_sum

背后逻辑:
    K线实体位置衡量收盘价在当日振幅中的相对位置，乘以成交量得到量价综合
    信号。当收盘价接近最高价且成交量较大时，因子值较大，表示买方力量强劲。

适用场景:
    量价趋势跟踪策略，偏好买方力量占优的股票。

变种与优化:
    - 可调整窗口期 (6 → 10/20)
    - 使用不同的量价组合方式
    - 加入成交额信息

注意事项:
    - HIGH=LOW 时分母为0，需置 NaN
    - 涨跌停板会影响K线实体位置的计算
    - 前 5 期数据不足时返回 NaN (ts_sum 6)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_011"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_011(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #11: K线实体位置量价累积。

    公式: SUM(((CLOSE-LOW)-(HIGH-CLOSE))/(HIGH-LOW)*VOLUME, period)

    Args:
        ctx: 因子数据上下文
        period: 累积窗口期 (默认 6)

    Returns:
        量价累积因子面板 (date × symbol)
    """
    rng = ctx.high - ctx.low
    rng = rng.replace(0, np.nan)
    body_pos = ((ctx.close - ctx.low) - (ctx.high - ctx.close)) / rng
    return ts_sum(body_pos * ctx.volume, period)

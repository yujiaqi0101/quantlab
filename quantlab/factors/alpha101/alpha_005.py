"""
Alpha101 #5 — VWAP 偏离
==========================

公式:
    rank(open - (sum(vwap, 10) / 10)) * (-1 * abs(rank(close - vwap)))

公式解释:
    第一部分：开盘价偏离 10 日平均 VWAP 的排名；
    第二部分：收盘价偏离 VWAP 排名的绝对值取负。两者相乘。

分类:
    VWAP 偏离 (vwap_deviation)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）
    - VWAP 成交量加权均价（日频）

算子依赖:
    - ts_mean (sum/N)
    - rank (截面)
    - abs (绝对值)

背后逻辑:
    开盘高于均价且收盘接近均价时因子值较高。
    abs(rank(close - vwap)) 的负号意味着收盘越接近 VWAP，因子值越高 (绝对值越小)。

适用场景:
    适用于检测开盘后的价格回归行为——高开但收盘回归均价的股票可能继续上涨。

变种与优化:
    - 可调整 VWAP 窗口 (10 → 5/20)
    - 可使用其他均价 (如 TWAP)

注意事项:
    - VWAP 缺失时由 amount/volume 近似
    - 前 10 期因 ts_mean 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_005"]

DIRECTION = -1
DEFAULT_VWAP_PERIOD = 10


def alpha_005(ctx: FactorContext, vwap_period: int = DEFAULT_VWAP_PERIOD) -> pd.DataFrame:
    """Alpha101 #5: VWAP 偏离。

    公式: rank(open - ts_mean(vwap, vwap_period)) * (-1 * abs(rank(close - vwap)))

    Args:
        ctx: 因子数据上下文
        vwap_period: VWAP 均值窗口 (默认 10)

    Returns:
        VWAP 偏离因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    open_dev = ctx.open - ts_mean(vwap, vwap_period)
    close_dev = rank(ctx.close - vwap)
    return rank(open_dev) * (-1.0 * close_dev.abs())

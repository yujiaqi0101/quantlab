"""
Alpha101 #11 — VWAP 偏离-成交量
====================================

公式:
    (rank(ts_max(vwap - close, 3)) + rank(ts_min(vwap - close, 3))) * rank(delta(volume, 3))

公式解释:
    VWAP 与收盘价差的 3 日最大值排名加 3 日最小值排名，再乘以 3 日成交量变化排名。

分类:
    VWAP 偏离-成交量 (vwap_deviation_volume)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - VWAP 成交量加权均价（日频）
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_max (滚动最大值)
    - ts_min (滚动最小值)
    - rank (截面)
    - delta (时序差分)

背后逻辑:
    捕捉 VWAP 偏离程度与成交量变化的交互效应。
    ts_max + ts_min 同时捕捉正向和负向偏离。

适用场景:
    适用于检测 VWAP 偏离伴随放量/缩量的场景。

变种与优化:
    - Alpha#71 结构相同
    - 可调整窗口 (3 → 5/10)

注意事项:
    - VWAP 缺失时由 amount/volume 近似
    - 前 4 期因 ts_max/ts_min/delta 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delta, ts_max, ts_min

__all__ = ["alpha_011"]

DIRECTION = -1
DEFAULT_PERIOD = 3


def alpha_011(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #11: VWAP 偏离-成交量。

    公式: (rank(ts_max(vwap - close, period)) + rank(ts_min(vwap - close, period))) * rank(delta(volume, period))

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口 (默认 3)

    Returns:
        VWAP 偏离-成交量因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    dev = vwap - ctx.close
    vol_delta = delta(ctx.volume, period)
    return (rank(ts_max(dev, period)) + rank(ts_min(dev, period))) * rank(vol_delta)

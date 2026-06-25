"""
Alpha191 #120 — VWAP与收盘价偏离排名比
========================================

公式:
    rank(vwap - close) / rank(vwap + close)

公式解释:
    计算 VWAP 与收盘价之差的截面排名除以
    VWAP 与收盘价之和的截面排名。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - VWAP 成交量加权均价（日频）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - rank (截面排名)

背后逻辑:
    衡量 VWAP 与收盘价的相对偏离。
    当 VWAP > Close 时分子为正，表示全天均价高于收盘价（尾盘回落）。

适用场景:
    日内价格偏离策略。

变种与优化:
    - 可使用不同的价格基准 (如 open)
    - 调整排名方式
    - 加入成交额加权

注意事项:
    - 分母为 0 时返回 NaN
    - 排名操作可能损失部分信息
    - VWAP 缺失时由 amount/volume 近似
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank

__all__ = ["alpha_120"]

DIRECTION = 1


def alpha_120(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #120: VWAP与收盘价偏离排名比。

    公式: rank(vwap - close) / rank(vwap + close)

    Args:
        ctx: 因子数据上下文

    Returns:
        偏离排名比因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    close = ctx.close
    numerator = rank(vwap - close)
    denominator = rank(vwap + close)
    # 分母为 0 时返回 NaN
    safe_denom = denominator.where(denominator > 0, np.nan)
    return numerator / safe_denom

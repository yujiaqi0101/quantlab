"""
Alpha101 #41 — 几何均价-VWAP偏离
========================================

公式:
    ((high * low) ^ 0.5) - vwap

公式解释:
    最高价与最低价的几何平均值减去 VWAP。
    衡量几何均价与成交量加权均价的偏离。

分类:
    几何均价-VWAP偏离 (geometric_mean_vwap_deviation)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VWAP 成交量加权均价（日频，缺失时由 amount/volume 近似）

算子依赖:
    - 无 (仅四则运算)

背后逻辑:
    几何均价 (high*low)^0.5 反映高低价的对称中心，VWAP 反映成交量加权均价。
    当几何均价 > VWAP 时，价格重心高于成交量重心，可能预示买盘较强 (看多)。

适用场景:
    日内价格结构偏离策略，捕捉价格重心与成交量重心的背离。

变种与优化:
    - 可使用算术均价 (high+low)/2 替代几何均价
    - 可使用 TWAP 替代 VWAP
    - 可结合多日累积偏离

注意事项:
    - high/low 为负时几何均值异常，需使用后复权正价格
    - VWAP 缺失时由 amount/volume 近似，volume=0 时为 NaN
    - 前 0 期即有值 (无窗口算子)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_041"]

DIRECTION = 1


def alpha_041(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #41: 几何均价-VWAP偏离。

    公式: (high * low) ^ 0.5 - vwap

    Args:
        ctx: 因子数据上下文

    Returns:
        几何均价-VWAP偏离因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    geo_mean = np.sqrt(ctx.high * ctx.low)
    return geo_mean - vwap

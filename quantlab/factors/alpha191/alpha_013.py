"""
Alpha191 #13 — 高低价几何均值与VWAP差
========================================

公式:
    ((HIGH * LOW)^0.5) - VWAP

公式解释:
    计算最高价与最低价的几何平均值减去VWAP。

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价、LOW 最低价（日频，后复权）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - 无（基础算术运算）

背后逻辑:
    几何平均值 (HIGH*LOW)^0.5 代表价格区间的一个特征值，减去VWAP衡量
    日内价格偏离加权均价的程度。当该值为正，说明价格区间中心高于成交
    均价，可能存在卖压；为负则相反。

适用场景:
    日内价格偏离分析，可作为均值回复的辅助信号。

变种与优化:
    - 可使用算术平均值 (HIGH+LOW)/2 替代几何平均值
    - 加入成交量加权
    - 结合其他偏离度指标

注意事项:
    - HIGH 或 LOW 为负时几何平均值无定义（实际不会出现）
    - 需关注极端行情下的偏离
    - VWAP 缺失时用 amount/volume 近似
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_013"]

DIRECTION = 1


def alpha_013(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #13: 高低价几何均值与VWAP差。

    公式: (HIGH*LOW)^0.5 - VWAP

    Args:
        ctx: 因子数据上下文

    Returns:
        偏离因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    return np.sqrt(ctx.high * ctx.low) - vwap

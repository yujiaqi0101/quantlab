"""
Alpha191 #78 — CCI商品路径指标
========================================

公式:
    (TYP - MA(TYP, 12)) / (0.015 * MAD)

    其中 TYP = (HIGH + LOW + CLOSE) / 3
          MAD = MEAN(ABS(TYP - MA(TYP, 12)), 12)

公式解释:
    计算典型价格（TYP=(H+L+C)/3）偏离12日典型价格均值的差，
    除以0.015倍的均值绝对偏差（MAD）。

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价、LOW 最低价、CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean
    - ts_mean (MAD 滚动均值)
    - numpy.abs

背后逻辑:
    CCI（Commodity Channel Index）是经典技术指标，衡量价格偏离统计均值的
    程度。CCI>100 为超买，CCI<-100 为超卖。正向选择偏好 CCI 高的股票。

适用场景:
    均值回复/动量策略。

变种与优化:
    - 可调整窗口期 (12 → 20)
    - 调整常数因子 (0.015 → 0.02)
    - 结合超买超卖区间使用

注意事项:
    - CCI 在强趋势中可能长期处于极端区域
    - MAD 为零时需置 NaN
    - 前 23 期数据不足时返回 NaN (12日均值 + 12日MAD)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_078"]

DIRECTION = 1
DEFAULT_PERIOD = 12
CCI_CONSTANT = 0.015


def alpha_078(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #78: CCI商品路径指标。

    公式: (TYP - MA(TYP, period)) / (0.015 * MAD)
          TYP = (HIGH+LOW+CLOSE)/3
          MAD = MEAN(ABS(TYP - MA(TYP, period)), period)

    Args:
        ctx: 因子数据上下文
        period: 均值与MAD窗口期 (默认 12)

    Returns:
        CCI 因子面板 (date × symbol)
    """
    typ = (ctx.high + ctx.low + ctx.close) / 3.0
    ma_typ = ts_mean(typ, period)
    dev = typ - ma_typ
    mad = ts_mean(np.abs(dev), period).replace(0, np.nan)
    return dev / (CCI_CONSTANT * mad)

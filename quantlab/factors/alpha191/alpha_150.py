"""
Alpha191 #150 — 典型价格乘以成交量
========================================

公式:
    (CLOSE + HIGH + LOW) / 3 * VOLUME

公式解释:
    计算典型价格（TYP）乘以成交量。

分类:
    成交量 (volume)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    无 (基础算术)

背后逻辑:
    典型价格乘以成交量得到量价综合指标，
    类似于典型价格加权的成交量。
    高值表示价格水平高且成交量大。

适用场景:
    量价综合策略。

变种与优化:
    - 可使用不同的价格加权方式 (如 (H+L+2C)/4)
    - 使用成交额替代
    - 做截面标准化

注意事项:
    - 与成交额 (AMOUNT) 概念类似
    - 无预热期，首期即可计算
    - 需做标准化处理
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_150"]

DIRECTION = 1


def alpha_150(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #150: 典型价格乘以成交量。

    公式: (CLOSE + HIGH + LOW) / 3 * VOLUME

    Args:
        ctx: 因子数据上下文

    Returns:
        量价综合因子面板 (date × symbol)
    """
    typ = (ctx.close + ctx.high + ctx.low) / 3.0
    return typ * ctx.volume

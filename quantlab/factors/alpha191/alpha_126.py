"""
Alpha191 #126 — 典型价格
========================================

公式:
    (CLOSE + HIGH + LOW) / 3

公式解释:
    计算典型价格（TYP），即收盘价、最高价、最低价的算术平均值。

分类:
    价格 (price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    无 (基础算术)

背后逻辑:
    典型价格综合了三个关键价格，比单一收盘价更能反映全天价格水平。
    高 TYP 表示价格水平高。

适用场景:
    价格水平选股策略。

变种与优化:
    - 可使用加权典型价格 (如 (H+L+2C)/4)
    - 结合其他价格特征使用
    - 做截面标准化

注意事项:
    - 简单价格水平因子信息含量有限
    - 需结合其他因子使用
    - 无预热期，首期即可计算
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_126"]

DIRECTION = 1


def alpha_126(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #126: 典型价格 (TYP)。

    公式: (CLOSE + HIGH + LOW) / 3

    Args:
        ctx: 因子数据上下文

    Returns:
        典型价格因子面板 (date × symbol)
    """
    return (ctx.close + ctx.high + ctx.low) / 3.0

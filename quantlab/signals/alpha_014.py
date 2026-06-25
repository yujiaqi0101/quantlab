"""
Alpha014 策略封装
================

将 Alpha191 #14 因子封装为可回测的 SignalStrategy。
因子方向为正向，signal() 直接返回因子值，由 PortfolioConstructor 截面排名择股。
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.alpha191.alpha_014 import alpha_014
from quantlab.factors.context import FactorContext
from quantlab.signals.base import SignalStrategy

__all__ = ["Alpha014Strategy", "ALPHA014_PARAM_SPACE"]

# Alpha014 是正向因子，signal 返回因子原值
# (TopN 取降序前 N，正向因子值越大越看好)
DIRECTION = 1

# 网格搜索参数空间 (供 Optimizer 使用)
ALPHA014_PARAM_SPACE = {
    "period": [5, 10, 20],
}


class Alpha014Strategy(SignalStrategy):
    """Alpha191 #14 策略: 5日收盘价动量。

    正向因子，因子值越大越看好。

    Args:
        period: 动量窗口期 (默认 5)
    """

    def __init__(self, period: int = 5):
        self.period = period

    def signal(self, ctx: FactorContext) -> pd.DataFrame:
        return alpha_014(ctx, period=self.period)

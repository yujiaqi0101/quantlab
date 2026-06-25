"""
Alpha191 #15 — 隔夜跳空收益率
========================================

公式:
    OPEN / DELAY(CLOSE, 1) - 1

公式解释:
    计算今日开盘价相对昨日收盘价的收益率（隔夜跳空）。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    衡量隔夜价格跳空 (Overnight Gap)。正值表示跳空高开，负值表示跳空低开。
    正向意味着偏好跳空高开的股票，反映隔夜利好信息的持续影响。

适用场景:
    跳空缺口跟踪策略，偏好隔夜信息驱动的强势股票。

变种与优化:
    - 可结合成交量分析跳空缺口的可靠性
    - 可区分利好和利空跳空
    - 可加入涨跌停板过滤

注意事项:
    - 开盘价受集合竞价影响较大
    - 需关注涨跌停板对开盘价的限制
    - 前期为 NaN，回测引擎自动跳过预热期
    - 需使用后复权价格以避免除权除息造成的虚假跳动
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_015"]

DIRECTION = 1
DEFAULT_PERIOD = 1


def alpha_015(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #15: 隔夜跳空收益率。

    公式: OPEN / DELAY(CLOSE, period) - 1

    Args:
        ctx: 因子数据上下文
        period: 延迟期数 (默认 1)

    Returns:
        隔夜跳空收益率面板 (date × symbol)
    """
    return ctx.open / delay(ctx.close, period) - 1

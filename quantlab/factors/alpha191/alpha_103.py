"""
Alpha191 #103 — 最低价新鲜度
========================================

公式:
    ((20 - LOWDAY(LOW, 20)) / 20) * 100

公式解释:
    计算20日内最低价出现在第几天，
    用 (20 - 天数) / 20 * 100 来衡量最低价的新鲜程度。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - LOW 最低价（日频，后复权）

算子依赖:
    - lowday (n期最小值出现距今天数)

背后逻辑:
    最低价新鲜度高（接近100）表示最低价出现在近期，
    可能意味着价格刚从低点反弹。
    低值表示最低价出现在较久以前，
    价格可能已经上涨了一段时间。

适用场景:
    动量策略，偏好刚从低点反弹的股票。

变种与优化:
    - 可调整窗口期 (20 → 10/30)
    - 结合价格水平使用
    - 加入成交量确认

注意事项:
    - 新鲜度高也可能是持续下跌的信号
    - 需结合趋势判断
    - 前 19 期返回 NaN (rolling 20)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import lowday

__all__ = ["alpha_103"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_103(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #103: 最低价新鲜度。

    公式: ((period - LOWDAY(LOW, period)) / period) * 100

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 20)

    Returns:
        最低价新鲜度因子面板 (date × symbol)
    """
    days = lowday(ctx.low, period)
    return (period - days) / period * 100.0

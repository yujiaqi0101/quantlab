"""
Alpha191 #14 — 5日收盘价动量
========================================

公式:
    CLOSE - DELAY(CLOSE, 5)

公式解释:
    计算当前收盘价与5日前收盘价的差值。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay

背后逻辑:
    最基础的5日动量因子，直接衡量过去5个交易日的价格变动幅度。
    正值表示上涨，负值表示下跌。正向意味着偏好近期上涨的股票（动量效应）。
    该因子是 Alpha191 中最简洁的动量因子，常作为动量类因子的基线对照。

适用场景:
    短期动量策略，偏好近期表现强势的股票；也可作为动量基线与其他复合因子对比。

变种与优化:
    - 可调整窗口期（5日→10日/20日）
    - 可使用对数收益率 log(CLOSE/DELAY(CLOSE,5)) 替代差值，消除量纲影响
    - 可加入成交量确认（放量上涨更可靠）

注意事项:
    - 简单动量因子容易被均值回复策略反向利用，需结合其他因子使用
    - 前5期数据不足时返回 NaN，回测引擎自动跳过预热期
    - 需使用后复权价格以避免除权除息造成的虚假跳动
    - 窗口期 5 为参数，可配置
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_014"]

# 因子方向: 正向 (+1) / 反向 (-1)
DIRECTION = 1
# 默认窗口期
DEFAULT_PERIOD = 5


def alpha_014(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #14: 5日收盘价动量。

    公式: CLOSE - DELAY(CLOSE, period)

    Args:
        ctx: 因子数据上下文
        period: 动量窗口期 (默认 5)

    Returns:
        动量因子面板 (date × symbol)，前 period 期为 NaN
    """
    close = ctx.close
    return close - delay(close, period)

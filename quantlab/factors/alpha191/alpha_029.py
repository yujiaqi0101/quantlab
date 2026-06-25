"""
Alpha191 #29 — 6日收益率量价共振
========================================

公式:
    (CLOSE - DELAY(CLOSE, 6)) / DELAY(CLOSE, 6) * VOLUME

公式解释:
    计算6日收益率乘以成交量。

分类:
    量价 (volume_price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - delay

背后逻辑:
    该因子是收益率与成交量的乘积，衡量量价共振强度。当收益率和成交量
    同时较大时（同向变动），因子值较大，表示趋势强劲。正向选择偏好
    放量上涨或缩量下跌的股票。

适用场景:
    量价共振策略，偏好放量上涨的股票。

变种与优化:
    - 可调整收益率窗口期 (6 → 5/10)
    - 使用成交额替代成交量
    - 进行标准化处理消除量纲差异

注意事项:
    - 收益率与成交量量纲不一致，需注意可比性
    - 前 6 期数据不足时返回 NaN
    - 成交量为 0 时因子值需置 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_029"]

DIRECTION = 1
DEFAULT_PERIOD = 6


def alpha_029(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #29: 6日收益率量价共振。

    公式: (CLOSE - DELAY(CLOSE, period)) / DELAY(CLOSE, period) * VOLUME

    Args:
        ctx: 因子数据上下文
        period: 收益率窗口期 (默认 6)

    Returns:
        量价共振因子面板 (date × symbol)
    """
    close = ctx.close
    prev = delay(close, period)
    ret = (close - prev) / prev
    return ret * ctx.volume

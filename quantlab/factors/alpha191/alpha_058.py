"""
Alpha191 #58 — 20日上涨频率
========================================

公式:
    COUNT(上涨, 20) / 20 * 100

公式解释:
    计算20日内上涨天数占比乘以100。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay
    - ts_sum

背后逻辑:
    与 Alpha53 类似但使用更长的窗口期，衡量中期上涨频率。
    更长的窗口期能更好地反映中期趋势。

适用场景:
    中期动量策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 使用不同的上涨定义
    - 结合涨跌幅加权

注意事项:
    - 简单计数因子信息含量有限
    - 前 20 期数据不足时返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_058"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_058(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #58: 20日上涨频率。

    公式: COUNT(CLOSE>DELAY(CLOSE,1), period) / period * 100

    Args:
        ctx: 因子数据上下文
        period: 统计窗口期 (默认 20)

    Returns:
        上涨频率因子面板 (date × symbol)，单位 %
    """
    prev = delay(ctx.close, 1)
    up = (ctx.close > prev).astype(float)
    # 预热期 (prev NaN) 保持 NaN，避免 0 污染累加
    up = up.where(prev.notna())
    return ts_sum(up, period) / period * 100.0

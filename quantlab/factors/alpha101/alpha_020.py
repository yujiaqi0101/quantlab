"""
Alpha101 #20 — 开盘缺口三因子乘积
========================================

公式:
    -1 * rank(open - delay(high, 1)) * rank(open - delay(close, 1)) * rank(open - delay(low, 1))

公式解释:
    今日开盘价分别与昨日最高价、收盘价、最低价的差值排名，三者相乘取负。
    综合衡量开盘缺口的大小。

分类:
    开盘缺口 (overnight_gap)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay
    - rank (截面)

背后逻辑:
    开盘缺口反映隔夜信息冲击。三个缺口排名相乘放大了缺口方向一致性：
    当开盘价同时高于昨日高/收/低 (全面跳空高开) 时，三个 rank 都高，乘积大，取负后看空。
    当开盘价同时低于昨日高/收/低 (全面跳空低开) 时，三个 rank 都低，乘积小，取负后看多。

适用场景:
    隔夜跳空反转策略，捕捉开盘缺口回归。

变种与优化:
    - 可使用对数变换替代乘积以缓解极端值
    - 可加权组合三个缺口 (如 0.5/0.3/0.2)
    - 可引入成交量确认缺口有效性

注意事项:
    - 三个 rank 相乘会放大极端值
    - 前 2 期数据不足返回 NaN (delay 1)
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_020"]

DIRECTION = -1


def alpha_020(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #20: 开盘缺口三因子乘积。

    公式: -1 * rank(open - delay(high,1)) * rank(open - delay(close,1)) * rank(open - delay(low,1))

    Args:
        ctx: 因子数据上下文

    Returns:
        开盘缺口因子面板 (date × symbol)
    """
    gap_high = rank(ctx.open - delay(ctx.high, 1))
    gap_close = rank(ctx.open - delay(ctx.close, 1))
    gap_low = rank(ctx.open - delay(ctx.low, 1))
    return -1 * gap_high * gap_close * gap_low

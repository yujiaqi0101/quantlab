"""
Alpha101 #37 — 滞后量价相关-日内变化
========================================

公式:
    rank(correlation(delay((open - close), 1), close, 200)) + rank((open - close))

公式解释:
    两部分之和：
    1. 延迟 1 日的日内涨跌幅 (open-close) 与收盘价的 200 日相关性的截面排名；
    2. 日内涨跌幅 (open-close) 的截面排名。
    结合长期量价关系和短期日内变化。

分类:
    滞后量价相关-日内变化 (lagged_price_corr_intraday)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - delay
    - corr
    - rank (截面)

背后逻辑:
    延迟日内涨跌幅与收盘价的长期相关性反映"昨日日内变化对今日收盘的预测力"。
    加上当日日内涨跌幅排名，
    结合长期量价关系和短期日内动量。

适用场景:
    长期量价关系 + 短期日内变化组合策略。

变种与优化:
    - 可使用不同滞后期 (1 → 2/3)
    - 可调整相关性窗口 (200 → 120)
    - 可引入成交量维度

注意事项:
    - 前 201 期返回 NaN (delay 1 + corr 200)
    - 200 日长窗口需足够历史数据
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay

__all__ = ["alpha_037"]

DIRECTION = 1


def alpha_037(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #37: 滞后量价相关-日内变化。

    公式: rank(corr(delay(open-close,1), close, 200)) + rank(open-close)

    Args:
        ctx: 因子数据上下文

    Returns:
        滞后量价相关-日内变化因子面板 (date × symbol)
    """
    intraday = ctx.open - ctx.close
    lagged = delay(intraday, 1)
    return rank(corr(lagged, ctx.close, 200)) + rank(intraday)

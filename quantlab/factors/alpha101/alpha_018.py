"""
Alpha101 #18 — 波动率-价格相关性
====================================

公式:
    -1 * rank((stddev(abs(close - open), 5) + (close - open)) + correlation(close, open, 10))

公式解释:
    5 日日内波动的标准差加上日内涨跌幅，再加上收盘价与开盘价的 10 日相关系数，截面排名取负。

分类:
    波动率-价格相关性 (volatility_price_correlation)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - OPEN 开盘价（日频，后复权）

算子依赖:
    - ts_std (stddev)
    - corr (滚动相关)
    - rank (截面)

背后逻辑:
    stddev(abs(close - open), 5) 衡量日内波动性，close - open 衡量方向。
    综合波动率和价格形态，适用于高波动且开盘收盘价高度相关时的反转策略。

适用场景:
    适用于高波动且开盘收盘价高度相关时的反转策略。

变种与优化:
    - 可调整窗口参数 (5, 10)
    - 可加入成交量维度
    - 可使用 ATR 替代 stddev

注意事项:
    - 前 10 期因 corr(10) 预热返回 NaN
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_018"]

DIRECTION = -1
DEFAULT_STD_PERIOD = 5
DEFAULT_CORR_PERIOD = 10


def alpha_018(
    ctx: FactorContext,
    std_period: int = DEFAULT_STD_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha101 #18: 波动率-价格相关性。

    公式: -1 * rank((stddev(abs(close - open), std_period) + (close - open)) + correlation(close, open, corr_period))

    Args:
        ctx: 因子数据上下文
        std_period: 日内波动标准差窗口 (默认 5)
        corr_period: 收开盘相关系数窗口 (默认 10)

    Returns:
        波动率-价格相关性因子面板 (date × symbol)
    """
    intraday = (ctx.close - ctx.open).abs()
    return -1.0 * rank(
        ts_std(intraday, std_period) + (ctx.close - ctx.open) + corr(ctx.close, ctx.open, corr_period)
    )

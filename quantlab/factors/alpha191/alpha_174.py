"""
Alpha191 #174 — 上涨日波动率
========================================

公式:
    SMA(上涨日 STD(CLOSE, 20), 20, 1)

公式解释:
    计算仅在上涨日的20日收盘价标准差的20日SMA平滑。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_std (滚动标准差)
    - sma (指数平滑)

背后逻辑:
    与 Alpha160 类似但计算上涨日的波动率。
    高值表示上涨时价格波动剧烈，
    反映买方力量的不稳定性。

适用场景:
    上涨波动率分析策略。

变种与优化:
    - 可调整窗口期 (20 → 10/30)
    - 使用不同的波动率度量
    - 结合下跌日波动率对比

注意事项:
    - 条件判断导致因子值可能不稳定
    - ewm 从首期开始计算, 无 NaN 预热
    - ts_std(20) 预热 19 期
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_174"]

DIRECTION = 1
DEFAULT_STD_PERIOD = 20
DEFAULT_SMA_N = 20
DEFAULT_SMA_M = 1


def alpha_174(
    ctx: FactorContext,
    std_period: int = DEFAULT_STD_PERIOD,
    sma_n: int = DEFAULT_SMA_N,
    sma_m: int = DEFAULT_SMA_M,
) -> pd.DataFrame:
    """Alpha191 #174: 上涨日波动率。

    公式: SMA(上涨日 STD(CLOSE, std_period), sma_n, sma_m)

    Args:
        ctx: 因子数据上下文
        std_period: 标准差窗口期 (默认 20)
        sma_n: SMA 分母参数 (默认 20)
        sma_m: SMA 分子参数 (默认 1)

    Returns:
        上涨日波动率因子面板 (date × symbol)
    """
    ret = ctx.get_returns()
    close_std = ts_std(ctx.close, std_period)
    # 仅在上涨日保留标准差，否则置为 NaN
    up_std = close_std.where(ret > 0)
    return sma(up_std, sma_n, sma_m)

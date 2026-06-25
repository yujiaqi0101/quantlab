"""
Alpha191 #122 — 排名相关性与价格比时序差
========================================

公式:
    (SMA(SMA(SMA(LOG(CLOSE),13,2),13,2),13,2)
     - SUM(DELAY(LOG(CLOSE),5), 20)/20)
    + CORR(DELAY(CLOSE,5), DELAY(MEAN(VOL,20),5), 230)
    * SUM(DELAY(LOG(CLOSE),5), 230)/230

公式解释:
    三重SMA平滑的log收盘价 与 5日延迟log收盘价的20日均值之差，
    加上 延迟5日的收盘价与延迟5日的20日均量的230日相关性 乘以 延迟5日log收盘价的230日均值。

分类:
    价格 (price)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE/VOLUME（日频，后复权）

算子依赖:
    - delay
    - ts_sum
    - ts_mean
    - corr
    - sma (SMA(x, n, m): EMA-like平滑)

背后逻辑:
    价格长期均值与多重平滑的偏差，结合量价长期相关性。

适用场景:
    长期趋势选股。

变种与优化:
    - 调整SMA窗口
    - 调整长期窗口230

注意事项:
    - 230日窗口要求至少231天数据才能完整
    - 早期数据不足时返回NaN
    - log(CLOSE) 当 close<=0 时为NaN
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_mean, ts_sum

__all__ = ["alpha_122"]

DIRECTION = 1
LONG_WINDOW = 230


def alpha_122(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #122: 排名相关性与价格比时序差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    close = ctx.close
    vol = ctx.volume

    log_close = np.log(close.where(close > 0, np.nan))

    sma1 = sma(log_close, 13, 2)
    sma2 = sma(sma1, 13, 2)
    sma3 = sma(sma2, 13, 2)

    part1 = sma3 - ts_sum(delay(log_close, 5), 20) / 20.0

    part2_corr = corr(delay(close, 5), delay(ts_mean(vol, 20), 5), LONG_WINDOW)
    part2 = part2_corr * ts_sum(delay(log_close, 5), LONG_WINDOW) / float(LONG_WINDOW)

    return part1 + part2

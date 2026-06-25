"""
Alpha191 #26 — 短期均值回复与长期量价相关复合
========================================

公式:
    ((SUM(CLOSE,7)/7) - CLOSE) + CORR(VWAP, DELAY(CLOSE,5), 230)

公式解释:
    计算7日均价与当前收盘价之差（均值回复项），加上VWAP与5日前收盘价
    的230日相关系数（长期量价关系项）。

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VWAP 日内成交均价（日频，缺失时用 amount/volume 近似）

算子依赖:
    - ts_sum
    - delay
    - corr (滚动相关)

背后逻辑:
    短期均值回复项（价格低于均价）偏好价格低于均值的标的，长期相关系数项
    提供额外的趋势确认。两者结合形成中短期均值回复信号。

适用场景:
    中短期均值回复策略。

变种与优化:
    - 可调整各窗口期 (7/230)
    - 使用不同的长期信号
    - 标准化两项以消除量纲差异

注意事项:
    - 230日相关系数需较长历史数据
    - 短期项与长期项量纲不同，需注意
    - 前 234 期数据不足时返回 NaN (5日延迟 + 230日相关)
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_026"]

DIRECTION = 1
DEFAULT_SHORT_PERIOD = 7
DEFAULT_DELAY_PERIOD = 5
DEFAULT_CORR_PERIOD = 230


def alpha_026(
    ctx: FactorContext,
    short_period: int = DEFAULT_SHORT_PERIOD,
    delay_period: int = DEFAULT_DELAY_PERIOD,
    corr_period: int = DEFAULT_CORR_PERIOD,
) -> pd.DataFrame:
    """Alpha191 #26: 短期均值回复与长期量价相关复合。

    公式: (MEAN(CLOSE,short_period)-CLOSE) + CORR(VWAP,DELAY(CLOSE,delay_period),corr_period)

    Args:
        ctx: 因子数据上下文
        short_period: 均值窗口期 (默认 7)
        delay_period: 收盘价延迟窗口期 (默认 5)
        corr_period: 相关系数窗口期 (默认 230)

    Returns:
        复合均值回复因子面板 (date × symbol)
    """
    close = ctx.close
    vwap = ctx.get_vwap()
    mean_revert = ts_sum(close, short_period) / short_period - close
    long_corr = corr(vwap, delay(close, delay_period), corr_period)
    return mean_revert + long_corr

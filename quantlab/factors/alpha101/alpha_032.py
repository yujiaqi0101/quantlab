"""
Alpha101 #32 — 均线偏离-量价相关
========================================

公式:
    scale(((sum(close, 7) / 7) - close)) + (20 * scale(correlation(vwap, delay(close, 5), 230)))

公式解释:
    7 日均线与收盘价的偏离 (缩放后) 加上 20 倍的 VWAP 与 5 日延迟收盘价的 230 日相关性 (缩放后)。
    结合短期均值回归和长期量价关系。

分类:
    均线偏离-量价相关 (ma_deviation_price_corr)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - VWAP 成交量加权均价（日频）

算子依赖:
    - ts_sum
    - delay
    - corr
    - scale

背后逻辑:
    7 日均线偏离反映短期超买/超卖，
    230 日量价相关性反映长期量价趋势一致性。
    短期反转叠加长期量价确认，
    20 倍权重强调长期趋势。

适用场景:
    短期反转与长期量价趋势的结合策略。

变种与优化:
    - 可调整窗口 (7/230 → 5/120)
    - 可调整权重 (20 → 动态)
    - 可用 decay_linear 平滑

注意事项:
    - 前 235 期返回 NaN (delay 5 + corr 230)
    - 230 日长窗口需足够历史数据
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import scale
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delay, ts_sum

__all__ = ["alpha_032"]

DIRECTION = 1


def alpha_032(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #32: 均线偏离-量价相关。

    公式: scale(sum(close,7)/7 - close) + 20*scale(corr(vwap, delay(close,5), 230))

    Args:
        ctx: 因子数据上下文

    Returns:
        均线偏离-量价相关因子面板 (date × symbol)
    """
    close = ctx.close
    vwap = ctx.get_vwap()
    ma7_dev = scale(ts_sum(close, 7) / 7 - close)
    long_corr = scale(corr(vwap, delay(close, 5), 230))
    return ma7_dev + 20 * long_corr

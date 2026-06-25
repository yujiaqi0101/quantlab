"""
Alpha191 #137 — Wilder 标准化波动率
========================================

公式:
    16 * (价格变化) / TR * MAX(|H-prevC|, |L-prevC|)

公式解释:
    计算价格变化除以真实波幅 (TR)，乘以 16 倍的最大方向性变动 (|H-prevC| 或 |L-prevC|)。
    价格变化通常取 CLOSE - DELAY(CLOSE, 1)。
    TR = MAX(H-L, |H-prevC|, |L-prevC|)。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - tr (真实波幅)
    - delay
    - delta

背后逻辑:
    该因子将价格变动用真实波幅和方向性变动进行双重标准化，
    得到一个标准化的波动率度量。
    Wilder 提出的 TR 概念用于衡量真实的价格波动幅度。

适用场景:
    标准化波动率策略，跨标的波动率比较。

变种与优化:
    - 可调整常数因子 (16)
    - 使用不同的标准化方式
    - 加入波动率分位数确认

注意事项:
    - TR 为零时需特殊处理 (停牌或一字板)
    - 首期返回 NaN (无前一日收盘价)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.misc import tr
from quantlab.factors.operators.ts import delay, delta

__all__ = ["alpha_137"]

DIRECTION = 1


def alpha_137(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #137: Wilder 标准化波动率。

    公式: 16 * (CLOSE - DELAY(CLOSE,1)) / TR * MAX(|H-prevC|, |L-prevC|)

    Args:
        ctx: 因子数据上下文

    Returns:
        Wilder 标准化波动率因子面板 (date × symbol)
    """
    close = ctx.close
    high = ctx.high
    low = ctx.low
    prev_close = delay(close, 1)
    price_change = delta(close, 1)
    true_range = tr(high, low, prev_close)
    # MAX(|H-prevC|, |L-prevC|)
    hc = (high - prev_close).abs()
    lc = (low - prev_close).abs()
    direction_max = np.maximum(hc, lc)
    # 避免除零
    true_range = true_range.replace(0, np.nan)
    return 16 * price_change / true_range * direction_max

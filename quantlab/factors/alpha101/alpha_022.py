"""
Alpha101 #22 — 量价相关变化-波动率
========================================

公式:
    -1 * (delta(correlation(high, volume, 5), 5) * rank(stddev(close, 20)))

公式解释:
    最高价与成交量 5 日相关系数的 5 日变化量，乘以收盘价 20 日标准差的截面排名，取负。

分类:
    量价相关变化-波动率 (volume_price_corr_change_volatility)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - corr
    - delta
    - ts_std (stddev)
    - rank (截面)

背后逻辑:
    量价相关性变化反映市场情绪转变。相关性上升 (量价同步增强) 通常预示趋势延续，
    结合波动率排名取负，意味着高波动环境下量价同步上升看空 (可能见顶)。

适用场景:
    量价关系变化与波动率联合判断的反转策略。

变种与优化:
    - 可替换为 close 或 low 的相关性
    - 可使用其他相关性变化的度量方式
    - 可用 ATR 替代 stddev

注意事项:
    - 双重窗口 (5 + 5 + 20) 导致预热期较长
    - 前 10 期返回 NaN (corr 5 + delta 5)
    - 高波动时因子值放大
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import delta, ts_std

__all__ = ["alpha_022"]

DIRECTION = -1


def alpha_022(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #22: 量价相关变化-波动率。

    公式: -1 * (delta(corr(high, volume, 5), 5) * rank(stddev(close, 20)))

    Args:
        ctx: 因子数据上下文

    Returns:
        量价相关变化-波动率因子面板 (date × symbol)
    """
    corr_hv = corr(ctx.high, ctx.volume, 5)
    delta_corr = delta(corr_hv, 5)
    vol_rank = rank(ts_std(ctx.close, 20))
    return -1 * (delta_corr * vol_rank)

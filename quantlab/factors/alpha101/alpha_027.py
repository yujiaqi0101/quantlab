"""
Alpha101 #27 — 量价相关性阈值
========================================

公式:
    (0.5 < rank(sum(correlation(rank(volume), rank(vwap), 6), 2) / 2.0)) ? -1 : 1

公式解释:
    成交量排名与 VWAP 排名的 6 日相关系数取 2 日平均，
    排名超过 0.5 时做空 (-1)，否则做多 (+1)。
    基于量价相关性的二值信号。

分类:
    量价相关性阈值 (volume_price_corr_threshold)

信号方向:
    正向 (+1) — 因子值越大越看好 (此处为二值信号)

数据来源与频率:
    - VOLUME 成交量（日频）
    - VWAP 成交量加权均价（日频，缺失时由 amount/volume 近似）

算子依赖:
    - rank (截面)
    - corr
    - ts_sum

背后逻辑:
    量价排名相关性的 2 日均值反映短期量价关系强度。
    强相关 (>0.5) 时量价同向明显，看空 (反转)；
    弱相关时看多。
    二值信号简单但鲁棒。

适用场景:
    量价关系强弱的二元判断策略。

变种与优化:
    - 可改为连续信号 (如 rank 值本身)
    - 可使用多阈值
    - 可调整窗口 (6/2 → 10/5)

注意事项:
    - 前 7 期返回 NaN (corr 6 + ts_sum 2 - 重叠)
    - 二值信号损失幅度信息
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_027"]

DIRECTION = 1


def alpha_027(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #27: 量价相关性阈值。

    公式: (0.5 < rank(sum(corr(rank(volume), rank(vwap), 6), 2)/2.0)) ? -1 : 1

    Args:
        ctx: 因子数据上下文

    Returns:
        量价相关性阈值因子面板 (date × symbol)
    """
    vwap = ctx.get_vwap()
    c = corr(rank(ctx.volume), rank(vwap), 6)
    avg = ts_sum(c, 2) / 2.0
    r = rank(avg)
    # rank > 0.5 → -1, 否则 → 1
    result = pd.DataFrame(
        1.0, index=ctx.close.index, columns=ctx.close.columns
    )
    result = result.where(r <= 0.5, -1.0)
    return result.where(r.notna())

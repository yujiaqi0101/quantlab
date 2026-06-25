"""
Alpha101 #28 — 均价-收盘价偏离 (adv20)
========================================

公式:
    scale(((correlation(adv20, low, 5) + ((high + low) / 2)) - close))

公式解释:
    20 日均量与最低价的 5 日相关系数加上高低价中位数，减去收盘价，再缩放。
    综合量价相关性和价格位置。

分类:
    均价-收盘价偏离 (avg_close_deviation)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - ADV20 20 日平均成交量（由 volume 派生）
    - LOW 最低价（日频，后复权）
    - HIGH 最高价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - corr
    - scale
    - ctx.get_adv

背后逻辑:
    量价相关性反映成交活跃度与价格的协同，
    高低价中位数反映日内价格中枢，
    减去收盘价衡量收盘价相对中枢的偏离。
    偏离为正 (收盘价低于中枢) 时看多。

适用场景:
    量价关系 + 价格位置组合策略。

变种与优化:
    - 可用 vwap 替代 (high+low)/2
    - 可调整相关性窗口 (5 → 10)
    - 可引入 decay_linear 平滑

注意事项:
    - 前 24 期返回 NaN (adv20 20 + corr 5 - 重叠)
    - scale 对截面分布敏感
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import scale
from quantlab.factors.operators.stats import corr

__all__ = ["alpha_028"]

DIRECTION = 1


def alpha_028(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #28: 均价-收盘价偏离 (adv20)。

    公式: scale(corr(adv20, low, 5) + (high+low)/2 - close)

    Args:
        ctx: 因子数据上下文

    Returns:
        均价-收盘价偏离因子面板 (date × symbol)
    """
    adv20 = ctx.get_adv(20)
    return scale(corr(adv20, ctx.low, 5) + (ctx.high + ctx.low) / 2 - ctx.close)

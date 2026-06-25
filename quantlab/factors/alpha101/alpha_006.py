"""
Alpha101 #6 — 开盘价-成交量负相关
========================================

公式:
    -1 * correlation(open, volume, 10)

公式解释:
    计算开盘价与成交量的 10 日滚动皮尔逊相关系数，取负值。

分类:
    量价相关性 (volume_price_correlation)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - OPEN 开盘价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - corr (滚动相关)

背后逻辑:
    捕捉开盘价与成交量之间的反向关系。正相关高 (量价齐升) 时取负后因子值低，
    看空；负相关高 (放量下跌) 时取负后因子值高，看多。
    比 Alpha#3 更简洁 (未用 rank)，但可能受极端值影响更大。

适用场景:
    量价背离策略，捕捉开盘价与成交量的反向关系。

变种与优化:
    - 可替换价格字段 (close/high/low)
    - 可加入 rank 处理增强稳健性
    - 可使用 Spearman 秩相关替代 Pearson 相关

注意事项:
    - 未做 rank 处理，受极端值影响较大
    - 前 10 期数据不足返回 NaN
    - 成交量为 0 时相关系数异常，需做下限处理
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.stats import corr

__all__ = ["alpha_006"]

DIRECTION = -1
DEFAULT_PERIOD = 10


def alpha_006(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha101 #6: 开盘价-成交量负相关。

    公式: -1 * correlation(open, volume, period)

    Args:
        ctx: 因子数据上下文
        period: 滚动相关窗口 (默认 10)

    Returns:
        负相关因子面板 (date × symbol)
    """
    return -1 * corr(ctx.open, ctx.volume, period)

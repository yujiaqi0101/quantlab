"""
Alpha101 #40 — 波动率-量价相关
========================================

公式:
    -1 * rank(stddev(high, 10)) * correlation(high, volume, 10)

公式解释:
    最高价 10 日标准差排名取负，乘以最高价与成交量的 10 日相关系数。
    低波动且量价高度相关时因子值较低。

分类:
    波动率-量价相关 (volatility_volume_corr)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - VOLUME 成交量（日频）

算子依赖:
    - ts_std (stddev)
    - rank (截面)
    - corr

背后逻辑:
    低波动 (stddev 低) + 量价正相关 (corr 高) → -rank 低 * corr 高 = 负值低 → 看多。
    这种组合代表平稳上涨 (低波动 + 量价同步)，是趋势延续信号。

适用场景:
    低波动趋势策略，捕捉平稳量价同步的标的。

变种与优化:
    - 可使用 close/low 替代 high
    - 可引入 ATR 或其他波动率度量
    - 可调整窗口 (10 → 5/20)

注意事项:
    - 前 10 期返回 NaN (ts_std + corr)
    - 高波动时因子值放大
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_040"]

DIRECTION = -1


def alpha_040(ctx: FactorContext) -> pd.DataFrame:
    """Alpha101 #40: 波动率-量价相关。

    公式: -1 * rank(stddev(high, 10)) * corr(high, volume, 10)

    Args:
        ctx: 因子数据上下文

    Returns:
        波动率-量价相关因子面板 (date × symbol)
    """
    return -1 * rank(ts_std(ctx.high, 10)) * corr(ctx.high, ctx.volume, 10)

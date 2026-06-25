"""
Alpha191 #185 — 排名时序差
========================================

公式:
    RANK(-1 * ((1 - (OPEN/CLOSE))^1))

公式解释:
    计算 1 - OPEN/CLOSE
    取其相反数
    进行截面排名

分类:
    均值回复 (mean_reversion)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - OPEN/CLOSE（日频，后复权）

算子依赖:
    - rank

背后逻辑:
    当日开盘-收盘比率的反向排名，反映日内方向。

适用场景:
    短期均值回复策略。

变种与优化:
    - 调整幂次 1
    - 替换为 (close-open)

注意事项:
    - 分母为 0 时返回 NaN
    - 首期即可计算
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank

__all__ = ["alpha_185"]

DIRECTION = 1


def alpha_185(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #185: 排名时序差。

    Args:
        ctx: 因子数据上下文

    Returns:
        因子面板 (date × symbol)
    """
    open_ = ctx.open
    close = ctx.close

    safe_close = close.where(close.abs() > 0, np.nan)
    return rank(-1.0 * (1.0 - open_ / safe_close))

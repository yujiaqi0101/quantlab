"""
Alpha191 #54 — 低波动稳定方向因子
========================================

公式:
    -1 * RANK( (STD(|CLOSE-OPEN|, 10) + (CLOSE-OPEN)) + CORR(CLOSE, OPEN, 10) )

公式解释:
    计算收盘价与开盘价绝对差的 10 日标准差，加上当日收盘价与开盘价之差，
    再加上收盘价与开盘价的 10 日相关系数，最后截面排名取负值。

分类:
    波动率 (volatility)

信号方向:
    反向 (-1) — 因子值越小越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）
    - OPEN 开盘价（日频，后复权）

算子依赖:
    - ts_std
    - corr
    - rank

背后逻辑:
    综合价格振幅波动率 (STD|C-O|)、日内方向 (C-O) 与日内方向稳定性 (CORR(C,O))。
    三者之和越大说明波动大且方向不稳定，取负值偏好低波动且方向稳定的股票。

适用场景:
    低波动选股策略，偏好日内价格行为平稳的标的。

变种与优化:
    - 可调整窗口期 (10 → 20)
    - 可对三个子信号做标准化再合成
    - 可使用振幅 (HIGH-LOW) 替代 |C-O|

注意事项:
    - 三个子信号量纲不同 (价格差 / 价格差 / 相关系数)，合成前建议标准化
    - 前 10 期数据不足返回 NaN，回测引擎自动跳过预热期
    - 需使用后复权价格
"""
from __future__ import annotations

import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.cross_section import rank
from quantlab.factors.operators.stats import corr
from quantlab.factors.operators.ts import ts_std

__all__ = ["alpha_054"]

DIRECTION = -1
DEFAULT_PERIOD = 10


def alpha_054(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #54: 低波动稳定方向因子。

    公式: -1 * RANK( (STD(|CLOSE-OPEN|, period) + (CLOSE-OPEN)) + CORR(CLOSE, OPEN, period) )

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 10)

    Returns:
        反向波动率因子面板 (date × symbol)
    """
    c_o = ctx.close - ctx.open
    abs_c_o = (c_o).abs()
    combined = ts_std(abs_c_o, period) + c_o + corr(ctx.close, ctx.open, period)
    return -1 * rank(combined)

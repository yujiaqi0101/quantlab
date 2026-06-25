"""
Alpha191 #158 — 振幅比率
========================================

公式:
    (HIGH - LOW) / CLOSE

公式解释:
    计算当日振幅 (最高价-最低价) 除以收盘价。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    无 (基础算术)

背后逻辑:
    振幅比率衡量当日价格波动的相对幅度。
    高值表示价格波动剧烈。

适用场景:
    波动率选股策略。

变种与优化:
    - 可使用多日平均振幅 (ts_mean)
    - 使用不同的标准化方式 (如 vwap)
    - 加入波动率分位数确认

注意事项:
    - 单日振幅噪声较大，建议使用多日平均
    - 收盘价为 0 时需特殊处理
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np

from quantlab.factors.context import FactorContext

__all__ = ["alpha_158"]

DIRECTION = 1


def alpha_158(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #158: 振幅比率。

    公式: (HIGH - LOW) / CLOSE

    Args:
        ctx: 因子数据上下文

    Returns:
        振幅比率因子面板 (date × symbol)
    """
    close = ctx.close.replace(0, np.nan)
    return (ctx.high - ctx.low) / close

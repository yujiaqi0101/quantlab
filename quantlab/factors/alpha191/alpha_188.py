"""
Alpha191 #188 — 振幅偏离率
========================================

公式:
    ((H - L - SMA(H - L, 11, 2)) / SMA(H - L, 11, 2)) * 100

公式解释:
    计算当日振幅减去11日振幅SMA的差，
    除以11日振幅SMA乘以100。
    SMA(X, n, m) 为指数平滑: alpha=m/n。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - sma (Alpha191 指数平滑)

背后逻辑:
    该因子衡量当前振幅偏离近期平均振幅的程度。
    正值表示振幅扩大，负值表示振幅缩小。

适用场景:
    振幅变化策略，捕捉波动率扩张信号。

变种与优化:
    - 可调整窗口期 (11 → 其他)
    - 使用不同的振幅定义 (如 TR)
    - 加入波动率分位数确认

注意事项:
    - 分母为零时需特殊处理
    - SMA 预热期较短，但建议至少 11 期
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.smooth import sma

__all__ = ["alpha_188"]

DIRECTION = 1


def alpha_188(ctx: FactorContext) -> pd.DataFrame:
    """Alpha191 #188: 振幅偏离率。

    公式: ((H-L - SMA(H-L,11,2)) / SMA(H-L,11,2)) * 100

    Args:
        ctx: 因子数据上下文

    Returns:
        振幅偏离率因子面板 (date × symbol)
    """
    hl = ctx.high - ctx.low
    sma_hl = sma(hl, 11, 2)
    # 分母为零时设为 NaN
    sma_hl = sma_hl.replace(0, np.nan)
    return ((hl - sma_hl) / sma_hl) * 100

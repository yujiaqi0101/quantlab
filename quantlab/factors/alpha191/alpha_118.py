"""
Alpha191 #118 — 上影线/下影线比
========================================

公式:
    SUM(HIGH-OPEN, 20) / SUM(OPEN-LOW, 20) * 100

公式解释:
    计算 20 日内上影线 (HIGH-OPEN) 之和与下影线 (OPEN-LOW) 之和的比值乘以 100。

分类:
    波动率 (volatility)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - HIGH 最高价（日频，后复权）
    - OPEN 开盘价（日频，后复权）
    - LOW 最低价（日频，后复权）

算子依赖:
    - ts_sum

背后逻辑:
    上影线代表日内冲高回落的幅度，下影线代表日内探底回升的幅度。
    比值高表示冲高回落较多，反映上方卖压较大。正向偏好上方卖压
    显著的股票 (可能反映试盘或主力派发)。

适用场景:
    K 线形态分析策略，结合影线不对称性选股。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 可使用 (HIGH-MAX(OPEN,CLOSE)) 替代 (HIGH-OPEN) 更严格的影线定义
    - 可加入振幅加权

注意事项:
    - OPEN=HIGH 或 OPEN=LOW 时该日上影线或下影线为 0
    - 分母 SUM(OPEN-LOW) 为 0 时返回 NaN (避免除零)
    - 需使用后复权价格
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_sum

__all__ = ["alpha_118"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_118(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #118: 上影线/下影线比。

    公式: SUM(HIGH-OPEN, period) / SUM(OPEN-LOW, period) * 100

    Args:
        ctx: 因子数据上下文
        period: 滚动窗口期 (默认 20)

    Returns:
        影线比面板 (date × symbol)
    """
    upper_shadow = ctx.high - ctx.open
    lower_shadow = ctx.open - ctx.low
    sum_upper = ts_sum(upper_shadow, period)
    sum_lower = ts_sum(lower_shadow, period)
    # 分母为 0 时返回 NaN
    sum_lower_safe = sum_lower.where(sum_lower.abs() > 1e-12, np.nan)
    return sum_upper / sum_lower_safe * 100

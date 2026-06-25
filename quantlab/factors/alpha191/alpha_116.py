"""
Alpha191 #116 — 20日收盘价回归斜率
========================================

公式:
    REGBETA(CLOSE, SEQUENCE(20), 20)

公式解释:
    计算收盘价对时间序列 (1,2,...,20) 的20日回归斜率。

分类:
    动量 (momentum)

信号方向:
    正向 (+1) — 因子值越大越看好

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - regbeta (滚动回归斜率)
    - sequence (生成时间序列)

背后逻辑:
    与 Alpha21 类似但使用20日窗口期。
    回归斜率衡量了中期价格趋势的方向和强度。
    正向选择偏好上升趋势的股票。

适用场景:
    中期趋势跟踪策略。

变种与优化:
    - 可调整窗口期 (20 → 10/60)
    - 使用不同的价格基准 (如 VWAP)
    - 加入成交量加权

注意事项:
    - 回归斜率对异常值敏感
    - 长期窗口期估计更稳定
    - 前 19 期返回 NaN (rolling 20)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext

__all__ = ["alpha_116"]

DIRECTION = 1
DEFAULT_PERIOD = 20


def alpha_116(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #116: 20日收盘价回归斜率。

    公式: REGBETA(CLOSE, SEQUENCE(period), period)

    自变量固定为 [1, 2, ..., period]，对每个滚动窗口做 OLS 回归求斜率。

    Args:
        ctx: 因子数据上下文
        period: 回归窗口期 (默认 20)

    Returns:
        回归斜率因子面板 (date × symbol)
    """
    y = ctx.close
    # 自变量 x = [1, 2, ..., period]，每个窗口内固定
    x_arr = np.arange(1, period + 1, dtype=float)
    x_centered = x_arr - x_arr.mean()
    var_x = (x_centered * x_centered).sum()

    out = pd.DataFrame(np.nan, index=y.index, columns=y.columns, dtype=float)
    vals = y.values
    n_rows = vals.shape[0]
    # beta = sum((y_i - y_mean) * x_centered_i) / var_x
    #      = sum(y_i * x_centered_i) / var_x   (因为 sum(x_centered)=0)
    for i in range(period - 1, n_rows):
        window = vals[i - period + 1 : i + 1, :]
        # 跳过含 NaN 的窗口
        valid = ~np.isnan(window).any(axis=0)
        if valid.any():
            beta = (window * x_centered[:, None]).sum(axis=0) / var_x
            out.iloc[i, valid] = beta[valid]
    return out

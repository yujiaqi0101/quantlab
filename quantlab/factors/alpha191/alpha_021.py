"""
Alpha191 #21 — 6日收盘价均值回归斜率
========================================

公式:
    REGBETA(MEAN(CLOSE, 6), SEQUENCE(6))

公式解释:
    计算6日收盘价均值对时间序列 (1,2,...,6) 的滚动回归斜率。

分类:
    动量 (momentum)

信号方向:
    反向 (-1) — 因子值越大越看好（偏好下降趋势标的）

数据来源与频率:
    - CLOSE 收盘价（日频，后复权）

算子依赖:
    - ts_mean
    - regbeta (此处因自变量为固定序列 [1..n]，采用向量化实现)

背后逻辑:
    回归斜率衡量了价格均值的趋势方向和强度。正斜率表示上升趋势，
    负斜率表示下降趋势。反向意味着偏好下降趋势的股票（均值回复逻辑）。
    相比简单的差分动量，回归斜率对窗口内所有点加权，更稳健。

适用场景:
    趋势反转策略。

变种与优化:
    - 可调整窗口期（6日 → 12日/20日）
    - 使用不同的价格基准（如 VWAP）
    - 加入成交量加权

注意事项:
    - 回归斜率对异常值敏感
    - 窗口期过短时估计不稳定
    - 前 11 期数据不足时返回 NaN (MEAN 预热 5 + 回归窗口 6)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from quantlab.factors.context import FactorContext
from quantlab.factors.operators.ts import ts_mean

__all__ = ["alpha_021"]

DIRECTION = -1
DEFAULT_PERIOD = 6


def alpha_021(ctx: FactorContext, period: int = DEFAULT_PERIOD) -> pd.DataFrame:
    """Alpha191 #21: 6日收盘价均值回归斜率。

    公式: REGBETA(MEAN(CLOSE, period), SEQUENCE(period))

    自变量固定为 [1, 2, ..., period]，对每个滚动窗口做 OLS 回归求斜率。

    Args:
        ctx: 因子数据上下文
        period: 回归窗口期 (默认 6)

    Returns:
        回归斜率因子面板 (date × symbol)
    """
    y = ts_mean(ctx.close, period)
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

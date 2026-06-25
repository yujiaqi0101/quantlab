"""
回归算子 (regression operators)
================================

滚动窗口线性回归算子。

算子清单:
    regbeta(y, x, n) — n 期滚动回归 y ~ x 的斜率 (beta)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["regbeta"]


def regbeta(y: pd.DataFrame, x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动回归斜率: y 对 x 的 OLS 斜率 beta。

    对应 Alpha191 的 REGBETA。
    逐列(标的)在滚动窗口 n 内拟合 y = alpha + beta * x + eps，返回 beta。

    公式:
        beta = cov(x, y) / var(x)

    Args:
        y: 因变量面板 (date × symbol)
        x: 自变量面板 (date × symbol, 与 y 对齐)
        n: 滚动窗口 (>=2)

    Returns:
        斜率面板，前 n-1 期为 NaN；x 方差为 0 的窗口返回 NaN
    """
    if n < 2:
        raise ValueError(f"n 必须 >= 2, 实际: {n}")

    x = x.reindex_like(y)

    def _beta(s_y: np.ndarray, s_x: np.ndarray) -> float:
        if len(s_y) < n or np.any(np.isnan(s_y)) or np.any(np.isnan(s_x)):
            return np.nan
        # 中心化
        mx = s_x - s_x.mean()
        var_x = (mx * mx).sum()
        if var_x == 0:
            return np.nan
        my = s_y - s_y.mean()
        cov_xy = (mx * my).sum()
        return cov_xy / var_x

    out = pd.DataFrame(index=y.index, columns=y.columns, dtype=float)
    vals_y = y.values
    vals_x = x.values
    for j in range(y.shape[1]):
        col_y = vals_y[:, j]
        col_x = vals_x[:, j]
        res = np.full(y.shape[0], np.nan)
        for i in range(n - 1, y.shape[0]):
            res[i] = _beta(col_y[i - n + 1 : i + 1], col_x[i - n + 1 : i + 1])
        out.iloc[:, j] = res
    return out

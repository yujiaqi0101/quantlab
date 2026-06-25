"""
平滑算子 (smoothing operators)
================================

指数/加权移动平均算子。

算子清单:
    decay_linear(x, n) — n 日线性衰减加权移动平均 (权重 n,n-1,...,1)
    sma(x, n, m)       — 指数移动平均 (Alpha191 SMA, alpha=m/n)
    wma(x, n)          — 线性加权移动平均 (Alpha191 WMA, 权重线性递减)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["decay_linear", "sma", "wma"]


def decay_linear(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 日线性衰减加权移动平均。

    对应 Alpha191 的 DECAYLINEAR / Alpha101 的 decay_linear。
    权重从 1(最远) 到 n(最近) 线性递增，归一化后加权平均，
    使最近一期权重最大。

    Args:
        x: 输入面板
        n: 窗口

    Returns:
        衰减加权移动平均面板
    """
    # 窗口内 s 按 [最远,...,最近] 排列，最近一期权重最大
    weights = np.arange(1, n + 1, dtype=float)  # 1, 2, ..., n
    weights = weights / weights.sum()
    return x.rolling(n).apply(lambda s: np.dot(s, weights), raw=True)


def sma(x: pd.DataFrame, n: int, m: int = 1) -> pd.DataFrame:
    """指数移动平均 (Alpha191 SMA)。

    递推公式: SMA(t) = (m*X(t) + (n-m)*SMA(t-1)) / n
    平滑系数 alpha = m/n。

    对应 Alpha191 的 SMA(X, n, m)。Alpha101 无对应(其 sma 为简单移动平均)。

    Args:
        x: 输入面板
        n: 分母参数
        m: 分子参数 (默认 1)

    Returns:
        指数平滑面板
    """
    if n <= 0:
        raise ValueError(f"n 必须 > 0, 实际: {n}")
    alpha = m / n
    return x.ewm(alpha=alpha, adjust=False).mean()


def wma(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """线性加权移动平均 (Alpha191 WMA)。

    权重线性递减: 第 n 期(最远)权重 1, 第 1 期(最近)权重 n。
    等价于 decay_linear (两者定义一致, 提供两个别名以对应文档命名)。

    Args:
        x: 输入面板
        n: 窗口

    Returns:
        加权移动平均面板
    """
    return decay_linear(x, n)

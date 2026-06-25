"""
统计算子 (statistical operators)
================================

相关性、协方差等滚动统计算子。

算子清单:
    corr(x, y, n)      — n 期皮尔逊相关系数
    cov(x, y, n)       — n 期协方差
    rsi(close, n)      — n 期 RSI (Alpha191 SMA 指数平滑版)
    ts_corr 同 corr
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["corr", "cov", "rsi"]


def corr(x: pd.DataFrame, y: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动皮尔逊相关系数。

    对应 Alpha191 的 CORR / Alpha101 的 correlation。
    x 与 y 逐列(标的)计算滚动相关。

    Args:
        x: 输入面板 A
        y: 输入面板 B (形状与 x 对齐)
        n: 滚动窗口

    Returns:
        相关系数面板 [-1, 1]
    """
    # 对齐索引
    y = y.reindex_like(x)
    return x.rolling(n).corr(y)


def cov(x: pd.DataFrame, y: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动协方差。

    对应 Alpha191 的 COV/COVARIANCE / Alpha101 的 covariance。

    Args:
        x: 输入面板 A
        y: 输入面板 B
        n: 滚动窗口

    Returns:
        协方差面板
    """
    y = y.reindex_like(x)
    return x.rolling(n).cov(y)


def rsi(close: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期 RSI (相对强弱指标)。

    采用 Alpha191 的 SMA 指数平滑定义:
        UP = max(diff, 0), DOWN = max(-diff, 0)
        RS = SMA(UP, n, 1) / SMA(DOWN, n, 1)
        RSI = 100 - 100 / (1 + RS)

    Args:
        close: 收盘价面板
        n: RSI 窗口

    Returns:
        RSI 面板 [0, 100]，前 n 期可能因预热不足为 NaN
    """
    from quantlab.factors.operators.smooth import sma

    diff = close.diff()
    up = diff.where(diff > 0, 0.0)
    down = (-diff).where(diff < 0, 0.0)
    # diff 为 NaN (序列首值) 时 up/down 应保持 NaN，避免污染 ewm
    up = up.where(diff.notna())
    down = down.where(diff.notna())
    avg_up = sma(up, n, 1)
    avg_down = sma(down, n, 1)
    rs = avg_up / avg_down
    rs = rs.replace([np.inf, -np.inf], np.nan)
    return 100.0 - 100.0 / (1.0 + rs)

"""
时序算子 (time-series operators)
================================

实现 Alpha191 与 Alpha101 文档中的时序算子。
输入输出统一为 pd.DataFrame (index=date, columns=symbol)，沿时间轴(行)计算。

算子清单:
    delay(x, n)        — 延迟 n 期
    delta(x, n)        — 差分: x - delay(x, n)
    ts_rank(x, n)      — 时序排名 (过去 n 期百分位, 0~1)
    ts_max(x, n)       — n 期滚动最大值
    ts_min(x, n)       — n 期滚动最小值
    ts_argmax(x, n)    — n 期最大值出现位置 (0=最近)
    ts_argmin(x, n)    — n 期最小值出现位置 (0=最近)
    ts_sum(x, n)       — n 期滚动求和
    ts_mean(x, n)      — n 期滚动均值 (简单移动平均)
    ts_std(x, n)       — n 期滚动标准差 (样本标准差, ddof=1)
    product(x, n)      — n 期滚动乘积
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = [
    "delay",
    "delta",
    "ts_rank",
    "ts_max",
    "ts_min",
    "ts_argmax",
    "ts_argmin",
    "ts_sum",
    "ts_mean",
    "ts_std",
    "product",
]


def delay(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """时序延迟 n 期: 取 n 期前的值。

    Args:
        x: 输入面板 (date × symbol)
        n: 延迟期数 (n>0)

    Returns:
        延迟后的面板，前 n 期为 NaN
    """
    if n < 0:
        raise ValueError(f"n 必须 >= 0, 实际: {n}")
    return x.shift(n)


def delta(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """时序差分: x - delay(x, n)。

    Args:
        x: 输入面板
        n: 差分期数

    Returns:
        差分后的面板
    """
    return x - delay(x, n)


def ts_rank(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """时序排名: 当前值在过去 n 期中的百分位排名 (0~1)。

    采用平均排名法 (method='average')，与 Alpha 文档定义一致。
    最近一期(当前值)的排名 / n 归一化到 [1/n, 1]。

    若窗口内含 NaN，返回 NaN（排名无意义）。

    Args:
        x: 输入面板
        n: 排名窗口

    Returns:
        排名面板 (0~1)，前 n-1 期或窗口含 NaN 时为 NaN
    """
    if n <= 0:
        raise ValueError(f"n 必须 > 0, 实际: {n}")

    def _rank_pct(s: np.ndarray) -> float:
        if len(s) < n or np.isnan(s).any():
            return np.nan
        order = np.argsort(np.argsort(s))
        return (order[-1] + 1.0) / n  # 当前值(最后)的排名 / n

    return x.rolling(n).apply(_rank_pct, raw=True)


def ts_max(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动最大值。"""
    return x.rolling(n).max()


def ts_min(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动最小值。"""
    return x.rolling(n).min()


def ts_argmax(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期最大值出现位置 (0=最近一期, n-1=最远)。

    对应 Alpha101 的 ts_argmax。
    """
    return x.rolling(n).apply(lambda s: n - 1 - np.argmax(s), raw=True)


def ts_argmin(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期最小值出现位置 (0=最近一期, n-1=最远)。

    对应 Alpha101 的 ts_argmin。
    """
    return x.rolling(n).apply(lambda s: n - 1 - np.argmin(s), raw=True)


def ts_sum(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动求和。"""
    return x.rolling(n).sum()


def ts_mean(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动均值 (简单移动平均)。

    对应 Alpha191 的 MEAN / Alpha101 的 sma。
    """
    return x.rolling(n).mean()


def ts_std(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动标准差 (样本标准差, ddof=1)。

    对应 Alpha191 的 STD / Alpha101 的 stddev。
    """
    return x.rolling(n).std(ddof=1)


def product(x: pd.DataFrame, n: int) -> pd.DataFrame:
    """n 期滚动乘积。

    对应 Alpha101 的 product。
    """
    return x.rolling(n).apply(np.prod, raw=True)

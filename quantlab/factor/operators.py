"""
Operators — V4.6 因子算子

职责：
  - 因子之间的算术运算 (+, -, *, /)
  - 横截面操作 (rank, zscore, quantile)
  - 时序操作 (ts_rank, ts_zscore, ts_delta, ts_mean)
  - 组合因子构造

用法：
    from quantlab.factor.operators import rank, zscore, ts_delta

    # 横截面 rank
    ranked = rank(factor_values_df)   # DataFrame → DataFrame

    # 时序 delta
    delta = ts_delta(series, period=5)  # Series → Series
"""

from __future__ import annotations

from typing import Dict, Optional

import pandas as pd
import numpy as np


# ==================================================================
# 横截面算子（per-bar, cross-symbol）
# ==================================================================

def rank(df: pd.DataFrame, axis: int = 1) -> pd.DataFrame:
    """
    横截面排名

    每根 bar 对所有 symbol 排名（1=最小, N=最大）
    """
    return df.rank(axis=axis, ascending=True)


def zscore(df: pd.DataFrame, axis: int = 1) -> pd.DataFrame:
    """
    横截面 Z-Score 标准化

    每根 bar 对所有 symbol 做 (x - mean) / std
    """
    mean = df.mean(axis=axis)
    std = df.std(axis=axis).replace(0, 1e-9)
    if axis == 1:
        return df.sub(mean, axis=0).div(std, axis=0)
    return df.sub(mean, axis=1).div(std, axis=1)


def quantile(df: pd.DataFrame, q: int = 5, axis: int = 1) -> pd.DataFrame:
    """
    横截面分位数分组

    每根 bar 把 symbol 分成 q 组，返回组号 (1..q)
    """
    return df.rank(axis=axis, pct=True).mul(q).apply(np.ceil).clip(upper=q)


def demean(df: pd.DataFrame, axis: int = 1) -> pd.DataFrame:
    """横截面去均值"""
    mean = df.mean(axis=axis)
    if axis == 1:
        return df.sub(mean, axis=0)
    return df.sub(mean, axis=1)


# ==================================================================
# 时序算子（per-symbol, cross-time）
# ==================================================================

def ts_delta(series: pd.Series, period: int = 1) -> pd.Series:
    """时序差分: x_t - x_{t-period}"""
    return series.diff(period)


def ts_pct_change(series: pd.Series, period: int = 1) -> pd.Series:
    """时序百分比变化"""
    return series.pct_change(period)


def ts_mean(series: pd.Series, period: int = 20) -> pd.Series:
    """时序均值"""
    return series.rolling(period).mean()


def ts_std(series: pd.Series, period: int = 20) -> pd.Series:
    """时序标准差"""
    return series.rolling(period).std()


def ts_rank(series: pd.Series, period: int = 20) -> pd.Series:
    """时序排名: 当前值在过去 period 根 bar 中的排名百分位"""
    return series.rolling(period).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False
    )


def ts_zscore(series: pd.Series, period: int = 20) -> pd.Series:
    """时序 Z-Score: (x - rolling_mean) / rolling_std"""
    m = series.rolling(period).mean()
    s = series.rolling(period).std().replace(0, 1e-9)
    return (series - m) / s


def ts_max(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(period).max()


def ts_min(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(period).min()


def ts_sum(series: pd.Series, period: int = 20) -> pd.Series:
    return series.rolling(period).sum()


def ts_corr(series_a: pd.Series, series_b: pd.Series, period: int = 20) -> pd.Series:
    """时序相关性"""
    return series_a.rolling(period).corr(series_b)


def ts_cov(series_a: pd.Series, series_b: pd.Series, period: int = 20) -> pd.Series:
    """时序协方差"""
    return series_a.rolling(period).cov(series_b)


# ==================================================================
# 因子算术（Series 级别）
# ==================================================================

def factor_add(a: pd.Series, b: pd.Series) -> pd.Series:
    return a + b

def factor_sub(a: pd.Series, b: pd.Series) -> pd.Series:
    return a - b

def factor_mul(a: pd.Series, b: pd.Series) -> pd.Series:
    return a * b

def factor_div(a: pd.Series, b: pd.Series) -> pd.Series:
    return a / b.replace(0, 1e-9)

def factor_abs(a: pd.Series) -> pd.Series:
    return a.abs()

def factor_log(a: pd.Series) -> pd.Series:
    return np.log(a.replace(0, 1e-9))

def factor_sign(a: pd.Series) -> pd.Series:
    return np.sign(a)

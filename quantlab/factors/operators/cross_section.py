"""
截面算子 (cross-sectional operators)
=====================================

沿标的维度(列)计算，在每个时间截面对所有标的排名/缩放。

算子清单:
    rank(x)            — 截面排名 (0~1, method='average')
    scale(x, k)        — 缩放使 sum(abs(x)) = k (默认 k=1)
    ind_neutralize(x)  — 行业中性化 (占位, P3 实现)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["rank", "scale", "ind_neutralize"]


def rank(x: pd.DataFrame) -> pd.DataFrame:
    """截面排名: 在每个时间截面对所有标的按百分位排名 (0~1)。

    对应 Alpha191 的 RANK / Alpha101 的 rank。
    采用平均排名法 (method='average')，与 Alpha101 文档一致。
    最低值→0，最高值→1 (通过 (rank-1)/(n-1) 归一化，n>1 时)。

    Args:
        x: 输入面板 (date × symbol)

    Returns:
        截面排名面板 (0~1)
    """
    ranked = x.rank(axis=1, method="average", pct=True)
    return ranked


def scale(x: pd.DataFrame, k: float = 1.0) -> pd.DataFrame:
    """截面缩放: 使每行 sum(abs(x)) = k。

    对应 Alpha101 的 scale(x, k)。

    Args:
        x: 输入面板
        k: 目标绝对值之和 (默认 1.0)

    Returns:
        缩放后的面板
    """
    abs_sum = x.abs().sum(axis=1)
    # 避免除零
    abs_sum = abs_sum.where(abs_sum > 0, np.nan)
    return x.div(abs_sum, axis=0) * k


def ind_neutralize(
    x: pd.DataFrame, industry_map: dict | None = None
) -> pd.DataFrame:
    """行业中性化: 在每个截面按行业分组去均值。

    对应 Alpha101 的 IndNeutralize。
    P3 阶段完整实现，当前为占位: 若无 industry_map 则返回原值。

    Args:
        x: 输入面板
        industry_map: {symbol: industry} 映射

    Returns:
        行业中性化后的面板
    """
    if industry_map is None:
        return x.copy()
    # 按行业分组去均值
    out = x.copy()
    for _, row in x.iterrows():
        industries = {industry_map.get(sym, "UNK") for sym in row.index}
        for ind in industries:
            cols = [s for s in row.index if industry_map.get(s, "UNK") == ind]
            out.loc[row.name, cols] = row[cols] - row[cols].mean()
    return out

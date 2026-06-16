"""
Factor IC Analysis — 因子 IC 分析

专业量化研究核心功能：

1. IC (Information Coefficient): factor(t) vs return(t+1) 的相关系数
2. Rank IC: factor(t) vs return(t+1) 的 Spearman 相关系数
3. IC 统计: Mean IC, IC IR, IC > 0 比例
4. Factor Correlation: 因子间相关系数矩阵

参考: WorldQuant BRAIN / Barra 风险模型
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.factor.ic_analysis")


def compute_ic(
    factor_values: pd.DataFrame,
    returns: pd.DataFrame,
    method: str = "spearman",
) -> pd.Series:
    """
    计算逐期 IC

    参数:
        factor_values  DataFrame(index=时间, columns=symbols) 因子值
        returns        DataFrame(index=时间, columns=symbols) 下期收益率
        method         "spearman" (Rank IC) 或 "pearson" (Normal IC)

    返回:
        pd.Series(index=时间) 逐期 IC 值
    """
    if method == "spearman":
        ic = factor_values.corrwith(returns, axis=1, method="spearman")
    else:
        ic = factor_values.corrwith(returns, axis=1, method="pearson")
    return ic


def compute_ic_stats(ic_series: pd.Series) -> Dict[str, Any]:
    """
    IC 统计摘要

    返回:
        mean_ic     平均 IC
        ic_std      IC 标准差
        ic_ir       IC 信息比率 (mean / std)
        ic_positive IC > 0 的比例
        ic_t_stat   IC t 统计量
        count       有效期数
    """
    ic = ic_series.dropna()
    if len(ic) == 0:
        return {
            "mean_ic": 0, "ic_std": 0, "ic_ir": 0,
            "ic_positive": 0, "ic_t_stat": 0, "count": 0,
        }

    mean_ic = float(ic.mean())
    ic_std = float(ic.std()) if len(ic) > 1 else 0
    ic_ir = mean_ic / ic_std if ic_std > 1e-9 else 0
    ic_positive = float((ic > 0).mean())
    ic_t_stat = mean_ic / (ic_std / np.sqrt(len(ic))) if ic_std > 1e-9 else 0

    return {
        "mean_ic": round(mean_ic, 4),
        "ic_std": round(ic_std, 4),
        "ic_ir": round(ic_ir, 4),
        "ic_positive": round(ic_positive, 4),
        "ic_t_stat": round(ic_t_stat, 4),
        "count": len(ic),
    }


def compute_factor_correlation(
    factor_data: Dict[str, pd.DataFrame],
    method: str = "spearman",
) -> pd.DataFrame:
    """
    因子间相关系数矩阵

    参数:
        factor_data  {factor_name: DataFrame(index=时间, columns=symbols)}
        method       "spearman" 或 "pearson"

    返回:
        DataFrame(index=factor_name, columns=factor_name) 相关系数矩阵
    """
    # 把每个因子展平成单列（取截面均值的时间序列）
    factor_series: Dict[str, pd.Series] = {}
    for name, df in factor_data.items():
        if isinstance(df, pd.DataFrame):
            factor_series[name] = df.mean(axis=1)
        elif isinstance(df, pd.Series):
            factor_series[name] = df

    if not factor_series:
        return pd.DataFrame()

    combined = pd.DataFrame(factor_series)
    return combined.corr(method=method)


def compute_factor_ic_report(
    factor_values: pd.DataFrame,
    returns: pd.DataFrame,
    factor_name: str = "",
) -> Dict[str, Any]:
    """
    完整的因子 IC 报告

    参数:
        factor_values  DataFrame(index=时间, columns=symbols)
        returns        DataFrame(index=时间, columns=symbols) 下期收益率
        factor_name    因子名称

    返回:
        ic_series      逐期 IC 序列
        ic_stats       IC 统计
        rank_ic_series 逐期 Rank IC 序列
        rank_ic_stats  Rank IC 统计
    """
    # Normal IC
    ic_series = compute_ic(factor_values, returns, method="pearson")
    ic_stats = compute_ic_stats(ic_series)

    # Rank IC
    rank_ic_series = compute_ic(factor_values, returns, method="spearman")
    rank_ic_stats = compute_ic_stats(rank_ic_series)

    return {
        "factor_name": factor_name,
        "ic_series": ic_series,
        "ic_stats": ic_stats,
        "rank_ic_series": rank_ic_series,
        "rank_ic_stats": rank_ic_stats,
    }


def compute_turnover(
    factor_values: pd.DataFrame,
    n_groups: int = 5,
) -> pd.Series:
    """
    因子换手率

    每期将 symbol 分成 n_groups 组，计算 top 组的换手率
    （当期 top 组与上期 top 组不同的比例）

    参数:
        factor_values  DataFrame(index=时间, columns=symbols)
        n_groups       分组数

    返回:
        pd.Series(index=时间) 换手率
    """
    ranks = factor_values.rank(axis=1, ascending=True, pct=True)
    top_group = ranks > (1 - 1 / n_groups)

    turnover = pd.Series(np.nan, index=factor_values.index)
    for i in range(1, len(top_group)):
        prev = top_group.iloc[i - 1]
        curr = top_group.iloc[i]
        common = prev.dropna() & curr.dropna()
        if common.sum() > 0:
            changed = (prev[common] != curr[common]).sum()
            total = common.sum()
            turnover.iloc[i] = changed / total
    return turnover


def compute_coverage(
    factor_values: pd.DataFrame,
) -> pd.Series:
    """
    因子覆盖率（非 NaN 比例）

    参数:
        factor_values  DataFrame(index=时间, columns=symbols)

    返回:
        pd.Series(index=时间) 覆盖率
    """
    total = factor_values.shape[1]
    non_nan = factor_values.notna().sum(axis=1)
    return non_nan / total

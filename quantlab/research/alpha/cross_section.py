"""
Cross Section Alpha — 截面 Alpha 评估

与 Time Series Alpha 的区别：
  - Time Series: 单品种时间序列（RSI<30 → 做多）
  - Cross Section: 多品种截面排序（MomentumRank Top50 → 买入）

核心指标：
  - IC / Rank IC
  - Quantile Return（分组收益）
  - Quantile Spread（Top - Bottom）
  - Long-Short Sharpe

用法：
    evaluator = CrossSectionEvaluator()
    result = evaluator.evaluate(
        factor_values=factor_df,   # DataFrame(index=date, columns=symbols)
        forward_returns=ret_df,    # DataFrame(index=date, columns=symbols)
        n_quantiles=5,
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..alpha.alpha import Alpha, AlphaMetrics, ResearchMode

logger = logging.getLogger("quantlab.alpha.cross_section")


class CrossSectionEvaluator:
    """
    截面 Alpha 评估器

    评估逻辑：
      1. 每期按因子值排序，分成 N 组
      2. 计算每组收益
      3. Top 组 - Bottom 组 = Spread
      4. IC = 因子值与收益的相关系数
    """

    def __init__(self, n_quantiles: int = 5) -> None:
        self._n_quantiles = n_quantiles

    def evaluate(
        self,
        factor_values: pd.DataFrame,
        forward_returns: pd.DataFrame,
        n_quantiles: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        截面评估

        参数:
            factor_values   因子值矩阵 (date × symbol)
            forward_returns 前瞻收益矩阵 (date × symbol)
            n_quantiles     分组数

        返回:
            {
                "ic": 0.05, "rank_ic": 0.07, "ir": 0.8,
                "quantile_returns": {1: 0.001, 2: 0.002, ..., 5: 0.005},
                "quantile_spread": 0.004,
                "long_short_sharpe": 1.2,
                "ic_series": [...],
                "metrics": AlphaMetrics,
            }
        """
        n_q = n_quantiles or self._n_quantiles

        # 对齐
        common_idx = factor_values.index.intersection(forward_returns.index)
        common_cols = factor_values.columns.intersection(forward_returns.columns)
        factor_df = factor_values.loc[common_idx, common_cols]
        ret_df = forward_returns.loc[common_idx, common_cols]

        if factor_df.empty:
            return {"error": "No overlapping data"}

        # 1. IC / Rank IC
        ic_series = self._compute_ic_series(factor_df, ret_df)
        rank_ic_series = self._compute_rank_ic_series(factor_df, ret_df)

        ic_mean = float(ic_series.mean()) if len(ic_series) > 0 else 0.0
        rank_ic_mean = float(rank_ic_series.mean()) if len(rank_ic_series) > 0 else 0.0
        ic_std = float(ic_series.std()) if len(ic_series) > 1 else 1.0
        ir = ic_mean / ic_std if ic_std > 1e-9 else 0.0

        # 2. 分组收益
        quantile_returns = self._compute_quantile_returns(factor_df, ret_df, n_q)

        # 3. Spread
        top_ret = quantile_returns.get(n_q, 0.0)
        bottom_ret = quantile_returns.get(1, 0.0)
        spread = top_ret - bottom_ret

        # 4. Long-Short Sharpe
        ls_returns = self._compute_long_short_returns(factor_df, ret_df, n_q)
        ls_sharpe = 0.0
        if len(ls_returns) > 1:
            ls_mean = ls_returns.mean()
            ls_std = ls_returns.std()
            ls_sharpe = float(ls_mean / ls_std * np.sqrt(252)) if ls_std > 1e-9 else 0.0

        # 5. 构建 AlphaMetrics
        metrics = AlphaMetrics(
            ic=round(ic_mean, 6),
            rank_ic=round(rank_ic_mean, 6),
            ir=round(ir, 4),
            coverage=float((~factor_df.isna()).any(axis=1).mean()),
            quantile_return_top=round(top_ret, 6),
            quantile_return_bottom=round(bottom_ret, 6),
            quantile_spread=round(spread, 6),
            long_short_sharpe=round(ls_sharpe, 4),
            ic_std=round(ic_std, 6),
            ic_positive_ratio=float((ic_series > 0).mean()) if len(ic_series) > 0 else 0.0,
        )

        # 综合评分
        metrics.score = self._compute_score(metrics)

        return {
            "ic": metrics.ic,
            "rank_ic": metrics.rank_ic,
            "ir": metrics.ir,
            "quantile_returns": {k: round(v, 6) for k, v in quantile_returns.items()},
            "quantile_spread": round(spread, 6),
            "long_short_sharpe": round(ls_sharpe, 4),
            "ic_series": ic_series.to_dict(),
            "rank_ic_series": rank_ic_series.to_dict(),
            "metrics": metrics.to_dict(),
        }

    def evaluate_alpha(
        self,
        alpha: Alpha,
        factor_values: pd.DataFrame,
        forward_returns: pd.DataFrame,
    ) -> AlphaMetrics:
        """
        评估单个截面 Alpha，返回 AlphaMetrics

        alpha 的 factor_name 对应 factor_values 中的列
        """
        result = self.evaluate(factor_values, forward_returns)
        if "metrics" in result:
            m = AlphaMetrics.from_dict(result["metrics"])
            return m
        return AlphaMetrics()

    # ---- 内部方法 ----

    def _compute_ic_series(
        self,
        factor_df: pd.DataFrame,
        ret_df: pd.DataFrame,
    ) -> pd.Series:
        """逐期计算 IC（Pearson 相关系数）"""
        ic_list = []
        for date in factor_df.index:
            f = factor_df.loc[date].dropna()
            r = ret_df.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) < 5:
                ic_list.append(np.nan)
                continue
            ic = f[common].corr(r[common])
            ic_list.append(ic)
        return pd.Series(ic_list, index=factor_df.index)

    def _compute_rank_ic_series(
        self,
        factor_df: pd.DataFrame,
        ret_df: pd.DataFrame,
    ) -> pd.Series:
        """逐期计算 Rank IC（Spearman 相关系数）"""
        ric_list = []
        for date in factor_df.index:
            f = factor_df.loc[date].dropna()
            r = ret_df.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) < 5:
                ric_list.append(np.nan)
                continue
            from scipy.stats import spearmanr
            corr, _ = spearmanr(f[common], r[common])
            ric_list.append(corr)
        return pd.Series(ric_list, index=factor_df.index)

    def _compute_quantile_returns(
        self,
        factor_df: pd.DataFrame,
        ret_df: pd.DataFrame,
        n_quantiles: int,
    ) -> Dict[int, float]:
        """计算分组收益"""
        quantile_rets: Dict[int, List[float]] = {q: [] for q in range(1, n_quantiles + 1)}

        for date in factor_df.index:
            f = factor_df.loc[date].dropna()
            r = ret_df.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) < n_quantiles:
                continue

            # 排序分组
            ranked = f[common].rank(pct=True)
            for q in range(1, n_quantiles + 1):
                lower = (q - 1) / n_quantiles
                upper = q / n_quantiles
                mask = (ranked > lower) & (ranked <= upper)
                if mask.any():
                    quantile_rets[q].append(float(r[common][mask].mean()))

        # 平均
        result = {}
        for q, rets in quantile_rets.items():
            result[q] = float(np.mean(rets)) if rets else 0.0

        return result

    def _compute_long_short_returns(
        self,
        factor_df: pd.DataFrame,
        ret_df: pd.DataFrame,
        n_quantiles: int,
    ) -> pd.Series:
        """计算多空收益序列"""
        ls_list = []
        dates = []

        for date in factor_df.index:
            f = factor_df.loc[date].dropna()
            r = ret_df.loc[date].dropna()
            common = f.index.intersection(r.index)
            if len(common) < n_quantiles:
                continue

            ranked = f[common].rank(pct=True)
            # Top 组
            top_mask = ranked > (n_quantiles - 1) / n_quantiles
            # Bottom 组
            bottom_mask = ranked <= 1 / n_quantiles

            top_ret = float(r[common][top_mask].mean()) if top_mask.any() else 0.0
            bottom_ret = float(r[common][bottom_mask].mean()) if bottom_mask.any() else 0.0

            ls_list.append(top_ret - bottom_ret)
            dates.append(date)

        return pd.Series(ls_list, index=dates)

    def _compute_score(self, metrics: AlphaMetrics) -> float:
        """截面 Alpha 综合评分"""
        score = (
            0.25 * min(abs(metrics.ic) / 0.05, 1.0)
            + 0.25 * min(abs(metrics.rank_ic) / 0.07, 1.0)
            + 0.25 * min(abs(metrics.ir) / 0.8, 1.0)
            + 0.25 * min(abs(metrics.quantile_spread) / 0.005, 1.0)
        )
        return round(score, 4)

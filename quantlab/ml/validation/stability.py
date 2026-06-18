"""
Stability Analyzer — 稳定性分析器

ML Lab M3 第三部分：模型必须在不同时间段都稳定

  很多模型：
    Sharpe 2.5（看起来很好）
    但 2020 +50%, 2021 +40%, 2022 -35%, 2023 -30%
    说明非常不稳定

  统计：
    yearly_return
    yearly_ic
    yearly_sharpe

  计算：
    Stability Score = f(正收益年份占比, IC 稳定性, Sharpe 稳定性)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.validation.stability")


@dataclass
class YearlyStat:
    """年度统计"""
    year: str
    n_samples: int = 0
    ic: float = 0.0
    rank_ic: float = 0.0
    sharpe: float = 0.0
    return_mean: float = 0.0     # 信号加权收益均值
    return_std: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "n_samples": self.n_samples,
            "ic": round(self.ic, 6),
            "rank_ic": round(self.rank_ic, 6),
            "sharpe": round(self.sharpe, 6),
            "return_mean": round(self.return_mean, 6),
            "return_std": round(self.return_std, 6),
        }


@dataclass
class StabilityResult:
    """稳定性分析结果"""
    yearly_stats: List[YearlyStat] = field(default_factory=list)
    n_years: int = 0
    # 汇总
    mean_ic: float = 0.0
    std_ic: float = 0.0
    ic_stability: float = 0.0          # mean / std
    mean_sharpe: float = 0.0
    std_sharpe: float = 0.0
    sharpe_stability: float = 0.0
    positive_return_years: int = 0     # 正收益年数
    positive_return_ratio: float = 0.0
    # 综合评分 0~100
    stability_score: float = 0.0
    # 评级
    grade: str = ""                    # A / B / C / D / F

    def to_dict(self) -> Dict[str, Any]:
        return {
            "yearly_stats": [s.to_dict() for s in self.yearly_stats],
            "n_years": self.n_years,
            "mean_ic": round(self.mean_ic, 6),
            "std_ic": round(self.std_ic, 6),
            "ic_stability": round(self.ic_stability, 6),
            "mean_sharpe": round(self.mean_sharpe, 6),
            "std_sharpe": round(self.std_sharpe, 6),
            "sharpe_stability": round(self.sharpe_stability, 6),
            "positive_return_years": self.positive_return_years,
            "positive_return_ratio": round(self.positive_return_ratio, 4),
            "stability_score": round(self.stability_score, 2),
            "grade": self.grade,
        }


class StabilityAnalyzer:
    """
    稳定性分析器

    用法：
        analyzer = StabilityAnalyzer()
        result = analyzer.analyze(predictions, label)
        print(f"Stability Score: {result.stability_score}")
    """

    def analyze(
        self,
        predictions: pd.Series,
        label: pd.Series,
        min_years: int = 2,
    ) -> StabilityResult:
        """
        分析预测的年度稳定性

        Args:
            predictions: 预测值（信号）
            label: 真实收益
            min_years: 最少年份数（不足返回空结果）

        Returns:
            StabilityResult
        """
        result = StabilityResult()

        # 对齐
        common_idx = predictions.index.intersection(label.index)
        if len(common_idx) == 0:
            return result
        preds = predictions.loc[common_idx]
        y = label.loc[common_idx]

        # 确保索引是时间类型
        if not isinstance(preds.index, pd.DatetimeIndex):
            try:
                preds.index = pd.to_datetime(preds.index)
                y.index = pd.to_datetime(y.index)
            except Exception:
                logger.warning("Index is not datetime, cannot group by year")
                return result

        # 按年分组
        try:
            years = preds.index.year
        except AttributeError:
            return result

        yearly_stats: List[YearlyStat] = []
        for year, pred_mask in pd.Series(preds).groupby(years):
            year_preds = preds[pred_mask.index]
            year_label = y[pred_mask.index]
            valid = year_preds.notna() & year_label.notna()
            if valid.sum() < 5:
                continue
            yp = year_preds[valid]
            yl = year_label[valid]

            # 信号加权收益
            strategy_ret = yp * yl

            stat = YearlyStat(
                year=str(year),
                n_samples=int(valid.sum()),
                ic=float(yp.corr(yl)) if yp.std() > 0 else 0.0,
                rank_ic=float(yp.corr(yl, method="spearman")) if yp.std() > 0 else 0.0,
                sharpe=float(
                    strategy_ret.mean() / strategy_ret.std() * np.sqrt(252)
                ) if strategy_ret.std() > 0 else 0.0,
                return_mean=float(strategy_ret.mean()),
                return_std=float(strategy_ret.std()),
            )
            yearly_stats.append(stat)

        if len(yearly_stats) < min_years:
            logger.info(f"Only {len(yearly_stats)} years, need >= {min_years}")
            result.yearly_stats = yearly_stats
            result.n_years = len(yearly_stats)
            return result

        # 汇总
        ics = [s.ic for s in yearly_stats]
        sharpes = [s.sharpe for s in yearly_stats]
        returns = [s.return_mean for s in yearly_stats]

        result.yearly_stats = yearly_stats
        result.n_years = len(yearly_stats)
        result.mean_ic = float(np.mean(ics))
        result.std_ic = float(np.std(ics))
        result.ic_stability = (
            result.mean_ic / result.std_ic if result.std_ic > 0 else 0.0
        )
        result.mean_sharpe = float(np.mean(sharpes))
        result.std_sharpe = float(np.std(sharpes))
        result.sharpe_stability = (
            result.mean_sharpe / result.std_sharpe
            if result.std_sharpe > 0 else 0.0
        )
        result.positive_return_years = sum(1 for r in returns if r > 0)
        result.positive_return_ratio = (
            result.positive_return_years / len(returns) if returns else 0.0
        )

        # 综合评分（0~100）
        result.stability_score = self._compute_score(result)
        result.grade = self._score_to_grade(result.stability_score)

        return result

    def _compute_score(self, result: StabilityResult) -> float:
        """
        计算稳定性评分

        评分组成（各占权重）：
          - 正收益年份占比 40%
          - IC 稳定性（mean/std）30%
          - Sharpe 稳定性 30%
        """
        # 正收益占比分（0~100）
        pos_score = result.positive_return_ratio * 100

        # IC 稳定性分：ic_stability > 1 为良好，> 2 为优秀
        ic_score = min(100, max(0, result.ic_stability * 50))

        # Sharpe 稳定性分
        sharpe_score = min(100, max(0, result.sharpe_stability * 50))

        score = 0.4 * pos_score + 0.3 * ic_score + 0.3 * sharpe_score
        return float(score)

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"

"""
Challenge Comparator — Candidate vs Champion 对比器

从 ValidationReport / PipelineResult 中提取指标进行对比。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .core import (
    MetricComparison,
    ComparisonMetric,
    ChallengeDecision,
    ChallengeResult,
)

logger = logging.getLogger("quantlab.ml.challenge.comparator")


class ChallengeComparator:
    """
    对比器

    用法：
        comparator = ChallengeComparator()
        result = comparator.compare(
            candidate_metrics={"walk_forward_ic": 0.08, "sharpe": 1.2, ...},
            champion_metrics={"walk_forward_ic": 0.06, "sharpe": 1.0, ...},
            metrics=[ComparisonMetric.WALK_FORWARD_IC, ComparisonMetric.SHARPE],
        )
    """

    # 每个指标是否越高越好
    HIGHER_IS_BETTER = {
        ComparisonMetric.WALK_FORWARD_IC: True,
        ComparisonMetric.WALK_FORWARD_RANK_IC: True,
        ComparisonMetric.SHARPE: True,
        ComparisonMetric.MAX_DRAWDOWN: False,      # 回撤越小越好
        ComparisonMetric.ROBUSTNESS_SCORE: True,
        ComparisonMetric.BENCHMARK_SCORE: True,
        ComparisonMetric.IC_STABILITY: True,
        ComparisonMetric.OVERALL_SCORE: True,
    }

    def compare(
        self,
        candidate_metrics: Dict[str, float],
        champion_metrics: Dict[str, float],
        metrics: Optional[List[ComparisonMetric]] = None,
        threshold: float = 0.0,
    ) -> List[MetricComparison]:
        """
        逐项对比

        Args:
            candidate_metrics: Candidate 的指标字典
            champion_metrics: Champion 的指标字典
            metrics: 要对比的指标列表（None 则全部）
            threshold: 超过此阈值才算赢（0 = 只要更好就算赢）

        Returns:
            List[MetricComparison]
        """
        if metrics is None:
            metrics = list(ComparisonMetric)

        comparisons = []
        for metric in metrics:
            metric_key = metric.value
            cand_val = candidate_metrics.get(metric_key, 0.0)
            champ_val = champion_metrics.get(metric_key, 0.0)
            higher_is_better = self.HIGHER_IS_BETTER.get(metric, True)

            delta = cand_val - champ_val

            if higher_is_better:
                candidate_wins = delta > threshold
            else:
                # 越小越好，delta 应为负
                candidate_wins = delta < -threshold

            comparisons.append(MetricComparison(
                metric=metric_key,
                candidate_value=cand_val,
                champion_value=champ_val,
                delta=delta,
                higher_is_better=higher_is_better,
                candidate_wins=candidate_wins,
            ))

        return comparisons

    def extract_metrics_from_pipeline_result(
        self,
        pipeline_result: Any,
    ) -> Dict[str, float]:
        """
        从 PipelineResult 中提取对比指标

        Args:
            pipeline_result: PipelineResult 或 dict

        Returns:
            {metric_name: value}
        """
        result = pipeline_result
        if hasattr(result, "to_dict"):
            result = result.to_dict()

        metrics: Dict[str, float] = {}
        metrics["overall_score"] = result.get("overall_score", 0.0)

        # 从 gate_results 中提取
        for gr in result.get("gate_results", []):
            gate_name = gr.get("gate_name", "")
            details = gr.get("details", {})
            score = gr.get("score", 0.0)

            if gate_name == "walk_forward":
                metrics["walk_forward_ic"] = details.get("avg_ic", 0.0)
                metrics["walk_forward_rank_ic"] = details.get("avg_rank_ic", 0.0)
                metrics["ic_stability"] = details.get("ic_stability", 0.0)
            elif gate_name == "trading":
                metrics["sharpe"] = details.get("sharpe", 0.0)
                metrics["max_drawdown"] = details.get("max_drawdown", 0.0)
            elif gate_name == "robustness":
                metrics["robustness_score"] = score
            elif gate_name == "benchmark":
                metrics["benchmark_score"] = score

        return metrics

    def extract_metrics_from_dict(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        从普通字典中提取指标（兼容旧版 ValidationReport）
        """
        metrics: Dict[str, float] = {}
        metrics["overall_score"] = data.get("model_score", data.get("overall_score", 0.0))

        for item in data.get("items", data.get("gate_results", [])):
            name = item.get("name", item.get("gate_name", ""))
            details = item.get("details", {})
            score = item.get("score", 0.0)

            if name == "walk_forward":
                metrics["walk_forward_ic"] = details.get("avg_ic", 0.0)
                metrics["walk_forward_rank_ic"] = details.get("avg_rank_ic", 0.0)
                metrics["ic_stability"] = details.get("ic_stability", 0.0)
            elif name == "trading":
                metrics["sharpe"] = details.get("sharpe", 0.0)
                metrics["max_drawdown"] = details.get("max_drawdown", 0.0)
            elif name == "robustness":
                metrics["robustness_score"] = score
            elif name == "benchmark":
                metrics["benchmark_score"] = score

        return metrics

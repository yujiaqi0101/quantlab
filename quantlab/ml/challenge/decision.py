"""
Challenge Decision Engine — 决策引擎

根据对比结果决定 PROMOTE / REJECT / INCONCLUSIVE
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .core import (
    ChallengeResult,
    ChallengeDecision,
    MetricComparison,
    ComparisonMetric,
)
from .comparator import ChallengeComparator

logger = logging.getLogger("quantlab.ml.challenge.decision")


class DecisionEngine:
    """
    决策引擎

    规则：
      1. 如果没有 Champion（首次），Candidate 自动晋升
      2. 如果 Candidate 在超过 win_threshold 比例的指标上胜出 → PROMOTE
      3. 如果 Candidate 在关键指标（walk_forward_ic, sharpe）上 FAIL → REJECT
      4. 否则 → INCONCLUSIVE

    用法：
        engine = DecisionEngine()
        decision = engine.decide(comparisons, has_champion=True)
    """

    # 关键指标（必须胜出才能晋升）
    CRITICAL_METRICS = {
        ComparisonMetric.WALK_FORWARD_IC.value,
        ComparisonMetric.SHARPE.value,
    }

    # 默认胜出阈值（超过此比例的指标胜出才晋升）
    DEFAULT_WIN_THRESHOLD = 0.6

    def decide(
        self,
        comparisons: List[MetricComparison],
        has_champion: bool = True,
        win_threshold: float = None,
    ) -> ChallengeDecision:
        """
        做出决策

        Args:
            comparisons: 逐项对比结果
            has_champion: 是否有当前 Champion（False = 首次）
            win_threshold: 胜出比例阈值

        Returns:
            ChallengeDecision
        """
        if win_threshold is None:
            win_threshold = self.DEFAULT_WIN_THRESHOLD

        # 没有 Champion，自动晋升
        if not has_champion:
            return ChallengeDecision.PROMOTE

        n_total = len(comparisons)
        if n_total == 0:
            return ChallengeDecision.INCONCLUSIVE

        n_wins = sum(1 for c in comparisons if c.candidate_wins)
        win_ratio = n_wins / n_total

        # 关键指标检查
        critical_wins = sum(
            1 for c in comparisons
            if c.candidate_wins and c.metric in self.CRITICAL_METRICS
        )
        critical_total = sum(
            1 for c in comparisons
            if c.metric in self.CRITICAL_METRICS
        )

        # 关键指标必须全部胜出
        if critical_total > 0 and critical_wins < critical_total:
            return ChallengeDecision.REJECT

        # 胜出比例达标
        if win_ratio >= win_threshold:
            return ChallengeDecision.PROMOTE

        return ChallengeDecision.INCONCLUSIVE

    def generate_reason(
        self,
        decision: ChallengeDecision,
        comparisons: List[MetricComparison],
        has_champion: bool = True,
    ) -> str:
        """生成决策原因"""
        n_wins = sum(1 for c in comparisons if c.candidate_wins)
        n_total = len(comparisons)

        if decision == ChallengeDecision.PROMOTE:
            if not has_champion:
                return "首次 Champion，自动晋升"
            return f"Candidate 在 {n_wins}/{n_total} 项指标上胜出，关键指标全部通过"

        if decision == ChallengeDecision.REJECT:
            critical_losses = [
                c.metric for c in comparisons
                if not c.candidate_wins and c.metric in self.CRITICAL_METRICS
            ]
            if critical_losses:
                return f"关键指标未通过: {', '.join(critical_losses)}"
            return f"Candidate 仅在 {n_wins}/{n_total} 项指标上胜出"

        return f"无法判定: {n_wins}/{n_total} 项胜出，需要人工审核"

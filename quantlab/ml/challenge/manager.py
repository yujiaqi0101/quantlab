"""
Champion Challenge — 冠军挑战核心类

整合 Comparator + DecisionEngine + Registry

  Candidate → Compare → Champion → Decision → Promote / Reject
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .core import (
    ChallengeResult,
    ChallengeDecision,
    ComparisonMetric,
)
from .comparator import ChallengeComparator
from .decision import DecisionEngine

logger = logging.getLogger("quantlab.ml.challenge")


class ChampionChallenge:
    """
    冠军挑战

    用法：
        challenge = ChampionChallenge(registry)
        result = challenge.challenge(
            candidate_id="MV-new",
            family="LGBM_Momentum",
            candidate_metrics={"walk_forward_ic": 0.08, "sharpe": 1.2},
            metrics=[ComparisonMetric.WALK_FORWARD_IC, ComparisonMetric.SHARPE],
        )
        if result.decision == ChallengeDecision.PROMOTE:
            print("新 Champion 上线！")
    """

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry
        self.comparator = ChallengeComparator()
        self.decision_engine = DecisionEngine()
        self._history: List[ChallengeResult] = []

    def challenge(
        self,
        candidate_id: str,
        family: str,
        candidate_metrics: Dict[str, float],
        champion_metrics: Optional[Dict[str, float]] = None,
        metrics: Optional[List[ComparisonMetric]] = None,
        threshold: float = 0.0,
        win_threshold: float = None,
        auto_promote: bool = True,
    ) -> ChallengeResult:
        """
        发起挑战

        Args:
            candidate_id: Candidate 模型版本 ID
            family: 模型族名
            candidate_metrics: Candidate 的指标
            champion_metrics: 当前 Champion 的指标（None 则从 Registry 获取）
            metrics: 对比维度（None 则全部）
            threshold: 单项指标胜出阈值
            win_threshold: 整体胜出比例阈值
            auto_promote: 是否自动执行晋升操作

        Returns:
            ChallengeResult
        """
        # 获取 Champion 指标
        has_champion = True
        if champion_metrics is None:
            champion_metrics, has_champion = self._get_champion_metrics(family)

        # 逐项对比
        comparisons = self.comparator.compare(
            candidate_metrics=candidate_metrics,
            champion_metrics=champion_metrics,
            metrics=metrics,
            threshold=threshold,
        )

        # 决策
        decision = self.decision_engine.decide(
            comparisons=comparisons,
            has_champion=has_champion,
            win_threshold=win_threshold,
        )

        # 生成原因
        reason = self.decision_engine.generate_reason(
            decision=decision,
            comparisons=comparisons,
            has_champion=has_champion,
        )

        # 统计
        n_wins = sum(1 for c in comparisons if c.candidate_wins)
        n_total = len(comparisons)
        win_ratio = n_wins / n_total if n_total > 0 else 0.0

        result = ChallengeResult(
            family=family,
            candidate_id=candidate_id,
            champion_id=self._get_champion_id(family) if has_champion else "",
            comparisons=comparisons,
            decision=decision,
            reason=reason,
            n_wins=n_wins,
            n_total=n_total,
            win_ratio=win_ratio,
            threshold=threshold,
        )

        # 记录历史
        self._history.append(result)

        # 自动晋升
        if auto_promote and decision == ChallengeDecision.PROMOTE and self.registry:
            self._promote(candidate_id, family, result)

        logger.info(
            f"Challenge {result.challenge_id}: {decision.value} "
            f"({n_wins}/{n_total} wins) - {reason}"
        )

        return result

    def challenge_from_pipeline_result(
        self,
        candidate_id: str,
        family: str,
        candidate_pipeline_result: Any,
        champion_pipeline_result: Any = None,
        metrics: Optional[List[ComparisonMetric]] = None,
        auto_promote: bool = True,
    ) -> ChallengeResult:
        """
        从 PipelineResult 发起挑战

        Args:
            candidate_id: Candidate 模型版本 ID
            family: 模型族名
            candidate_pipeline_result: Candidate 的 PipelineResult
            champion_pipeline_result: 当前 Champion 的 PipelineResult（None 则从 Registry 获取）
            metrics: 对比维度
            auto_promote: 是否自动晋升
        """
        candidate_metrics = self.comparator.extract_metrics_from_pipeline_result(
            candidate_pipeline_result
        )

        champion_metrics = None
        if champion_pipeline_result is not None:
            champion_metrics = self.comparator.extract_metrics_from_pipeline_result(
                champion_pipeline_result
            )

        return self.challenge(
            candidate_id=candidate_id,
            family=family,
            candidate_metrics=candidate_metrics,
            champion_metrics=champion_metrics,
            metrics=metrics,
            auto_promote=auto_promote,
        )

    def get_history(self, family: str = "") -> List[ChallengeResult]:
        """获取挑战历史"""
        if family:
            return [r for r in self._history if r.family == family]
        return list(self._history)

    def get_latest_challenge(self, family: str = "") -> Optional[ChallengeResult]:
        """获取最近一次挑战"""
        history = self.get_history(family)
        return history[-1] if history else None

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _get_champion_metrics(self, family: str) -> tuple[Dict[str, float], bool]:
        """从 Registry 获取当前 Champion 的指标"""
        if self.registry is None:
            return {}, False

        try:
            champion = self.registry.get_champion(family)
            if champion is None:
                return {}, False

            # 从 ModelVersion 的 metrics 中提取
            metrics: Dict[str, float] = {}
            m = champion.metrics if hasattr(champion, "metrics") else {}
            metrics["walk_forward_ic"] = m.get("ic", m.get("walk_forward_ic", 0.0))
            metrics["sharpe"] = m.get("sharpe", 0.0)
            metrics["max_drawdown"] = m.get("max_drawdown", 0.0)
            metrics["overall_score"] = m.get("overall_score", m.get("model_score", 0.0))
            metrics["ic_stability"] = m.get("ic_stability", 0.0)
            metrics["robustness_score"] = m.get("robustness_score", 0.0)
            metrics["benchmark_score"] = m.get("benchmark_score", 0.0)
            return metrics, True

        except Exception as e:
            logger.warning(f"Cannot get champion metrics for family '{family}': {e}")
            return {}, False

    def _get_champion_id(self, family: str) -> str:
        """获取当前 Champion ID"""
        if self.registry is None:
            return ""
        try:
            champion = self.registry.get_champion(family)
            if champion and hasattr(champion, "version_id"):
                return champion.version_id
        except Exception:
            pass
        return ""

    def _promote(self, candidate_id: str, family: str, result: ChallengeResult) -> None:
        """执行晋升"""
        if self.registry is None:
            return

        try:
            # 使用 ChampionManager 执行晋升
            from ..registry.champion import ChampionManager
            mgr = ChampionManager(self.registry)
            mgr.promote(candidate_id, reason=f"Challenge {result.challenge_id}: {result.reason}")
            logger.info(f"Promoted {candidate_id} to Champion for family '{family}'")
        except Exception as e:
            logger.error(f"Failed to promote {candidate_id}: {e}")


# 全局单例
_champion_challenge: Optional[ChampionChallenge] = None


def get_champion_challenge(registry: Any = None) -> ChampionChallenge:
    """获取全局 ChampionChallenge 实例"""
    global _champion_challenge
    if _champion_challenge is None:
        _champion_challenge = ChampionChallenge(registry=registry)
    elif registry is not None and _champion_challenge.registry is None:
        _champion_challenge.registry = registry
    return _champion_challenge

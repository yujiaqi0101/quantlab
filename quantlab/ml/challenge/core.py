"""
Champion Challenge — 冠军挑战模块

ML Lab 质量控制中心：

  Candidate → Compare → Current Champion → Decision → Promote / Reject

  不是比较 Accuracy，而是比较：
    WalkForward IC / Sharpe / MaxDD / Robustness / Benchmark

  Registry 中的状态流转：
    VALIDATED → CANDIDATE → CHAMPION (挑战成功)
                          → ARCHIVED (挑战失败)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.ml.challenge")


class ChallengeDecision(str, Enum):
    """挑战决策"""
    PROMOTE = "PROMOTE"       # 晋升为新 Champion
    REJECT = "REJECT"         # 拒绝（保持原 Champion）
    INCONCLUSIVE = "INCONCLUSIVE"  # 无法判定


class ComparisonMetric(str, Enum):
    """对比维度"""
    WALK_FORWARD_IC = "walk_forward_ic"
    WALK_FORWARD_RANK_IC = "walk_forward_rank_ic"
    SHARPE = "sharpe"
    MAX_DRAWDOWN = "max_drawdown"
    ROBUSTNESS_SCORE = "robustness_score"
    BENCHMARK_SCORE = "benchmark_score"
    IC_STABILITY = "ic_stability"
    OVERALL_SCORE = "overall_score"


@dataclass
class MetricComparison:
    """单个指标对比"""
    metric: str = ""
    candidate_value: float = 0.0
    champion_value: float = 0.0
    delta: float = 0.0
    higher_is_better: bool = True
    candidate_wins: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "candidate_value": round(self.candidate_value, 6),
            "champion_value": round(self.champion_value, 6),
            "delta": round(self.delta, 6),
            "higher_is_better": self.higher_is_better,
            "candidate_wins": self.candidate_wins,
        }


@dataclass
class ChallengeResult:
    """
    挑战结果

    包含：
      - candidate_id / champion_id
      - 逐项指标对比
      - 决策（PROMOTE / REJECT / INCONCLUSIVE）
      - 原因
    """
    challenge_id: str = field(default_factory=lambda: f"CHL-{uuid.uuid4().hex[:8]}")
    family: str = ""
    candidate_id: str = ""
    champion_id: str = ""
    comparisons: List[MetricComparison] = field(default_factory=list)
    decision: ChallengeDecision = ChallengeDecision.INCONCLUSIVE
    reason: str = ""
    n_wins: int = 0
    n_total: int = 0
    win_ratio: float = 0.0
    threshold: float = 0.0
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "family": self.family,
            "candidate_id": self.candidate_id,
            "champion_id": self.champion_id,
            "comparisons": [c.to_dict() for c in self.comparisons],
            "decision": self.decision.value,
            "reason": self.reason,
            "n_wins": self.n_wins,
            "n_total": self.n_total,
            "win_ratio": round(self.win_ratio, 4),
            "threshold": self.threshold,
            "created_at": self.created_at,
        }

    def to_summary_text(self) -> str:
        lines = []
        lines.append(f"Challenge: {self.challenge_id}")
        lines.append(f"Family: {self.family}")
        lines.append(f"Candidate: {self.candidate_id}")
        lines.append(f"Champion: {self.champion_id or 'None (first champion)'}")
        lines.append(f"Decision: {self.decision.value}")
        lines.append(f"Wins: {self.n_wins}/{self.n_total} ({self.win_ratio:.0%})")
        lines.append(f"Reason: {self.reason}")
        lines.append("-" * 50)
        for c in self.comparisons:
            winner = "CANDIDATE" if c.candidate_wins else "CHAMPION"
            lines.append(
                f"  {c.metric:<25} "
                f"candidate={c.candidate_value:>10.4f}  "
                f"champion={c.champion_value:>10.4f}  "
                f"delta={c.delta:>+10.4f}  "
                f"→ {winner}"
            )
        return "\n".join(lines)

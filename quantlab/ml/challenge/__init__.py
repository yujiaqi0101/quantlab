"""
Champion Challenge — 冠军挑战模块

ML Lab 质量控制中心：

  Candidate → Compare → Current Champion → Decision → Promote / Reject

  Registry 状态流转：
    VALIDATED → CANDIDATE → CHAMPION (挑战成功)
                          → ARCHIVED (挑战失败)
"""

from .core import (
    ChallengeResult,
    ChallengeDecision,
    ComparisonMetric,
    MetricComparison,
)
from .comparator import ChallengeComparator
from .decision import DecisionEngine
from .manager import ChampionChallenge, get_champion_challenge

__all__ = [
    # Core
    "ChallengeResult",
    "ChallengeDecision",
    "ComparisonMetric",
    "MetricComparison",
    # Comparator
    "ChallengeComparator",
    # Decision
    "DecisionEngine",
    # Manager
    "ChampionChallenge",
    "get_champion_challenge",
]

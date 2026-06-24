"""
Validation Score — 验证评分体系

ML Lab 质量控制中心：

  每个 Gate 产生一个 ValidationScore
  最终汇总成 OverallScore

  评分维度：
    score: 0-100
    grade: A/B/C/D/F
    status: PASS/WARNING/FAIL/SKIP
    weight: 权重（用于加权汇总）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .gate import GateStatus, ValidationLevel, score_to_grade

logger = logging.getLogger("quantlab.ml.validation.pipeline.score")


@dataclass
class ValidationScore:
    """
    单项验证评分

    用法：
        score = ValidationScore(
            gate_name="walk_forward",
            level=ValidationLevel.L3_TIMESERIES,
            score=82.5,
            status=GateStatus.PASS,
            weight=25.0,
            summary="avg_ic=0.08, stability=0.72",
            details={"avg_ic": 0.08, "ic_stability": 0.72},
        )
        print(score.grade)  # "B"
    """
    gate_name: str = ""
    level: ValidationLevel = ValidationLevel.L1_DATA
    score: float = 0.0
    grade: str = "F"
    status: GateStatus = GateStatus.SKIP
    weight: float = 10.0
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status != GateStatus.SKIP and not self.grade:
            self.grade = score_to_grade(self.score, self.status == GateStatus.FAIL)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "level": self.level.value,
            "score": round(self.score, 2),
            "grade": self.grade,
            "status": self.status.value,
            "weight": self.weight,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class OverallScore:
    """
    综合评分

    汇总所有 Gate 的评分，加权计算总分。

    用法：
        overall = OverallScore(name="LGBM_v3")
        overall.add_score(score1)
        overall.add_score(score2)
        overall.compute()
        print(f"Overall: {overall.score} ({overall.grade})")
    """
    name: str = ""
    scores: List[ValidationScore] = field(default_factory=list)
    score: float = 0.0
    grade: str = "F"
    status: GateStatus = GateStatus.SKIP
    passed: bool = False

    def add_score(self, score: ValidationScore) -> None:
        """添加单项评分"""
        # 移除同名旧项
        self.scores = [s for s in self.scores if s.gate_name != score.gate_name]
        self.scores.append(score)

    def compute(self) -> None:
        """计算综合评分"""
        total_score = 0.0
        total_weight = 0.0
        has_fail = False
        has_warning = False

        for s in self.scores:
            if s.status == GateStatus.SKIP:
                continue
            total_score += s.score * s.weight
            total_weight += s.weight
            if s.status == GateStatus.FAIL:
                has_fail = True
            elif s.status == GateStatus.WARNING:
                has_warning = True

        if total_weight > 0:
            self.score = total_score / total_weight
        else:
            self.score = 0.0

        if has_fail:
            self.status = GateStatus.FAIL
            self.passed = False
        elif has_warning:
            self.status = GateStatus.WARNING
            self.passed = True
        else:
            self.status = GateStatus.PASS
            self.passed = True

        self.grade = score_to_grade(self.score, has_fail)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scores": [s.to_dict() for s in self.scores],
            "score": round(self.score, 2),
            "grade": self.grade,
            "status": self.status.value,
            "passed": self.passed,
        }

    def to_summary_text(self) -> str:
        """生成文本摘要"""
        lines = []
        lines.append(f"Model: {self.name}")
        lines.append(f"Overall Score: {self.score:.1f} ({self.grade})")
        lines.append(f"Status: {self.status.value}")
        lines.append(f"Passed: {'YES' if self.passed else 'NO'}")
        lines.append("-" * 50)
        for s in self.scores:
            lines.append(
                f"  [{s.level.value}] {s.gate_name:<20} "
                f"{s.status.value:<8} "
                f"{s.score:>5.1f} ({s.grade})  "
                f"{s.summary}"
            )
        return "\n".join(lines)


# 默认权重配置
DEFAULT_WEIGHTS: Dict[str, float] = {
    # L1
    "data": 10.0,
    # L2
    "training": 10.0,
    # L3
    "leakage": 20.0,           # 泄漏最关键
    "walk_forward": 20.0,      # Walk Forward 最关键
    # L4
    "trading": 15.0,
    # L5
    "robustness": 15.0,
    # L6
    "benchmark": 10.0,
}


def get_default_weights() -> Dict[str, float]:
    """获取默认权重"""
    return dict(DEFAULT_WEIGHTS)

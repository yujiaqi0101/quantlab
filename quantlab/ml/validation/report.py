"""
Validation Report — 验证报告汇总

ML Lab M3 第八部分：所有验证最终汇总

  内容：
    Walk Forward
    Leakage
    Stability
    Regime
    Robustness
    Benchmark

  最终评分：Model Score 0~100

  例如：
    LGBM_v3
    Score: 84
    Leakage:    PASS
    Walk Forward: PASS
    Stability:  PASS
    Regime:     WARNING
    Robustness: PASS
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.ml.validation.report")


class ValidationStatus(str, Enum):
    """单项验证状态"""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class ValidationItem:
    """单项验证结果"""
    name: str = ""
    status: ValidationStatus = ValidationStatus.SKIP
    score: float = 0.0
    grade: str = ""
    summary: str = ""
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "score": round(self.score, 2),
            "grade": self.grade,
            "summary": self.summary,
            "details": self.details,
        }


@dataclass
class ValidationReport:
    """
    完整验证报告

    用法：
        report = ValidationReport(name="LGBM_v3")
        report.set_item("leakage", ValidationStatus.PASS, 95, "A", "No leakage")
        report.set_item("walk_forward", ValidationStatus.PASS, 82, "B", "IC=0.08")
        ...
        report.compute_final_score()
        print(f"Model Score: {report.model_score}")
    """
    name: str = ""
    items: List[ValidationItem] = field(default_factory=list)
    model_score: float = 0.0
    model_grade: str = ""
    overall_status: ValidationStatus = ValidationStatus.SKIP

    # 各项权重（用于计算总分）
    weights: Dict[str, float] = field(default_factory=lambda: {
        "leakage": 25.0,       # 泄漏最关键
        "walk_forward": 25.0,  # Walk Forward 最关键
        "stability": 15.0,
        "regime": 10.0,
        "robustness": 15.0,
        "noise": 5.0,
        "benchmark": 5.0,
    })

    def set_item(
        self,
        name: str,
        status: ValidationStatus,
        score: float = 0.0,
        grade: str = "",
        summary: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """设置单项验证结果"""
        # 移除同名旧项
        self.items = [it for it in self.items if it.name != name]
        self.items.append(ValidationItem(
            name=name,
            status=status,
            score=score,
            grade=grade,
            summary=summary,
            details=details,
        ))

    def compute_final_score(self) -> None:
        """计算最终评分"""
        total_score = 0.0
        total_weight = 0.0
        has_fail = False
        has_warning = False

        for item in self.items:
            weight = self.weights.get(item.name, 0.0)
            if weight == 0:
                continue
            # SKIP 不计入
            if item.status == ValidationStatus.SKIP:
                continue
            total_score += item.score * weight
            total_weight += weight
            if item.status == ValidationStatus.FAIL:
                has_fail = True
            elif item.status == ValidationStatus.WARNING:
                has_warning = True

        if total_weight > 0:
            self.model_score = total_score / total_weight
        else:
            self.model_score = 0.0

        # 整体状态
        if has_fail:
            self.overall_status = ValidationStatus.FAIL
        elif has_warning:
            self.overall_status = ValidationStatus.WARNING
        else:
            self.overall_status = ValidationStatus.PASS

        # 评级
        self.model_grade = self._score_to_grade(self.model_score, has_fail)

    @staticmethod
    def _score_to_grade(score: float, has_fail: bool = False) -> str:
        if has_fail or score < 35:
            return "F"
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "items": [it.to_dict() for it in self.items],
            "model_score": round(self.model_score, 2),
            "model_grade": self.model_grade,
            "overall_status": self.overall_status.value,
            "weights": self.weights,
        }

    def to_summary_text(self) -> str:
        """生成文本摘要"""
        lines = []
        lines.append(f"Model: {self.name}")
        lines.append(f"Score: {self.model_score:.1f} ({self.model_grade})")
        lines.append(f"Overall: {self.overall_status.value}")
        lines.append("-" * 40)
        for item in self.items:
            lines.append(
                f"  {item.name:<15} {item.status.value:<8} "
                f"{item.score:>5.1f} ({item.grade})  {item.summary}"
            )
        return "\n".join(lines)


# ------------------------------------------------------------------
# 便捷构建函数
# ------------------------------------------------------------------

def build_validation_report(
    name: str,
    leakage_report: Optional[Any] = None,
    walk_forward_result: Optional[Any] = None,
    stability_result: Optional[Any] = None,
    regime_result: Optional[Any] = None,
    robustness_result: Optional[Any] = None,
    noise_result: Optional[Any] = None,
    benchmark_report: Optional[Any] = None,
) -> ValidationReport:
    """
    便捷构建完整验证报告

    用法：
        report = build_validation_report(
            name="LGBM_v3",
            leakage_report=leakage,
            walk_forward_result=wf,
            stability_result=stab,
            ...
        )
        print(report.to_summary_text())
    """
    report = ValidationReport(name=name)

    # 1. Leakage
    if leakage_report is not None:
        status = ValidationStatus.PASS if leakage_report.passed else ValidationStatus.FAIL
        score = 100 if leakage_report.passed else 0
        summary = f"critical={leakage_report.n_critical}, warning={leakage_report.n_warning}"
        report.set_item(
            "leakage", status, score, "A" if leakage_report.passed else "F",
            summary, leakage_report.to_dict(),
        )

    # 2. Walk Forward
    if walk_forward_result is not None:
        wf = walk_forward_result
        # IC > 0.05 且 stability > 0.5 为 PASS
        if wf.avg_ic > 0.05 and wf.ic_stability > 0.5:
            status = ValidationStatus.PASS
        elif wf.avg_ic > 0:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAIL
        # 评分：IC 贡献 + 稳定性贡献
        score = min(100, max(0, wf.avg_ic * 500 + wf.ic_stability * 20))
        summary = f"avg_ic={wf.avg_ic:.4f}, stability={wf.ic_stability:.2f}"
        report.set_item(
            "walk_forward", status, score,
            _grade_from_score(score), summary, wf.to_dict(),
        )

    # 3. Stability
    if stability_result is not None:
        s = stability_result
        if s.stability_score >= 65:
            status = ValidationStatus.PASS
        elif s.stability_score >= 40:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAIL
        summary = f"score={s.stability_score:.1f}, positive_years={s.positive_return_ratio:.0%}"
        report.set_item(
            "stability", status, s.stability_score, s.grade,
            summary, s.to_dict(),
        )

    # 4. Regime
    if regime_result is not None:
        r = regime_result
        if r.grade in ("A", "B"):
            status = ValidationStatus.PASS
        elif r.grade == "C":
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAIL
        score = {"A": 95, "B": 75, "C": 55, "D": 35, "F": 15}.get(r.grade, 0)
        summary = f"bull={r.bull_sharpe:.2f}, bear={r.bear_sharpe:.2f}, best={r.best_regime}"
        report.set_item(
            "regime", status, score, r.grade,
            summary, r.to_dict(),
        )

    # 5. Robustness
    if robustness_result is not None:
        rb = robustness_result
        if rb.is_overfit:
            status = ValidationStatus.FAIL
        elif rb.robustness_score >= 65:
            status = ValidationStatus.PASS
        else:
            status = ValidationStatus.WARNING
        summary = f"score={rb.robustness_score:.1f}, overfit={rb.is_overfit}"
        report.set_item(
            "robustness", status, rb.robustness_score, rb.grade,
            summary, rb.to_dict(),
        )

    # 6. Noise
    if noise_result is not None:
        n = noise_result
        if n.noise_score >= 65:
            status = ValidationStatus.PASS
        elif n.noise_score >= 40:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAIL
        summary = f"sensitivity={n.noise_sensitivity:.2f}"
        report.set_item(
            "noise", status, n.noise_score, n.grade,
            summary, n.to_dict(),
        )

    # 7. Benchmark
    if benchmark_report is not None:
        b = benchmark_report
        if b.ml_beats_all:
            status = ValidationStatus.PASS
        elif b.ml_beats_random:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.FAIL
        summary = f"beats_all={b.ml_beats_all}, beats_BH={b.ml_beats_buy_hold}"
        report.set_item(
            "benchmark", status, b.benchmark_score, b.grade,
            summary, b.to_dict(),
        )

    report.compute_final_score()
    return report


def _grade_from_score(score: float) -> str:
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

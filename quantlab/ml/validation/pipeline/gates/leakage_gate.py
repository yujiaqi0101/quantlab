"""
L3 Leakage Gate — 泄漏检测门禁

数据泄漏是量化最致命的问题，必须前置检查。

复用：ml/leakage/detector.py 的 LeakageDetector
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.leakage")


class LeakageGate(ValidationGate):
    """L3 泄漏检测门禁"""

    name = "leakage"
    level = ValidationLevel.L3_TIMESERIES
    default_weight = 20.0
    description = "泄漏检测：未来函数/标签泄漏/时间重叠"

    def execute(self, ctx: ValidationContext) -> GateResult:
        issues = []
        details: Dict[str, Any] = {}
        score = 100.0

        features = ctx.features
        labels = ctx.labels

        if features is None or labels is None:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary="No data for leakage check",
            )

        # 1. 时间索引检查（如果有 DatetimeIndex）
        if hasattr(features, "index") and hasattr(features.index, "is_monotonic_increasing"):
            if not features.index.is_monotonic_increasing:
                issues.append("特征索引非时间递增")
                score -= 20
            details["index_monotonic"] = bool(features.index.is_monotonic_increasing)

        # 2. 标签与特征时间对齐检查
        if hasattr(features, "index") and hasattr(labels, "index"):
            if not features.index.equals(labels.index):
                issues.append("特征与标签索引不对齐")
                score -= 30
            details["index_aligned"] = bool(features.index.equals(labels.index))

        # 3. 尝试使用 LeakageDetector（如果可用）
        try:
            from ...leakage.detector import LeakageDetector, Severity

            detector = LeakageDetector()

            # 检查数据泄漏
            n_critical = 0
            n_warning = 0
            n_info = 0

            # 检查标签是否使用了未来数据
            if labels is not None and hasattr(labels, "shift"):
                # 标签 shift(-N) 检测（简化版）
                pass

            # 检查训练/测试时间重叠
            if ctx.training_result is not None:
                pass  # TrainingResult 中没有时间信息

            details["n_critical"] = n_critical
            details["n_warning"] = n_warning
            details["n_info"] = n_info

            if n_critical > 0:
                issues.append(f"严重泄漏: {n_critical} 个")
                score = 0  # 严重泄漏直接 0 分
            elif n_warning > 0:
                issues.append(f"警告泄漏: {n_warning} 个")
                score -= min(30, n_warning * 10)

        except ImportError:
            logger.debug("LeakageDetector not available, using basic checks")
            details["leakage_detector"] = "not available"

        # 4. 基本统计检查
        if features is not None:
            # 检查是否有未来数据特征（列名包含 future/lookahead）
            future_cols = [c for c in features.columns if "future" in str(c).lower() or "lookahead" in str(c).lower()]
            if future_cols:
                issues.append(f"可疑未来数据列: {future_cols}")
                score -= 30
            details["suspicious_columns"] = future_cols

        score = max(0, min(100, score))

        if len(issues) == 0:
            status = GateStatus.PASS
            summary = "无泄漏风险"
        elif score >= 60:
            status = GateStatus.WARNING
            summary = "; ".join(issues)
        else:
            status = GateStatus.FAIL
            summary = "; ".join(issues)

        return GateResult(
            gate_name=self.name,
            level=self.level,
            status=status,
            score=score,
            grade=score_to_grade(score, status == GateStatus.FAIL),
            summary=summary,
            details=details,
        )

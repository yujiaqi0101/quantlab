"""
L1 Data Gate — 数据验证门禁

验证输入数据是否合法：
  - 缺失值检查
  - 重复样本检查
  - 特征方差检查（常量特征）
  - 标签分布检查

复用：ml/diagnostics/feature_diagnostics.py + label_diagnostics.py
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.data")


class DataGate(ValidationGate):
    """L1 数据验证门禁"""

    name = "data"
    level = ValidationLevel.L1_DATA
    default_weight = 10.0
    description = "数据验证：缺失值/重复/方差/标签分布"

    def execute(self, ctx: ValidationContext) -> GateResult:
        issues = []
        details: Dict[str, Any] = {}
        score = 100.0

        features = ctx.features
        labels = ctx.labels

        # 检查数据是否存在
        if features is None or labels is None:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.FAIL,
                score=0.0,
                grade="F",
                summary="Features or labels is None",
                details={"error": "missing_data"},
            )

        # 1. 缺失值检查
        missing_ratio = features.isnull().mean()
        high_missing = missing_ratio[missing_ratio > 0.5]
        if len(high_missing) > 0:
            issues.append(f"高缺失率特征: {len(high_missing)} 个")
            score -= min(30, len(high_missing) * 5)
        details["max_missing_rate"] = float(missing_ratio.max()) if len(missing_ratio) > 0 else 0.0
        details["n_high_missing_features"] = int(len(high_missing))

        # 2. 重复样本检查
        n_duplicates = features.duplicated().sum()
        dup_ratio = n_duplicates / len(features) if len(features) > 0 else 0
        if dup_ratio > 0.1:
            issues.append(f"重复样本: {n_duplicates} ({dup_ratio:.1%})")
            score -= min(20, dup_ratio * 100)
        details["n_duplicates"] = int(n_duplicates)
        details["duplicate_ratio"] = round(float(dup_ratio), 4)

        # 3. 常量特征检查（方差接近 0）
        variances = features.var(numeric_only=True)
        constant_features = variances[variances < 1e-10]
        if len(constant_features) > 0:
            issues.append(f"常量特征: {len(constant_features)} 个")
            score -= min(20, len(constant_features) * 5)
        details["n_constant_features"] = int(len(constant_features))

        # 4. 标签分布检查
        if labels is not None:
            label_missing = labels.isnull().sum()
            label_missing_rate = label_missing / len(labels) if len(labels) > 0 else 0
            if label_missing_rate > 0.1:
                issues.append(f"标签缺失率: {label_missing_rate:.1%}")
                score -= min(20, label_missing_rate * 100)
            details["label_missing_rate"] = round(float(label_missing_rate), 4)

            # 分类标签检查类别分布
            if ctx.is_classifier and labels.nunique() > 1:
                class_dist = labels.value_counts(normalize=True)
                min_class_ratio = float(class_dist.min())
                if min_class_ratio < 0.05:
                    issues.append(f"类别不平衡: 最小类占比 {min_class_ratio:.1%}")
                    score -= 10
                details["label_class_distribution"] = {str(k): round(float(v), 4) for k, v in class_dist.items()}
                details["min_class_ratio"] = round(min_class_ratio, 4)

        # 5. 样本数检查
        n_samples = len(features)
        if n_samples < 100:
            issues.append(f"样本数过少: {n_samples}")
            score -= 20
        details["n_samples"] = int(n_samples)
        details["n_features"] = int(features.shape[1])

        score = max(0, min(100, score))

        if len(issues) == 0:
            status = GateStatus.PASS
            summary = f"数据合法: {n_samples} 样本, {features.shape[1]} 特征"
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

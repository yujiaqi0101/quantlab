"""
L2 Training Gate — 训练验证门禁

验证模型训练是否正常：
  - Loss / 收敛性
  - Feature Importance 合理性
  - Overfit Ratio（训练集 vs 测试集）

复用：ml/training/job.py 的 TrainingResult
"""

from __future__ import annotations

import logging
import numpy as np
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.training")


class TrainingGate(ValidationGate):
    """L2 训练验证门禁"""

    name = "training"
    level = ValidationLevel.L2_TRAINING
    default_weight = 10.0
    description = "训练验证：Loss/收敛/Overfit Ratio/特征重要性"

    def execute(self, ctx: ValidationContext) -> GateResult:
        issues = []
        details: Dict[str, Any] = {}
        score = 100.0

        training_result = ctx.training_result

        if training_result is None:
            # 没有 TrainingResult，尝试从 model + predictions 推断
            if ctx.predictions is not None and ctx.labels is not None:
                return self._validate_from_predictions(ctx)
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary="No training result available, skipped",
            )

        # 1. 训练状态检查
        tr_status = getattr(training_result, "status", None)
        if tr_status is not None and str(tr_status) == "FAILED":
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.FAIL,
                score=0.0,
                grade="F",
                summary=f"Training failed: {getattr(training_result, 'error', '')}",
            )
        details["training_status"] = str(tr_status) if tr_status else "unknown"

        # 2. 训练/测试样本数
        n_train = getattr(training_result, "n_train_samples", 0)
        n_test = getattr(training_result, "n_test_samples", 0)
        details["n_train_samples"] = n_train
        details["n_test_samples"] = n_test

        if n_train < 50:
            issues.append(f"训练样本过少: {n_train}")
            score -= 20

        # 3. Overfit Ratio（训练 IC vs 测试 IC）
        metrics = getattr(training_result, "metrics", None)
        if metrics is not None:
            train_ic = getattr(metrics, "ic", 0) or 0
            # 如果有训练集 IC 和测试集 IC
            details["train_ic"] = float(train_ic)

            # 检查 IC 是否合理
            if train_ic < 0:
                issues.append(f"训练 IC 为负: {train_ic:.4f}")
                score -= 30
            elif train_ic > 0.5:
                issues.append(f"训练 IC 过高（可能过拟合）: {train_ic:.4f}")
                score -= 15

        # 4. Feature Importance 检查
        fi = getattr(training_result, "feature_importance", None)
        if fi and isinstance(fi, dict) and len(fi) > 0:
            max_importance = max(fi.values())
            n_features = len(fi)
            # 如果单个特征占比超过 80%，可能有问题
            if n_features > 3 and max_importance > 0.8:
                issues.append(f"特征重要性集中: 单特征占比 {max_importance:.1%}")
                score -= 15
            details["n_important_features"] = n_features
            details["max_importance"] = round(float(max_importance), 4)
        else:
            details["feature_importance"] = "not available"

        # 5. 训练时间
        train_time = getattr(training_result, "train_time", 0)
        details["train_time"] = round(float(train_time), 2)

        score = max(0, min(100, score))

        if len(issues) == 0:
            status = GateStatus.PASS
            summary = f"训练正常: {n_train} 训练样本, IC={details.get('train_ic', 'N/A')}"
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

    def _validate_from_predictions(self, ctx: ValidationContext) -> GateResult:
        """从 predictions 推断训练质量"""
        preds = ctx.predictions
        labels = ctx.labels

        if preds is None or labels is None:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary="No predictions or labels for training validation",
            )

        # 检查预测值是否合理
        n_nan = preds.isnull().sum()
        nan_ratio = n_nan / len(preds) if len(preds) > 0 else 0

        details = {
            "n_predictions": int(len(preds)),
            "n_nan_predictions": int(n_nan),
            "nan_ratio": round(float(nan_ratio), 4),
            "pred_mean": round(float(preds.mean()), 6),
            "pred_std": round(float(preds.std()), 6),
        }

        score = 100.0
        issues = []

        if nan_ratio > 0.1:
            issues.append(f"预测值缺失率高: {nan_ratio:.1%}")
            score -= 30

        if preds.std() < 1e-10:
            issues.append("预测值方差为 0（模型可能未学到东西）")
            score -= 40

        score = max(0, min(100, score))

        if len(issues) == 0:
            status = GateStatus.PASS
            summary = f"预测正常: {len(preds)} 样本"
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

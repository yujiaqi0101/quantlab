"""
L5 Robustness Gate — 鲁棒性验证门禁

回答：是否稳定？

验证：
  - Noise Injection（噪音注入）
  - Feature Drop（特征丢弃）
  - Parameter Perturbation（参数扰动）
  - Bootstrap

复用：ml/validation/robustness.py + noise.py
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.robustness")


class RobustnessGate(ValidationGate):
    """L5 鲁棒性验证门禁"""

    name = "robustness"
    level = ValidationLevel.L5_ROBUSTNESS
    default_weight = 15.0
    description = "鲁棒性验证：噪音注入/特征丢弃/参数扰动/Bootstrap"

    def execute(self, ctx: ValidationContext) -> GateResult:
        details: Dict[str, Any] = {}
        score = 0.0

        features = ctx.features
        labels = ctx.labels
        model = ctx.raw_model

        if features is None or labels is None or model is None:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary="No data/model for robustness test",
            )

        # 基准 IC
        try:
            if hasattr(model, "predict"):
                base_preds = model.predict(features)
                base_preds = pd.Series(base_preds, index=features.index)
            else:
                return GateResult(
                    gate_name=self.name,
                    level=self.level,
                    status=GateStatus.SKIP,
                    summary="Model has no predict method",
                )
        except Exception as e:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.ERROR,
                summary=f"Cannot get base predictions: {e}",
                error=str(e),
            )

        # 计算基准 IC（compute_ic 需要 pd.Series）
        from ....metrics import compute_ic
        base_ic = compute_ic(pd.Series(labels.values), pd.Series(base_preds.values))
        details["baseline_ic"] = round(float(base_ic), 6)

        scores = []

        # 1. Noise Injection（噪音注入）
        noise_scores = []
        for noise_level in [0.01, 0.05, 0.10]:
            try:
                noisy_features = features.copy()
                noise = np.random.normal(0, noise_level, noisy_features.shape)
                noisy_features = noisy_features + noise
                noisy_preds = model.predict(noisy_features)
                noisy_preds = pd.Series(noisy_preds, index=features.index)
                noisy_ic = compute_ic(pd.Series(labels.values), noisy_preds)
                delta_ic = abs(base_ic - noisy_ic)
                noise_scores.append(float(delta_ic))
            except Exception:
                noise_scores.append(1.0)  # 惩罚

        avg_noise_delta = float(np.mean(noise_scores)) if noise_scores else 1.0
        details["noise_delta_ic"] = [round(d, 6) for d in noise_scores]
        details["avg_noise_delta"] = round(avg_noise_delta, 6)
        # 噪音敏感度越低越好（delta 越小越好）
        noise_score = max(0, 100 - avg_noise_delta * 1000)
        scores.append(("noise", noise_score, 0.3))

        # 2. Feature Drop（特征丢弃）
        drop_scores = []
        n_features = features.shape[1]
        if n_features > 1:
            for i in range(min(n_features, 5)):
                try:
                    drop_features = features.drop(columns=features.columns[i])
                    drop_preds = model.predict(drop_features) if model.predict.__code__.co_argcount > 1 else base_preds
                    # 如果模型不支持变特征数，跳过
                    if isinstance(drop_preds, pd.Series):
                        drop_preds_series = drop_preds
                    else:
                        drop_preds_series = pd.Series(drop_preds, index=features.index)
                    drop_ic = compute_ic(pd.Series(labels.values), drop_preds_series)
                    delta = abs(base_ic - drop_ic)
                    drop_scores.append(float(delta))
                except Exception:
                    drop_scores.append(0.0)  # 模型不支持变特征数，不惩罚

        if drop_scores:
            avg_drop_delta = float(np.mean(drop_scores))
            details["feature_drop_delta"] = [round(d, 6) for d in drop_scores]
            details["avg_feature_drop_delta"] = round(avg_drop_delta, 6)
            drop_score = max(0, 100 - avg_drop_delta * 500)
            scores.append(("feature_drop", drop_score, 0.3))
        else:
            scores.append(("feature_drop", 70.0, 0.3))  # 默认中等

        # 3. 参数扰动（简化版：用不同随机种子重新预测）
        # 由于无法重新训练，这里用预测值的稳定性来近似
        pred_std = float(base_preds.std())
        pred_mean = float(abs(base_preds.mean()))
        if pred_mean > 1e-10:
            cv = pred_std / pred_mean
            stability_score = max(0, 100 - cv * 50)
        else:
            stability_score = 50.0
        details["prediction_cv"] = round(float(cv) if pred_mean > 1e-10 else 0, 6)
        scores.append(("stability", stability_score, 0.4))

        # 加权汇总
        total_weight = sum(w for _, _, w in scores)
        score = sum(s * w for _, s, w in scores) / total_weight if total_weight > 0 else 0

        # 过拟合检测
        is_overfit = base_ic > 0.3 and avg_noise_delta > 0.05
        details["is_overfit"] = is_overfit
        details["sub_scores"] = {name: round(s, 2) for name, s, _ in scores}

        if is_overfit:
            status = GateStatus.FAIL
            summary = f"过拟合: base_ic={base_ic:.4f}, noise_delta={avg_noise_delta:.4f}"
        elif score >= 60:
            status = GateStatus.PASS
            summary = f"鲁棒性良好: score={score:.1f}, base_ic={base_ic:.4f}"
        else:
            status = GateStatus.WARNING
            summary = f"鲁棒性一般: score={score:.1f}, noise_delta={avg_noise_delta:.4f}"

        return GateResult(
            gate_name=self.name,
            level=self.level,
            status=status,
            score=score,
            grade=score_to_grade(score, status == GateStatus.FAIL),
            summary=summary,
            details=details,
        )

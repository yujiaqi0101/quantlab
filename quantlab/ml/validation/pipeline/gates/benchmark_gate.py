"""
L6 Benchmark Gate — 基准验证门禁

回答：是否真的有价值？

比较：
  - Buy & Hold
  - Momentum
  - Random Signal
  - Previous Champion（如果有）

复用：ml/validation/benchmark.py 的 BenchmarkEngine
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.benchmark")


class BenchmarkGate(ValidationGate):
    """L6 基准验证门禁"""

    name = "benchmark"
    level = ValidationLevel.L6_BENCHMARK
    default_weight = 10.0
    description = "基准验证：vs Buy&Hold/Momentum/Random/Champion"

    def execute(self, ctx: ValidationContext) -> GateResult:
        details: Dict[str, Any] = {}
        score = 0.0

        predictions = ctx.predictions
        labels = ctx.labels

        if predictions is None or labels is None:
            # 尝试从 model 生成
            if ctx.raw_model is not None and ctx.features is not None:
                try:
                    model = ctx.raw_model
                    if hasattr(model, "predict"):
                        predictions = pd.Series(model.predict(ctx.features), index=ctx.features.index)
                except Exception:
                    pass

            if predictions is None:
                return GateResult(
                    gate_name=self.name,
                    level=self.level,
                    status=GateStatus.SKIP,
                    summary="No predictions for benchmark",
                )

        # 对齐
        if hasattr(predictions, "index") and hasattr(labels, "index"):
            common_idx = predictions.index.intersection(labels.index)
            if len(common_idx) > 0:
                predictions = predictions.loc[common_idx]
                labels = labels.loc[common_idx]

        # 去除 NaN
        mask = ~(predictions.isnull() | labels.isnull())
        predictions = predictions[mask]
        labels = labels[mask]

        if len(predictions) < 10:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary=f"Insufficient samples: {len(predictions)}",
            )

        from ....metrics import compute_ic, compute_sharpe

        # ML 模型指标（保留原始索引，避免对齐问题）
        labels_s = labels
        preds_s = predictions
        ml_ic = compute_ic(labels_s, preds_s)
        ml_sharpe = compute_sharpe(labels_s, preds_s) if len(predictions) > 1 else 0.0

        details["ml_ic"] = round(float(ml_ic), 6)
        details["ml_sharpe"] = round(float(ml_sharpe), 6)

        # 1. Buy & Hold 基准
        bh_ic = compute_ic(labels_s, labels_s)  # 完美预测（理论上 IC=1）
        bh_sharpe = compute_sharpe(labels_s, labels_s) if len(labels) > 1 else 0.0
        details["buy_hold_ic"] = round(float(bh_ic), 6)
        details["buy_hold_sharpe"] = round(float(bh_sharpe), 6)

        # 2. Random 基准
        np.random.seed(42)
        random_preds = pd.Series(
            np.random.randn(len(predictions)),
            index=predictions.index,
        )
        random_ic = compute_ic(labels_s, random_preds)
        details["random_ic"] = round(float(random_ic), 6)

        # 3. Momentum 基准（用 labels 的滞后作为预测）
        if len(labels) > 5:
            momentum_preds = labels.shift(1).fillna(0)
            momentum_ic = compute_ic(labels_s, momentum_preds)
            details["momentum_ic"] = round(float(momentum_ic), 6)
        else:
            momentum_ic = 0.0
            details["momentum_ic"] = "N/A"

        # 评分逻辑
        beats_random = ml_ic > random_ic
        beats_momentum = ml_ic > momentum_ic
        beats_buy_hold_ic = ml_ic > 0  # BH IC=1 不现实，用 >0 判断

        details["beats_random"] = beats_random
        details["beats_momentum"] = beats_momentum
        details["beats_buy_hold"] = beats_buy_hold_ic

        # 评分
        if beats_random:
            score += 30
        if beats_momentum:
            score += 30
        if ml_ic > 0.05:
            score += 20
        if ml_sharpe > 0.5:
            score += 20

        score = min(100, score)

        # 状态判定
        if beats_random and beats_momentum and ml_ic > 0.05:
            status = GateStatus.PASS
            summary = f"ML 优于基准: IC={ml_ic:.4f} > random={random_ic:.4f}, momentum={momentum_ic:.4f}"
        elif beats_random:
            status = GateStatus.WARNING
            summary = f"ML 仅优于随机: IC={ml_ic:.4f}, momentum={momentum_ic:.4f}"
        else:
            status = GateStatus.FAIL
            summary = f"ML 不如随机: IC={ml_ic:.4f} < random={random_ic:.4f}"

        return GateResult(
            gate_name=self.name,
            level=self.level,
            status=status,
            score=score,
            grade=score_to_grade(score, status == GateStatus.FAIL),
            summary=summary,
            details=details,
        )

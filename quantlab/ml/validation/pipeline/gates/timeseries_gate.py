"""
L3 Walk Forward Gate — 时间序列验证门禁

量化核心验证：Walk Forward 滚动前进验证。

复用：ml/validation/walk_forward.py 的 WalkForward + ValidationConfig
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.timeseries")


class WalkForwardGate(ValidationGate):
    """L3 时间序列验证门禁（Walk Forward）"""

    name = "walk_forward"
    level = ValidationLevel.L3_TIMESERIES
    default_weight = 20.0
    description = "时间序列验证：Walk Forward 滚动前进验证"

    def execute(self, ctx: ValidationContext) -> GateResult:
        details: Dict[str, Any] = {}
        score = 0.0

        features = ctx.features
        labels = ctx.labels
        model = ctx.raw_model

        if features is None or labels is None:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary="No data for walk forward",
            )

        if model is None:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary="No model for walk forward",
            )

        # 获取 Walk Forward 配置
        wf_config = ctx.walk_forward_config
        if wf_config is None:
            from ...walk_forward import ValidationConfig
            wf_config = ValidationConfig()

        try:
            from ...walk_forward import WalkForward, WalkForwardResult
            from ....model import ModelType

            # 创建 WalkForward 引擎
            wf = WalkForward(wf_config)

            # 解析 model_type
            try:
                model_type = ModelType(ctx.model_type)
            except (ValueError, KeyError):
                model_type = ModelType.LINEAR_REGRESSION

            # 运行 Walk Forward（使用 model_type 接口）
            wf_result = wf.run(
                features=features,
                label=labels,
                model_type=model_type,
                model_params=ctx.model_params or {},
                is_classifier=ctx.is_classifier,
            )

            # 评分逻辑
            avg_ic = wf_result.avg_ic
            avg_rank_ic = wf_result.avg_rank_ic
            ic_stability = wf_result.ic_stability
            n_splits = wf_result.n_splits

            details["n_splits"] = n_splits
            details["avg_ic"] = round(float(avg_ic), 6)
            details["avg_rank_ic"] = round(float(avg_rank_ic), 6)
            details["avg_rmse"] = round(float(wf_result.avg_rmse), 6)
            details["avg_sharpe"] = round(float(wf_result.avg_sharpe), 6)
            details["ic_stability"] = round(float(ic_stability), 4)
            details["fold_details"] = wf_result.fold_details

            # 评分：IC 贡献 + 稳定性贡献
            # IC > 0.05 为有效，> 0.1 为优秀
            # stability > 0.5 为稳定
            ic_score = min(50, max(0, avg_ic * 500))       # IC 最多贡献 50 分
            stability_score = min(30, max(0, ic_stability * 30))  # 稳定性最多 30 分
            rank_ic_score = min(20, max(0, avg_rank_ic * 200))    # Rank IC 最多 20 分
            score = ic_score + stability_score + rank_ic_score

            # 状态判定
            if avg_ic > 0.05 and ic_stability > 0.5:
                status = GateStatus.PASS
                summary = f"avg_ic={avg_ic:.4f}, stability={ic_stability:.2f}, splits={n_splits}"
            elif avg_ic > 0:
                status = GateStatus.WARNING
                summary = f"avg_ic={avg_ic:.4f} (弱), stability={ic_stability:.2f}"
            else:
                status = GateStatus.FAIL
                summary = f"avg_ic={avg_ic:.4f} (无效), stability={ic_stability:.2f}"

            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=status,
                score=score,
                grade=score_to_grade(score, status == GateStatus.FAIL),
                summary=summary,
                details=details,
            )

        except Exception as e:
            logger.exception(f"WalkForwardGate execution error: {e}")
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.ERROR,
                score=0.0,
                grade="F",
                summary=f"Walk Forward error: {e}",
                error=str(e),
            )

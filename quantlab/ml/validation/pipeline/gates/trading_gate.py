"""
L4 Trading Gate — 交易验证门禁

回答：能不能赚钱？

验证指标：
  - IC / Rank IC
  - Sharpe
  - Max Drawdown
  - Turnover
  - Win Rate

复用：ml/metrics/metrics.py
"""

from __future__ import annotations

import logging
import numpy as np
import pandas as pd
from typing import Any, Dict

from ..gate import ValidationGate, GateResult, GateStatus, ValidationLevel, score_to_grade
from ..core import ValidationContext

logger = logging.getLogger("quantlab.ml.validation.pipeline.gates.trading")


class TradingGate(ValidationGate):
    """L4 交易验证门禁"""

    name = "trading"
    level = ValidationLevel.L4_TRADING
    default_weight = 15.0
    description = "交易验证：IC/RankIC/Sharpe/MaxDD/Turnover/WinRate"

    def execute(self, ctx: ValidationContext) -> GateResult:
        details: Dict[str, Any] = {}
        score = 0.0

        predictions = ctx.predictions
        labels = ctx.labels

        if predictions is None or labels is None:
            # 尝试从 model 生成 predictions
            if ctx.raw_model is not None and ctx.features is not None:
                try:
                    model = ctx.raw_model
                    if hasattr(model, "predict"):
                        predictions = pd.Series(model.predict(ctx.features), index=ctx.features.index)
                except Exception as e:
                    return GateResult(
                        gate_name=self.name,
                        level=self.level,
                        status=GateStatus.SKIP,
                        summary=f"Cannot generate predictions: {e}",
                    )
            else:
                return GateResult(
                    gate_name=self.name,
                    level=self.level,
                    status=GateStatus.SKIP,
                    summary="No predictions or labels for trading validation",
                )

        # 对齐索引
        if hasattr(predictions, "index") and hasattr(labels, "index"):
            common_idx = predictions.index.intersection(labels.index)
            if len(common_idx) == 0:
                return GateResult(
                    gate_name=self.name,
                    level=self.level,
                    status=GateStatus.FAIL,
                    score=0.0,
                    grade="F",
                    summary="Predictions and labels have no common index",
                )
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
                status=GateStatus.FAIL,
                score=0.0,
                grade="F",
                summary=f"Insufficient samples: {len(predictions)}",
            )

        try:
            from ....metrics import compute_all_metrics

            metrics = compute_all_metrics(
                y_true=labels.values,
                y_pred=predictions.values,
                is_classifier=ctx.is_classifier,
            )

            # 核心指标
            ic = metrics.ic
            rank_ic = metrics.rank_ic
            sharpe = metrics.sharpe

            details["ic"] = round(float(ic), 6)
            details["rank_ic"] = round(float(rank_ic), 6)
            details["sharpe"] = round(float(sharpe), 6)
            details["rmse"] = round(float(metrics.rmse), 6)
            details["n_samples"] = int(len(predictions))

            # 分类指标
            if ctx.is_classifier:
                details["accuracy"] = round(float(metrics.accuracy), 6)
                details["precision"] = round(float(metrics.precision), 6)
                details["recall"] = round(float(metrics.recall), 6)
                details["auc"] = round(float(metrics.auc), 6)

            # 交易指标（简化版）
            # Turnover: 预测信号变化率
            if len(predictions) > 1:
                signal_changes = predictions.diff().abs()
                turnover = float(signal_changes.mean() / (abs(predictions).mean() + 1e-10))
                details["turnover"] = round(turnover, 6)

            # Win Rate: 预测方向正确的比例
            if not ctx.is_classifier:
                # 回归：预测和真实值同号为正确
                correct = (predictions * labels) > 0
                win_rate = float(correct.mean())
                details["win_rate"] = round(win_rate, 6)

            # Max Drawdown（基于信号加权收益）
            if not ctx.is_classifier and len(predictions) > 1:
                signal_returns = predictions * labels
                cumulative = signal_returns.cumsum()
                running_max = cumulative.expanding().max()
                drawdown = cumulative - running_max
                max_dd = float(drawdown.min())
                details["max_drawdown"] = round(max_dd, 6)

            # 评分逻辑
            # IC 贡献（最多 40 分）
            ic_score = min(40, max(0, ic * 400))
            # Rank IC 贡献（最多 25 分）
            rank_ic_score = min(25, max(0, rank_ic * 250))
            # Sharpe 贡献（最多 20 分）
            sharpe_score = min(20, max(0, sharpe * 15))
            # Win Rate 贡献（最多 15 分）
            win_rate_score = 0
            if "win_rate" in details:
                win_rate_score = min(15, max(0, (details["win_rate"] - 0.5) * 30))

            score = ic_score + rank_ic_score + sharpe_score + win_rate_score

            # 状态判定
            if ic > 0.03 and sharpe > 0.5:
                status = GateStatus.PASS
                summary = f"IC={ic:.4f}, Sharpe={sharpe:.2f}, WinRate={details.get('win_rate', 'N/A')}"
            elif ic > 0:
                status = GateStatus.WARNING
                summary = f"IC={ic:.4f} (弱), Sharpe={sharpe:.2f}"
            else:
                status = GateStatus.FAIL
                summary = f"IC={ic:.4f} (无效), Sharpe={sharpe:.2f}"

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
            logger.exception(f"TradingGate execution error: {e}")
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.ERROR,
                score=0.0,
                grade="F",
                summary=f"Trading validation error: {e}",
                error=str(e),
            )

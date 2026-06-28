"""
模块 11: Signal Explainability

信号溯源解释。
Pipeline 在每一步都把中间状态写入 signal.metadata["explain_trace"]，
Explainer 只是聚合展示，不重新计算。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .signal import Signal

logger = logging.getLogger("quantlab.ml.signal_engine.explainability")


@dataclass
class ExplainTrace:
    """信号溯源链"""

    prediction: Dict[str, Any] = field(default_factory=dict)      # 原始预测
    after_calibration: Dict[str, Any] = field(default_factory=dict)
    after_generator: Dict[str, Any] = field(default_factory=dict)  # 生成后 (direction)
    after_filter: Dict[str, Any] = field(default_factory=dict)     # 过滤后
    after_ranker: Dict[str, Any] = field(default_factory=dict)     # 排名
    after_scorer: Dict[str, Any] = field(default_factory=dict)     # 评分
    after_allocator: Dict[str, Any] = field(default_factory=dict)  # 建议权重
    final_signal: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction": self.prediction,
            "after_calibration": self.after_calibration,
            "after_generator": self.after_generator,
            "after_filter": self.after_filter,
            "after_ranker": self.after_ranker,
            "after_scorer": self.after_scorer,
            "after_allocator": self.after_allocator,
            "final_signal": self.final_signal,
        }


class ExplainabilityEngine:
    """信号解释引擎"""

    def explain(self, signal: Signal) -> ExplainTrace:
        """从 signal.metadata["explain_trace"] 重建溯源链"""
        trace_list: List[Dict[str, Any]] = signal.metadata.get("explain_trace", [])
        result = ExplainTrace(
            prediction=self._extract_prediction(signal),
            final_signal=signal.to_dict(),
        )
        for item in trace_list:
            step = item.get("step", "")
            state = item.get("state", {})
            if step == "calibrator":
                result.after_calibration = state
            elif step == "generator":
                result.after_generator = state
            elif step == "filter":
                result.after_filter = state
            elif step == "ranker":
                result.after_ranker = state
            elif step == "scorer":
                result.after_scorer = state
            elif step == "allocator":
                result.after_allocator = state
        return result

    def explain_pipeline(self, pipeline_trace: List[Dict[str, Any]]) -> ExplainTrace:
        """从 pipeline 的 trace 列表构建 ExplainTrace"""
        result = ExplainTrace()
        for item in pipeline_trace:
            step = item.get("step", "")
            state = item.get("state", {})
            if step == "calibrator":
                result.after_calibration = state
            elif step == "generator":
                result.after_generator = state
            elif step == "filter":
                result.after_filter = state
            elif step == "ranker":
                result.after_ranker = state
            elif step == "scorer":
                result.after_scorer = state
            elif step == "allocator":
                result.after_allocator = state
            elif step == "prediction":
                result.prediction = state
        return result

    @staticmethod
    def _extract_prediction(signal: Signal) -> Dict[str, Any]:
        """从 signal metadata 提取原始预测信息"""
        meta = signal.metadata
        return {
            "symbol": signal.symbol,
            "datetime": signal.datetime,
            "prediction_value": meta.get("prediction_value", 0.0),
            "raw_probability": meta.get("raw_probability", signal.confidence),
            "model_type": signal.source_model,
        }


def explain_signal(signal: Signal) -> ExplainTrace:
    """便捷函数：解释单个信号"""
    return ExplainabilityEngine().explain(signal)

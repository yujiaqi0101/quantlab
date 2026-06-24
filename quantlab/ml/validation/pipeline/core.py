"""
Validation Pipeline Core — 验证流水线核心

ML Lab 质量控制中心：

  Raw Model → Validation Pipeline → Model Package → Registry

  Pipeline 职责：
    1. 串联多个 Gate
    2. 每个 Gate 独立评分
    3. FAIL 则停止后续 Gate
    4. 汇总成 ValidationReport

  核心：
    ValidationContext  — 验证上下文（传递给每个 Gate）
    ValidationPipeline  — 流水线（编排 Gate 执行）
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .gate import (
    ValidationGate,
    GateResult,
    GateStatus,
    ValidationLevel,
    score_to_grade,
)

logger = logging.getLogger("quantlab.ml.validation.pipeline")


@dataclass
class ValidationContext:
    """
    验证上下文

    包含 Gate 执行所需的所有数据：
      - raw_model: 训练产出的原始模型
      - dataset: 训练数据集信息
      - features: 特征 DataFrame
      - labels: 标签 Series
      - predictions: 模型预测值（可选）
      - training_result: 训练结果（可选，用于 L2）
      - config: 额外配置

    每个 Gate 从 context 中取自己需要的数据。
    """
    # 核心数据
    raw_model: Any = None                 # Model 对象
    model_type: str = ""
    model_params: Dict[str, Any] = field(default_factory=dict)

    # 数据
    features: Optional[pd.DataFrame] = None
    labels: Optional[pd.Series] = None
    predictions: Optional[pd.Series] = None

    # 训练信息
    dataset_id: str = ""
    feature_ids: List[str] = field(default_factory=list)
    feature_set_id: str = ""
    label_id: str = ""
    label_set_id: str = ""
    is_classifier: bool = False

    # 训练结果（L2 Gate 用）
    training_result: Any = None          # TrainingResult

    # Walk Forward 配置（L3 Gate 用）
    walk_forward_config: Any = None      # ValidationConfig

    # 额外配置
    config: Dict[str, Any] = field(default_factory=dict)

    # 实验信息
    experiment_id: str = ""
    name: str = ""                        # 模型名称

    def to_summary(self) -> Dict[str, Any]:
        """生成上下文摘要（不含大数据对象）"""
        return {
            "model_type": self.model_type,
            "model_params": self.model_params,
            "dataset_id": self.dataset_id,
            "feature_ids": self.feature_ids,
            "feature_set_id": self.feature_set_id,
            "label_id": self.label_id,
            "label_set_id": self.label_set_id,
            "is_classifier": self.is_classifier,
            "n_features": self.features.shape[1] if self.features is not None else 0,
            "n_samples": self.features.shape[0] if self.features is not None else 0,
            "experiment_id": self.experiment_id,
            "name": self.name,
        }


@dataclass
class PipelineResult:
    """
    Pipeline 执行结果

    包含：
      - validation_id: 唯一 ID
      - gate_results: 每个 Gate 的结果
      - overall_score: 综合评分
      - overall_grade: 综合评级
      - overall_status: 综合状态
      - passed: 是否通过（可进入 Registry）
      - stopped_at: 在哪个 Gate 停止（如果有）
    """
    validation_id: str = field(default_factory=lambda: f"VAL-{uuid.uuid4().hex[:8]}")
    gate_results: List[GateResult] = field(default_factory=list)
    overall_score: float = 0.0
    overall_grade: str = "F"
    overall_status: GateStatus = GateStatus.SKIP
    passed: bool = False
    stopped_at: str = ""
    context_summary: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    total_execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "gate_results": [gr.to_dict() for gr in self.gate_results],
            "overall_score": round(self.overall_score, 2),
            "overall_grade": self.overall_grade,
            "overall_status": self.overall_status.value,
            "passed": self.passed,
            "stopped_at": self.stopped_at,
            "context_summary": self.context_summary,
            "created_at": self.created_at,
            "total_execution_time": round(self.total_execution_time, 4),
        }

    def get_gate_result(self, gate_name: str) -> Optional[GateResult]:
        """获取指定 Gate 的结果"""
        for gr in self.gate_results:
            if gr.gate_name == gate_name:
                return gr
        return None

    def to_summary_text(self) -> str:
        """生成文本摘要"""
        lines = []
        lines.append(f"Validation: {self.validation_id}")
        lines.append(f"Score: {self.overall_score:.1f} ({self.overall_grade})")
        lines.append(f"Status: {self.overall_status.value}")
        lines.append(f"Passed: {'YES' if self.passed else 'NO'}")
        if self.stopped_at:
            lines.append(f"Stopped at: {self.stopped_at}")
        lines.append("-" * 50)
        for gr in self.gate_results:
            lines.append(
                f"  [{gr.level.value}] {gr.gate_name:<20} "
                f"{gr.status.value:<8} "
                f"{gr.score:>5.1f} ({gr.grade})  "
                f"{gr.summary}"
            )
        return "\n".join(lines)


class ValidationPipeline:
    """
    验证流水线

    用法：
        pipeline = ValidationPipeline()
        pipeline.add_gate(DataGate())
        pipeline.add_gate(LeakageGate())
        pipeline.add_gate(WalkForwardGate())
        pipeline.add_gate(TradingGate())
        pipeline.add_gate(RobustnessGate())
        pipeline.add_gate(BenchmarkGate())

        result = pipeline.run(ctx)
        if result.passed:
            print("模型通过验证，可进入 Registry")
        else:
            print(f"模型被拒绝: {result.stopped_at}")
    """

    def __init__(self, name: str = "default") -> None:
        self.name = name
        self.gates: List[ValidationGate] = []
        self.stop_on_fail: bool = True       # FAIL 时停止后续 Gate
        self.stop_on_error: bool = False      # ERROR 时是否停止

    def add_gate(self, gate: ValidationGate) -> "ValidationPipeline":
        """添加 Gate"""
        self.gates.append(gate)
        return self

    def remove_gate(self, gate_name: str) -> "ValidationPipeline":
        """移除 Gate"""
        self.gates = [g for g in self.gates if g.name != gate_name]
        return self

    def get_gate(self, gate_name: str) -> Optional[ValidationGate]:
        """获取 Gate"""
        for g in self.gates:
            if g.name == gate_name:
                return g
        return None

    def enable_gate(self, gate_name: str) -> None:
        """启用 Gate"""
        g = self.get_gate(gate_name)
        if g:
            g.enabled = True

    def disable_gate(self, gate_name: str) -> None:
        """禁用 Gate"""
        g = self.get_gate(gate_name)
        if g:
            g.enabled = False

    def run(self, ctx: ValidationContext) -> PipelineResult:
        """
        执行验证流水线

        Args:
            ctx: 验证上下文

        Returns:
            PipelineResult
        """
        result = PipelineResult()
        result.context_summary = ctx.to_summary()

        from datetime import datetime
        result.created_at = datetime.now().isoformat()

        start_time = time.time()
        stopped = False

        for gate in self.gates:
            gate_result = gate.safe_execute(ctx)
            result.gate_results.append(gate_result)

            logger.info(
                f"Gate {gate.name}: {gate_result.status.value} "
                f"score={gate_result.score:.1f} ({gate_result.grade})"
            )

            # FAIL 停止
            if self.stop_on_fail and gate_result.status == GateStatus.FAIL:
                result.stopped_at = gate.name
                stopped = True
                logger.warning(
                    f"Pipeline stopped at gate '{gate.name}' (FAIL)"
                )
                break

            # ERROR 停止
            if self.stop_on_error and gate_result.status == GateStatus.ERROR:
                result.stopped_at = gate.name
                stopped = True
                logger.error(
                    f"Pipeline stopped at gate '{gate.name}' (ERROR)"
                )
                break

        result.total_execution_time = time.time() - start_time

        # 计算综合评分
        self._compute_overall_score(result)

        return result

    def _compute_overall_score(self, result: PipelineResult) -> None:
        """计算综合评分"""
        total_score = 0.0
        total_weight = 0.0
        has_fail = False
        has_warning = False
        has_error = False

        for gr in result.gate_results:
            if gr.status == GateStatus.SKIP:
                continue

            # 找到对应的 Gate 获取 weight
            weight = 10.0  # 默认权重
            gate = self.get_gate(gr.gate_name)
            if gate:
                weight = gate.weight

            total_score += gr.score * weight
            total_weight += weight

            if gr.status == GateStatus.FAIL:
                has_fail = True
            elif gr.status == GateStatus.ERROR:
                has_error = True
            elif gr.status == GateStatus.WARNING:
                has_warning = True

        if total_weight > 0:
            result.overall_score = total_score / total_weight
        else:
            result.overall_score = 0.0

        # 整体状态
        if has_fail or has_error:
            result.overall_status = GateStatus.FAIL
            result.passed = False
        elif has_warning:
            result.overall_status = GateStatus.WARNING
            result.passed = True       # WARNING 仍可通过
        else:
            result.overall_status = GateStatus.PASS
            result.passed = True

        # 评级
        result.overall_grade = score_to_grade(result.overall_score, has_fail or has_error)

    def to_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "name": self.name,
            "stop_on_fail": self.stop_on_fail,
            "stop_on_error": self.stop_on_error,
            "gates": [g.to_config() for g in self.gates],
        }

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "ValidationPipeline":
        """从配置创建 Pipeline"""
        from .registry import get_gate_registry

        pipeline = cls(name=config.get("name", "default"))
        pipeline.stop_on_fail = config.get("stop_on_fail", True)
        pipeline.stop_on_error = config.get("stop_on_error", False)

        gate_registry = get_gate_registry()
        for gate_cfg in config.get("gates", []):
            gate_cls = gate_registry.get(gate_cfg["name"])
            if gate_cls:
                gate = gate_cls(
                    enabled=gate_cfg.get("enabled", True),
                    weight=gate_cfg.get("weight"),
                )
                pipeline.add_gate(gate)

        return pipeline


def create_default_pipeline() -> ValidationPipeline:
    """
    创建默认验证流水线

    包含 6 级 Gate，按顺序执行：
      L1 DataGate         — 数据验证
      L2 TrainingGate     — 训练验证
      L3 LeakageGate      — 泄漏检测（L3 前置）
      L3 WalkForwardGate  — 时间序列验证
      L4 TradingGate      — 交易验证
      L5 RobustnessGate   — 鲁棒性验证
      L6 BenchmarkGate    — 基准验证
    """
    from .gates.data_gate import DataGate
    from .gates.training_gate import TrainingGate
    from .gates.leakage_gate import LeakageGate
    from .gates.timeseries_gate import WalkForwardGate
    from .gates.trading_gate import TradingGate
    from .gates.robustness_gate import RobustnessGate
    from .gates.benchmark_gate import BenchmarkGate

    pipeline = ValidationPipeline(name="default")
    pipeline.add_gate(DataGate())
    pipeline.add_gate(TrainingGate())
    pipeline.add_gate(LeakageGate())
    pipeline.add_gate(WalkForwardGate())
    pipeline.add_gate(TradingGate())
    pipeline.add_gate(RobustnessGate())
    pipeline.add_gate(BenchmarkGate())

    return pipeline

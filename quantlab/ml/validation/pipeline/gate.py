"""
Validation Gate — 验证门禁基类

ML Lab 质量控制中心核心概念：

  每个 Gate 是一个独立的验证关卡，可以：
    - 独立开启/关闭
    - 独立评分（0-100, A-F）
    - 独立判定 PASS/WARNING/FAIL
    - 串联成 Pipeline，FAIL 则停止

  6 级分类：
    L1 Data Validation       — 输入是否合法
    L2 Training Validation   — 训练是否正常
    L3 Time Series Validation — 时间序列验证（量化核心）
    L4 Trading Validation    — 能不能赚钱
    L5 Robustness Validation  — 是否稳定
    L6 Benchmark Validation   — 是否真的有价值
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.ml.validation.pipeline.gate")


class GateStatus(str, Enum):
    """门禁状态"""
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"
    SKIP = "SKIP"
    ERROR = "ERROR"          # 执行出错


class ValidationLevel(str, Enum):
    """验证级别"""
    L1_DATA = "L1_DATA"
    L2_TRAINING = "L2_TRAINING"
    L3_TIMESERIES = "L3_TIMESERIES"
    L4_TRADING = "L4_TRADING"
    L5_ROBUSTNESS = "L5_ROBUSTNESS"
    L6_BENCHMARK = "L6_BENCHMARK"


@dataclass
class GateResult:
    """
    单个 Gate 的执行结果

    包含：
      - status: PASS/WARNING/FAIL/SKIP/ERROR
      - score: 0-100
      - grade: A/B/C/D/F
      - summary: 一句话摘要
      - details: 详细数据（JSON 可序列化）
      - artifacts: 产物路径列表
    """
    gate_name: str = ""
    level: ValidationLevel = ValidationLevel.L1_DATA
    status: GateStatus = GateStatus.SKIP
    score: float = 0.0
    grade: str = "F"
    summary: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gate_name": self.gate_name,
            "level": self.level.value,
            "status": self.status.value,
            "score": round(self.score, 2),
            "grade": self.grade,
            "summary": self.summary,
            "details": self.details,
            "artifacts": self.artifacts,
            "execution_time": round(self.execution_time, 4),
            "error": self.error,
        }


def score_to_grade(score: float, has_fail: bool = False) -> str:
    """分数转评级"""
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


class ValidationGate:
    """
    验证门禁基类

    子类必须实现 execute() 方法。

    用法：
        class MyGate(ValidationGate):
            name = "my_gate"
            level = ValidationLevel.L1_DATA
            default_weight = 10.0

            def execute(self, ctx: ValidationContext) -> GateResult:
                # 执行验证逻辑
                score = 85
                status = GateStatus.PASS if score >= 60 else GateStatus.FAIL
                return GateResult(
                    gate_name=self.name,
                    level=self.level,
                    status=status,
                    score=score,
                    grade=score_to_grade(score),
                    summary="一切正常",
                    details={"key": "value"},
                )
    """

    # 子类覆盖
    name: str = "base_gate"
    level: ValidationLevel = ValidationLevel.L1_DATA
    default_weight: float = 10.0
    description: str = ""

    def __init__(self, enabled: bool = True, weight: float = None) -> None:
        self.enabled = enabled
        self.weight = weight if weight is not None else self.default_weight

    def execute(self, ctx: "ValidationContext") -> GateResult:
        """
        执行验证

        子类必须实现此方法。

        Args:
            ctx: 验证上下文（包含 model, dataset, features, labels 等）

        Returns:
            GateResult
        """
        raise NotImplementedError(f"{self.name}.execute() not implemented")

    def safe_execute(self, ctx: "ValidationContext") -> GateResult:
        """
        安全执行（捕获异常，返回 ERROR 状态）

        Pipeline 内部调用此方法，不直接调用 execute()。
        """
        if not self.enabled:
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.SKIP,
                summary=f"Gate {self.name} is disabled",
            )

        import time
        start = time.time()
        try:
            result = self.execute(ctx)
            result.execution_time = time.time() - start
            return result
        except Exception as e:
            logger.exception(f"Gate {self.name} execution error: {e}")
            return GateResult(
                gate_name=self.name,
                level=self.level,
                status=GateStatus.ERROR,
                score=0.0,
                grade="F",
                summary=f"Execution error: {e}",
                error=str(e),
                execution_time=time.time() - start,
            )

    def to_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "name": self.name,
            "level": self.level.value,
            "enabled": self.enabled,
            "weight": self.weight,
            "description": self.description,
        }

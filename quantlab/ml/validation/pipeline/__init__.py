"""
Validation Pipeline — 验证流水线

ML Lab 质量控制中心核心模块

  Raw Model → Validation Pipeline → Model Package → Registry

  Pipeline 编排多个 Gate，每个 Gate 独立评分，FAIL 则停止。

  6 级 Gate：
    L1 DataGate         — 数据验证
    L2 TrainingGate     — 训练验证
    L3 LeakageGate      — 泄漏检测
    L3 WalkForwardGate  — 时间序列验证
    L4 TradingGate      — 交易验证
    L5 RobustnessGate   — 鲁棒性验证
    L6 BenchmarkGate    — 基准验证
"""

from .gate import (
    ValidationGate,
    GateResult,
    GateStatus,
    ValidationLevel,
    score_to_grade,
)
from .core import (
    ValidationContext,
    ValidationPipeline,
    PipelineResult,
    create_default_pipeline,
)
from .score import (
    ValidationScore,
    OverallScore,
    DEFAULT_WEIGHTS,
    get_default_weights,
)
from .artifacts import (
    ValidationArtifactStore,
    generate_html_report,
)
from .registry import get_gate_registry

# 导出所有 Gate
from .gates import (
    DataGate,
    TrainingGate,
    LeakageGate,
    WalkForwardGate,
    TradingGate,
    RobustnessGate,
    BenchmarkGate,
)

__all__ = [
    # Gate 基类
    "ValidationGate",
    "GateResult",
    "GateStatus",
    "ValidationLevel",
    "score_to_grade",
    # Pipeline 核心
    "ValidationContext",
    "ValidationPipeline",
    "PipelineResult",
    "create_default_pipeline",
    # Score
    "ValidationScore",
    "OverallScore",
    "DEFAULT_WEIGHTS",
    "get_default_weights",
    # Artifacts
    "ValidationArtifactStore",
    "generate_html_report",
    # Registry
    "get_gate_registry",
    # Gates
    "DataGate",
    "TrainingGate",
    "LeakageGate",
    "WalkForwardGate",
    "TradingGate",
    "RobustnessGate",
    "BenchmarkGate",
]

"""
Research Context — Pipeline 统一上下文

每次研究必须有统一上下文，包含：
  - dataset_id     数据集
  - factor_set     因子配置
  - signal_set     信号配置
  - strategy_config 策略配置
  - mode           研究模式 (TS / CS / HYBRID)
  - params         额外参数
  - artifacts      产出物
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class PipelineType(str, Enum):
    """Pipeline 类型"""
    SINGLE_EXPERIMENT = "single_experiment"   # 单策略单次回测
    PARAMETER_SWEEP = "parameter_sweep"       # 参数网格搜索
    ALPHA_BATCH = "alpha_batch"               # Alpha 批量生成+评估+排序


class PipelineStatus(str, Enum):
    """Pipeline 状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FactorConfig:
    """因子配置"""
    name: str = ""                    # 因子名（如 "RSI"）
    params: Dict[str, Any] = field(default_factory=dict)  # 参数（如 {"period": 14}）
    save_as: str = ""                 # 保存名称

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignalConfig:
    """信号配置"""
    strategy_id: str = ""             # 策略 ID
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    save_as: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyConfig:
    """策略配置"""
    strategy_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    tag: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlphaBatchConfig:
    """Alpha 批处理配置"""
    factor_names: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=lambda: ["threshold"])
    ic_min: float = 0.03
    ir_min: float = 0.5
    coverage_min: float = 0.05

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SweepConfig:
    """参数扫描配置"""
    param_space: Dict[str, List[Any]] = field(default_factory=dict)
    metric: str = "sharpe"
    top_n: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchContext:
    """
    研究上下文 — Pipeline 的输入

    统一所有研究任务的配置
    """
    # 唯一标识
    context_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""

    # Pipeline 类型
    pipeline_type: PipelineType = PipelineType.SINGLE_EXPERIMENT

    # 研究模式
    mode: str = "time_series"  # time_series / cross_section / hybrid

    # 数据集
    dataset_id: str = "default"
    symbols: Optional[List[str]] = None
    start: Optional[str] = None
    end: Optional[str] = None

    # 因子配置
    factors: List[FactorConfig] = field(default_factory=list)

    # 信号配置
    signals: List[SignalConfig] = field(default_factory=list)

    # 策略配置
    strategy: Optional[StrategyConfig] = None

    # Alpha 批处理配置（ALPHA_BATCH 模式）
    alpha_batch: Optional[AlphaBatchConfig] = None

    # 参数扫描配置（PARAMETER_SWEEP 模式）
    sweep: Optional[SweepConfig] = None

    # 额外参数
    params: Dict[str, Any] = field(default_factory=dict)

    # 产出物（运行时填充）
    artifacts: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pipeline_type"] = self.pipeline_type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ResearchContext":
        if isinstance(d.get("pipeline_type"), str):
            d["pipeline_type"] = PipelineType(d["pipeline_type"])
        # 嵌套对象
        if "factors" in d and isinstance(d["factors"], list):
            d["factors"] = [FactorConfig(**f) if isinstance(f, dict) else f for f in d["factors"]]
        if "signals" in d and isinstance(d["signals"], list):
            d["signals"] = [SignalConfig(**s) if isinstance(s, dict) else s for s in d["signals"]]
        if "strategy" in d and isinstance(d["strategy"], dict):
            d["strategy"] = StrategyConfig(**d["strategy"])
        if "alpha_batch" in d and isinstance(d["alpha_batch"], dict):
            d["alpha_batch"] = AlphaBatchConfig(**d["alpha_batch"])
        if "sweep" in d and isinstance(d["sweep"], dict):
            d["sweep"] = SweepConfig(**d["sweep"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PipelineStepResult:
    """Pipeline 单步结果"""
    step_name: str = ""
    step_type: str = ""
    status: str = "pending"   # pending / running / success / error
    output: Optional[Any] = None
    error: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # output 可能包含不可序列化的对象，简化处理
        if not isinstance(d["output"], (str, int, float, bool, list, dict, type(None))):
            d["output"] = str(d["output"])
        return d


@dataclass
class PipelineResult:
    """
    Pipeline 执行结果 — 统一输出

    不管是单实验、参数扫描还是 Alpha 批处理，
    都输出 PipelineResult
    """
    # 唯一标识
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    context_id: str = ""
    name: str = ""

    # Pipeline 类型
    pipeline_type: PipelineType = PipelineType.SINGLE_EXPERIMENT

    # 状态
    status: PipelineStatus = PipelineStatus.PENDING

    # 各步骤结果
    steps: List[PipelineStepResult] = field(default_factory=list)

    # 最终指标
    metrics: Dict[str, Any] = field(default_factory=dict)

    # 实验ID（单实验模式）
    experiment_id: Optional[str] = None

    # 扫描结果（参数扫描模式）
    sweep_results: Optional[List[Dict[str, Any]]] = None

    # Alpha 结果（Alpha 批处理模式）
    alpha_results: Optional[List[Dict[str, Any]]] = None

    # 产出物路径
    artifacts: Dict[str, str] = field(default_factory=dict)

    # 时间
    created_at: str = ""
    completed_at: str = ""
    duration_ms: float = 0.0

    def __post_init__(self):
        if not self.created_at:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["pipeline_type"] = self.pipeline_type.value
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineResult":
        if isinstance(d.get("pipeline_type"), str):
            d["pipeline_type"] = PipelineType(d["pipeline_type"])
        if isinstance(d.get("status"), str):
            d["status"] = PipelineStatus(d["status"])
        if "steps" in d and isinstance(d["steps"], list):
            d["steps"] = [PipelineStepResult(**s) if isinstance(s, dict) else s for s in d["steps"]]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

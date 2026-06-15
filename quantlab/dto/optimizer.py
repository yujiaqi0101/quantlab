"""Optimizer DTO"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class OptimizerMethod(str, Enum):
    GRID = "grid"
    RANDOM = "random"
    BAYESIAN = "bayesian"
    PARALLEL = "parallel"     # ProcessPoolExecutor
    AUTO = "auto"             # 由 service 自行选择


@dataclass(slots=True)
class OptimizerRequest:
    """
    优化请求

    method              优化方法
    param_space         参数空间，{name: [v1, v2, ...]} 或 {name: (min, max, n)}
    n_trials            random/bayes 专用：试验次数
    top_k               保留前 K 个
    dataset / symbols   与 BacktestRequest 一致
    engine / cash       与 BacktestRequest 一致
    """
    strategy_id: str
    method: str = OptimizerMethod.GRID.value
    param_space: Dict[str, Any] = field(default_factory=dict)
    n_trials: int = 50
    top_k: int = 5
    dataset: str = ""
    symbols: List[str] = field(default_factory=list)
    initial_cash: float = 100000.0
    commission_bps: float = 1.0
    slippage_bps: float = 1.0
    engine: str = "bar"
    top_n: int = 1
    save_experiments: bool = True
    experiment_prefix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OptimizerResultRow:
    """一次试验的结果行"""
    params: Dict[str, Any]
    score: float
    experiment_id: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OptimizerResponse:
    task_id: str
    status: str
    best: Optional[OptimizerResultRow] = None
    top: List[OptimizerResultRow] = field(default_factory=list)
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

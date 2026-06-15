"""
Domain — OptimizerJob / OptimizerTrial

参数优化的领域对象。
OptimizerService 入口：
    create_task(experiment, param_space) → Task
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from .experiment import Experiment


class OptimizerMethod(str, Enum):
    GRID = "grid"
    RANDOM = "random"
    BAYESIAN = "bayesian"
    PARALLEL = "parallel"
    AUTO = "auto"


@dataclass(slots=True)
class OptimizerSpec:
    """
    优化任务规格

    method            grid / random / bayesian / parallel / auto
    param_space       参数空间
                      列表 → grid 取全部
                      (min, max, n) → 离散化
    n_trials          random/bayes 专用
    top_k             保留前 K
    experiment_prefix 落库实验名前缀
    """
    strategy_id: str
    method: str = OptimizerMethod.GRID.value
    param_space: Dict[str, Any] = field(
        default_factory=dict
    )
    n_trials: int = 50
    top_k: int = 5
    dataset: str = "default"
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

    def to_backtest_spec_template(self) -> "BacktestSpecTemplate":
        """用本 spec 的字段，生成单次回测的模板（不含 param_space）"""
        return BacktestSpecTemplate(
            strategy_id=self.strategy_id,
            dataset=self.dataset,
            symbols=list(self.symbols),
            initial_cash=self.initial_cash,
            commission_bps=self.commission_bps,
            slippage_bps=self.slippage_bps,
            engine=self.engine,
            top_n=self.top_n,
        )


@dataclass(slots=True)
class BacktestSpecTemplate:
    """单次试验用的 BacktestSpec 模板（参数由 trial 注入）"""
    strategy_id: str
    dataset: str
    symbols: List[str]
    initial_cash: float
    commission_bps: float
    slippage_bps: float
    engine: str
    top_n: int


@dataclass(slots=True)
class OptimizerTrial:
    """一次试验：参数 + 分数 + 落库后的 experiment_id"""
    params: Dict[str, Any]
    score: float = 0.0
    experiment_id: Optional[str] = None
    metrics: Dict[str, float] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OptimizerJob:
    spec: OptimizerSpec
    template: BacktestSpecTemplate
    trials: List[OptimizerTrial] = field(
        default_factory=list
    )
    best: Optional[OptimizerTrial] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "trials": [t.to_dict() for t in self.trials],
            "best": (
                self.best.to_dict() if self.best else None
            ),
        }

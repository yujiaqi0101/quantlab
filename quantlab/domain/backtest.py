"""
Domain — BacktestJob

一次"回测任务"的完整规格。

BacktestService.create_task(experiment) → Task
                          ↓
                    BacktestJob（内部） → 执行
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .experiment import Experiment


@dataclass(slots=True)
class BacktestSpec:
    """
    回测的执行参数

    字段：
      strategy_id
      parameters
      dataset / symbols / start / end
      initial_cash
      commission_bps / slippage_bps
      engine             bar / vectorbt / auto
      top_n              组合构造选 N
    """
    strategy_id: str
    parameters: Dict[str, Any] = field(
        default_factory=dict
    )
    dataset: str = "default"
    symbols: List[str] = field(default_factory=list)
    start: Optional[str] = None
    end: Optional[str] = None
    initial_cash: float = 100000.0
    commission_bps: float = 1.0
    slippage_bps: float = 1.0
    engine: str = "bar"
    top_n: int = 1
    save_experiment: bool = True
    experiment_name: Optional[str] = None
    dataset_version: Optional[str] = None  # V4.3: 数据集版本

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_experiment(self) -> Experiment:
        """生成一个 Experiment（供 ExperimentRepository 落库）"""
        import uuid
        from .task import now_iso
        return Experiment(
            id="exp_" + uuid.uuid4().hex[:8],
            name=(
                self.experiment_name
                or f"{self.strategy_id}_backtest"
            ),
            strategy_id=self.strategy_id,
            parameters=dict(self.parameters),
            dataset=self.dataset,
            dataset_version=self.dataset_version,
            symbols=list(self.symbols),
            created_at=now_iso(),
            tag="backtest",
        )


@dataclass(slots=True)
class BacktestJob:
    """
    回测任务（在 Service 内部流转）

    spec        回测参数
    experiment  实验元信息（落库用）
    """
    spec: BacktestSpec
    experiment: Experiment

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec": self.spec.to_dict(),
            "experiment": self.experiment.to_dict(),
        }

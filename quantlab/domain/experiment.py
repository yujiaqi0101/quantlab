"""
Domain — Experiment / ExperimentResult

两个**不同**对象：
  Experiment        = 一次实验"是什么"（元数据）
  ExperimentResult  = 一次实验"跑出来什么"（指标）

不要混。
前端：
  - "我的实验列表"  → List[ExperimentSummary]
  - "看具体实验"    → Experiment + ExperimentResult 一起返回
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .task import now_iso


@dataclass(slots=True)
class Experiment:
    """
    一次实验（只描述"是什么"）

    字段：
      id           实验 ID
      name         命名（用户给）
      strategy_id  策略注册 ID
      parameters   参数字典
      dataset      数据集标识
      symbols      标的列表
      created_at   ISO
      tag          标签
      note         备注
    """
    id: str
    name: str
    strategy_id: str
    parameters: Dict[str, Any] = field(
        default_factory=dict
    )
    dataset: str = "default"
    dataset_version: Optional[str] = None  # V4.3: 数据集版本，保证回测可复现
    symbols: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=now_iso)
    tag: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExperimentResult:
    """
    一次实验的结果（只描述"跑出什么"）

    与 Experiment 是 1:1 关系（按 experiment_id 关联）。
    一个 Experiment 可以暂时没有 Result（在跑中）。

    字段：
      experiment_id
      sharpe / total_return / max_drawdown / trade_count
      final_equity / win_rate
      extra          其它自定义指标
      source         "event" / "bar" / "vectorbt" ...
    """
    experiment_id: str
    sharpe: float = 0.0
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    trade_count: int = 0
    win_rate: float = 0.0
    final_equity: float = 0.0
    profit_factor: float = 0.0
    avg_trade: float = 0.0
    source: str = "event"
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_summary(self) -> Dict[str, Any]:
        d = self.to_dict()
        # 简化版，列表页用
        return {
            "experiment_id": d["experiment_id"],
            "sharpe": d["sharpe"],
            "total_return": d["total_return"],
            "max_drawdown": d["max_drawdown"],
            "trade_count": d["trade_count"],
            "final_equity": d["final_equity"],
        }


@dataclass(slots=True)
class ExperimentSummary:
    """
    列表页用：Experiment + 关键指标（合一展示）
    """
    id: str
    name: str
    strategy: str
    params: Dict[str, Any] = field(
        default_factory=dict
    )
    sharpe: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    created_at: str = ""
    tag: str = ""
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExperimentDetail:
    """详情页：Experiment + Result + 配置 + 曲线 + 交易明细"""
    experiment: Experiment
    result: Optional[ExperimentResult] = None
    config: Dict[str, Any] = field(default_factory=dict)
    equity_curve: List[Dict[str, Any]] = field(
        default_factory=list
    )
    trades: List[Dict[str, Any]] = field(
        default_factory=list
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment": self.experiment.to_dict(),
            "result": (
                self.result.to_dict()
                if self.result else None
            ),
            "config": dict(self.config),
            "equity_curve": list(self.equity_curve),
            "trades": list(self.trades),
        }


def summary_from(
    exp: Experiment,
    result: Optional[ExperimentResult] = None,
) -> ExperimentSummary:
    """Experiment (+ Result) → ExperimentSummary"""
    return ExperimentSummary(
        id=exp.id,
        name=exp.name,
        strategy=exp.strategy_id,
        params=dict(exp.parameters),
        sharpe=result.sharpe if result else 0.0,
        total_return=(
            result.total_return if result else 0.0
        ),
        max_drawdown=(
            result.max_drawdown if result else 0.0
        ),
        created_at=exp.created_at,
        tag=exp.tag,
        note=exp.note,
    )

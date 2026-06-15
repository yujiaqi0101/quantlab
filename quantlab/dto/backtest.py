"""Backtest DTO"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class BacktestRequest:
    """
    回测请求

    字段：
      strategy_id        注册的策略 ID（如 "ma_cross"）
      parameters         策略参数字典
      dataset            数据集标识（目录名 / 文件名 / 远程 ID）
      symbols            标的列表（多资产场景；空则取 dataset 全部）
      start / end        时间过滤
      initial_cash       初始资金
      commission_bps     佣金（bps，1bps=0.0001）
      slippage_bps       滑点（bps）
      engine             "bar" / "vectorbt" / "auto"
      top_n              组合构造选 N（多资产）
      save_experiment    是否落库 Experiment
      experiment_name    自定义实验名（默认自动生成）
    """
    strategy_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dataset: str = ""
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
    dataset_version: Optional[str] = None  # V4.3: 数据集版本，保证回测可复现

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BacktestMetrics:
    """回测核心指标（精简版，前端展示够用）"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    n_trades: int = 0
    avg_trade: float = 0.0
    final_equity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BacktestResponse:
    """
    回测响应

    task_id             异步任务 ID
    status              任务状态字符串
    experiment_id       若 save_experiment，落库后的 ID
    metrics             回测指标
    message             附加信息
    """
    task_id: str
    status: str
    experiment_id: Optional[str] = None
    metrics: Optional[BacktestMetrics] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

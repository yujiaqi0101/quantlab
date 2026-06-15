"""
Domain — RuntimeInstance

实盘运行实例的领域模型。

RuntimeService 入口：
    start_strategy(spec)  →  内部 create_task → Task → 异步启动
    stop_strategy(id)     →  同上
    restart_strategy(id)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

from .task import now_iso


class RuntimeState(str, Enum):
    """实盘实例状态"""
    PENDING = "PENDING"      # 启动中
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"

    @classmethod
    def terminal(cls) -> list:
        return [cls.STOPPED, cls.ERROR, cls.CANCELLED]


@dataclass(slots=True)
class RuntimeInstance:
    """
    一个实盘/Paper 运行实例

    id             实例 ID
    strategy_id    策略 ID
    account_id     账户 ID
    parameters     策略参数
    symbols        订阅的标的
    data_source    "replay" / "live" / "paper"
    replay_dataset 回放数据集标识（data_source=replay）
    status         RuntimeState
    started_at
    stopped_at
    last_equity
    last_pnl
    bars_processed
    message
    error
    """
    id: str
    strategy_id: str
    account_id: str
    parameters: Dict[str, Any] = field(
        default_factory=dict
    )
    symbols: List[str] = field(default_factory=list)
    data_source: str = "paper"
    replay_dataset: Optional[str] = None
    status: str = RuntimeState.PENDING.value
    started_at: Optional[str] = None
    stopped_at: Optional[str] = None
    last_equity: float = 0.0
    last_pnl: float = 0.0
    bars_processed: int = 0
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def is_running(self) -> bool:
        return self.status == RuntimeState.RUNNING.value

    @property
    def is_terminal(self) -> bool:
        try:
            return (
                RuntimeState(self.status)
                in RuntimeState.terminal()
            )
        except ValueError:
            return False


@dataclass(slots=True)
class StartStrategySpec:
    """启动实盘请求的领域对象"""
    runtime_id: str
    strategy_id: str
    account_id: str
    parameters: Dict[str, Any] = field(
        default_factory=dict
    )
    symbols: List[str] = field(default_factory=list)
    data_source: str = "paper"
    replay_dataset: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_instance(self) -> RuntimeInstance:
        return RuntimeInstance(
            id=self.runtime_id,
            strategy_id=self.strategy_id,
            account_id=self.account_id,
            parameters=dict(self.parameters),
            symbols=list(self.symbols),
            data_source=self.data_source,
            replay_dataset=self.replay_dataset,
        )

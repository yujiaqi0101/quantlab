"""Monitor DTO"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class LogEntry:
    """一条日志"""
    ts: str
    level: str
    source: str
    message: str
    trace_id: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AlertInfo:
    rule_name: str
    level: str
    message: str
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MetricsSnapshot:
    """
    一帧指标快照（前端 Dashboard 轮询/WebSocket 推送）

    ts                   采样时间
    equity               净值
    pnl                  累计 PnL
    drawdown             回撤
    exposure             暴露
    positions_value      持仓市值
    cash                 现金
    extra                其它自定义键值
    """
    ts: str
    equity: float = 0.0
    pnl: float = 0.0
    drawdown: float = 0.0
    exposure: float = 0.0
    positions_value: float = 0.0
    cash: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

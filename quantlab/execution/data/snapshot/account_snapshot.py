"""
Account Snapshot — 账户快照

定期对账户状态做快照，用于：
  1. 系统恢复时重建持仓
  2. 对账时对比本地 vs 交易所
  3. 资金管理决策
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class AccountSnapshot:
    """
    账户快照 — 某一时刻的完整账户状态
    """
    timestamp: int                                  # exchange time (ms)
    local_timestamp: int = 0                        # local capture time (ms)
    cash: float = 0.0
    equity: float = 0.0
    margin_used: float = 0.0
    buying_power: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)    # symbol → qty
    position_values: Dict[str, float] = field(default_factory=dict)  # symbol → market value
    source: str = ""

    @classmethod
    def from_broker(cls, broker, source: str = "") -> "AccountSnapshot":
        """从 broker 获取当前账户快照"""
        account = broker.get_account()
        positions = broker.get_positions()
        return cls(
            timestamp=int(time.time() * 1000),
            local_timestamp=int(time.time() * 1000),
            cash=account.cash,
            equity=account.equity,
            margin_used=account.margin_used,
            buying_power=account.buying_power,
            positions=dict(positions),
            source=source,
        )

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "local_timestamp": self.local_timestamp,
            "cash": self.cash,
            "equity": self.equity,
            "margin_used": self.margin_used,
            "buying_power": self.buying_power,
            "positions": self.positions,
            "position_values": self.position_values,
            "source": self.source,
        }

    def invested_value(self) -> float:
        """已投资金额 = equity - cash"""
        return self.equity - self.cash

    def exposure(self) -> float:
        """敞口 = invested / equity"""
        if self.equity <= 0:
            return 0.0
        return self.invested_value() / self.equity

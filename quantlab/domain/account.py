"""
Domain — Account

账户的对外统一模型。
注意：
  - domain.Account  与 runtime.AccountManager.Account 是不同层次的模型
  - domain.Account 是 API 友好（只读视图）
  - runtime.Account 是带状态的对象（apply_fill 等）
  - 内部通过适配器互转
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Position:
    """单只标的的持仓"""
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Account:
    """
    账户的对外只读模型

    account_id       唯一 ID
    name             显示名
    broker           "PAPER" / "IBKR" / "BINANCE" ...
    cash             现金
    equity           净值
    risk_profile     "low" / "medium" / "high"
    positions        持仓列表
    extra            其它元数据
    """
    account_id: str
    name: str = ""
    broker: str = "PAPER"
    cash: float = 0.0
    equity: float = 0.0
    risk_profile: str = "medium"
    positions: List[Position] = field(
        default_factory=list
    )
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def exposure(self) -> float:
        return sum(
            p.market_value for p in self.positions
        )

    @property
    def position_count(self) -> int:
        return sum(
            1 for p in self.positions if p.qty != 0
        )

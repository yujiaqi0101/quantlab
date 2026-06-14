"""
Account + AccountManager：多账户模型（V3.4）

V3.4 核心：
    1) 每个 Account 独立 cash / equity / positions
    2) AccountManager 管理多账户
    3) Account 通过 broker_name 关联到具体 broker
    4) 账户间资金不互通

Account 结构：
    account_id       唯一标识
    name             显示名
    cash             现金
    equity           净值（实时算）
    positions        Dict[symbol, Position]
    broker_name      关联的 broker（如 "PAPER" / "IBKR" / "BINANCE"）
    risk_profile     "low" / "medium" / "high"
    extra            自定义元数据

V3.4 隔离原则：
    Supervisor 不会修改 Account 内部状态
    只有该账户的 StrategyRuntime 才能 update
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class Account:
    """V3.4 账户模型"""
    account_id: str
    name: str = ""
    cash: float = 0.0
    equity: float = 0.0
    positions: Dict[str, Any] = field(
        default_factory=dict
    )   # Dict[symbol, qty]  简化为数量
    broker_name: str = "PAPER"
    risk_profile: str = "medium"
    extra: Dict[str, Any] = field(
        default_factory=dict
    )

    def position_qty(self, symbol: str) -> int:
        return int(self.positions.get(symbol, 0))

    def has_position(self, symbol: str) -> bool:
        return self.position_qty(symbol) != 0

    def apply_fill(
        self,
        symbol: str,
        qty: int,
        price: float,
        commission: float = 0.0,
    ):
        """
        V3.4 Account 内置 apply_fill（账户级）
        简化：用 qty 绝对值累加，不算 realized_pnl
        （account 视角：只关心资金和持仓分布）
        """
        cur = self.positions.get(symbol, 0)
        new = cur + qty
        if new == 0:
            self.positions.pop(symbol, None)
        else:
            self.positions[symbol] = new
        # 现金：买入扣、卖出加
        self.cash -= qty * price
        self.cash -= commission
        # equity 在 equity() 里动态算


class AccountManager:
    """
    V3.4 多账户管理

    用法：
        am = AccountManager()
        am.create_account("acc1", cash=100000, broker="PAPER")
        am.create_account("acc2", cash=50000,  broker="IBKR")
        a = am.get_account("acc1")
        a.apply_fill("AAPL", qty=100, price=150.0)
    """

    def __init__(self):
        self.accounts: Dict[str, Account] = {}

    def create_account(
        self,
        account_id: str,
        cash: float = 0.0,
        broker_name: str = "PAPER",
        risk_profile: str = "medium",
        name: str = "",
        extra: Optional[Dict] = None,
    ) -> Account:
        if account_id in self.accounts:
            raise ValueError(
                f"account {account_id!r} already exists"
            )
        acc = Account(
            account_id=account_id,
            name=name or account_id,
            cash=float(cash),
            equity=float(cash),
            broker_name=broker_name,
            risk_profile=risk_profile,
            extra=extra or {},
        )
        self.accounts[account_id] = acc
        return acc

    def get_account(
        self, account_id: str
    ) -> Account:
        if account_id not in self.accounts:
            raise KeyError(
                f"account {account_id!r} not found"
            )
        return self.accounts[account_id]

    def list_accounts(self) -> List[Account]:
        return list(self.accounts.values())

    def update_account(
        self,
        account_id: str,
        cash_delta: float = 0.0,
        equity_delta: float = 0.0,
    ) -> Account:
        acc = self.get_account(account_id)
        acc.cash += cash_delta
        acc.equity += equity_delta
        return acc

    def total_equity(self) -> float:
        return sum(
            a.cash + sum(
                a.positions.get(s, 0) * 0   # 需要价 → 这里简化为 0
                for s in a.positions
            )
            for a in self.accounts.values()
        )

    def snapshot(self) -> Dict[str, Dict]:
        return {
            a.account_id: {
                "cash": a.cash,
                "equity": a.equity,
                "positions": dict(a.positions),
                "broker_name": a.broker_name,
                "risk_profile": a.risk_profile,
            }
            for a in self.accounts.values()
        }

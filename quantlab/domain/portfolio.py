"""
Domain — PortfolioSnapshot / PortfolioSummary

跨场景（Backtest / Paper / Live）共用的组合视图。

注意：
  - core.portfolio_snapshot.PortfolioSnapshot 是 V1.9 引擎内部用的
  - domain.PortfolioSnapshot 是"对外传输模型"，字段更全
  - Service 层做适配
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .account import Account, Position


@dataclass(slots=True)
class PortfolioSnapshot:
    """
    单时点组合快照

    timestamp     ISO 字符串 / datetime
    cash
    equity
    positions     List[Position]
    pnl           相对初始的累计 PnL
    drawdown      当前回撤（0~1，负数）
    exposure      持仓市值
    extra         其它
    """
    timestamp: str
    cash: float = 0.0
    equity: float = 0.0
    positions: List[Position] = field(
        default_factory=list
    )
    pnl: float = 0.0
    drawdown: float = 0.0
    exposure: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def invested_weight(self) -> float:
        if self.equity <= 0:
            return 0.0
        return 1.0 - (self.cash / self.equity)


@dataclass(slots=True)
class PortfolioSummary:
    """
    多账户全局概览

    total_equity
    total_cash
    total_exposure
    total_pnl
    accounts          List[Account]
    exposure_by_symbol
    """
    total_equity: float = 0.0
    total_cash: float = 0.0
    total_exposure: float = 0.0
    total_pnl: float = 0.0
    accounts: List[Account] = field(
        default_factory=list
    )
    exposure_by_symbol: Dict[str, float] = field(
        default_factory=dict
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_accounts(
        cls,
        accounts: List[Account],
        initial_equity: Optional[Dict[str, float]] = None,
    ) -> "PortfolioSummary":
        """从账户列表聚合"""
        initial = initial_equity or {}
        total_equity = 0.0
        total_cash = 0.0
        total_exposure = 0.0
        total_pnl = 0.0
        exposure_by: Dict[str, float] = {}

        for acc in accounts:
            total_equity += acc.equity
            total_cash += acc.cash
            total_exposure += acc.exposure
            base = initial.get(acc.account_id, 0.0)
            if base <= 0:
                base = acc.cash  # fallback
            total_pnl += (acc.equity - base)
            for p in acc.positions:
                exposure_by[p.symbol] = (
                    exposure_by.get(p.symbol, 0.0)
                    + p.market_value
                )

        return cls(
            total_equity=total_equity,
            total_cash=total_cash,
            total_exposure=total_exposure,
            total_pnl=total_pnl,
            accounts=list(accounts),
            exposure_by_symbol=exposure_by,
        )

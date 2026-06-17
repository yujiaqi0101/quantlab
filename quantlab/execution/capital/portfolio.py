"""
Portfolio Manager — 组合管理

Capital 层的组合管理，跟踪所有策略的合并持仓
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger("quantlab.execution.capital.portfolio")


@dataclass
class Position:
    """持仓"""
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    market_price: float = 0.0
    strategy_id: str = ""
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0

    @property
    def market_value(self) -> float:
        return self.qty * self.market_price

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "strategy_id": self.strategy_id,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
        }


class CapitalPortfolio:
    """
    组合管理器

    用法：
        portfolio = CapitalPortfolio(initial_capital=100000)
        portfolio.update_position("BTCUSDT", qty=0.5, price=50000, strategy_id="s1")
        portfolio.update_prices({"BTCUSDT": 51000})
        print(portfolio.equity())
    """

    def __init__(self, initial_capital: float = 100000) -> None:
        self.cash: float = initial_capital
        self.initial_capital: float = initial_capital
        self._positions: Dict[str, Position] = {}
        self._strategy_positions: Dict[str, List[str]] = {}  # strategy_id → [symbol]

    @property
    def positions(self) -> Dict[str, Position]:
        return self._positions

    def update_position(
        self,
        symbol: str,
        qty: float,
        price: float,
        strategy_id: str = "",
    ) -> None:
        """更新持仓"""
        if symbol not in self._positions:
            self._positions[symbol] = Position(
                symbol=symbol,
                strategy_id=strategy_id,
            )

        pos = self._positions[symbol]
        old_value = pos.qty * pos.avg_price
        new_value = qty * price

        if pos.qty + qty != 0 and (pos.qty > 0) == (qty > 0):
            # 加仓
            total_qty = pos.qty + qty
            pos.avg_price = (old_value + new_value) / total_qty
            pos.qty = total_qty
        else:
            # 减仓或反手
            if abs(qty) >= abs(pos.qty):
                # 清仓或反手
                realized = (price - pos.avg_price) * pos.qty * (1 if pos.qty > 0 else -1)
                pos.realized_pnl += realized
                remaining = qty + pos.qty
                if remaining != 0:
                    pos.qty = remaining
                    pos.avg_price = price
                else:
                    pos.qty = 0
            else:
                # 部分减仓
                realized = (price - pos.avg_price) * qty * (1 if pos.qty > 0 else -1)
                pos.realized_pnl += realized
                pos.qty += qty

        pos.market_price = price

        if strategy_id:
            if strategy_id not in self._strategy_positions:
                self._strategy_positions[strategy_id] = []
            if symbol not in self._strategy_positions[strategy_id]:
                self._strategy_positions[strategy_id].append(symbol)

    def update_prices(self, prices: Dict[str, float]) -> None:
        """更新市场价格"""
        for symbol, price in prices.items():
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.market_price = price
                pos.unrealized_pnl = (price - pos.avg_price) * pos.qty

    def equity(self) -> float:
        """总净值"""
        invested = sum(p.market_value for p in self._positions.values())
        return self.cash + invested

    def invested_value(self) -> float:
        return sum(abs(p.market_value) for p in self._positions.values())

    def exposure(self) -> float:
        eq = self.equity()
        return self.invested_value() / eq if eq > 0 else 0.0

    def total_pnl(self) -> float:
        return self.equity() - self.initial_capital

    def total_realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self._positions.values())

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self._positions.values())

    def get_positions_by_strategy(self, strategy_id: str) -> List[Position]:
        symbols = self._strategy_positions.get(strategy_id, [])
        return [self._positions[s] for s in symbols if s in self._positions]

    def to_dict(self) -> Dict:
        return {
            "cash": self.cash,
            "initial_capital": self.initial_capital,
            "equity": self.equity(),
            "invested_value": self.invested_value(),
            "exposure": self.exposure(),
            "total_pnl": self.total_pnl(),
            "realized_pnl": self.total_realized_pnl(),
            "unrealized_pnl": self.total_unrealized_pnl(),
            "positions": {k: v.to_dict() for k, v in self._positions.items()},
        }

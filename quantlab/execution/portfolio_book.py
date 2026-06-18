"""
Portfolio Book — 组合簿

T1 第五模块：维护 cash / equity / margin / exposure

  cash        — 现金
  equity      — 总净值（cash + 持仓市值）
  margin      — 保证金占用
  exposure    — 敞口（持仓市值 / equity）

  Observe Studio Overview 页面数据来源

用法：
    book = PortfolioBook(initial_capital=100000)
    book.apply_fill(symbol="BTCUSDT", side="BUY", qty=0.1, price=50000, commission=5.0)
    book.update_prices({"BTCUSDT": 51000})
    print(book.equity(), book.exposure())
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .position_book import PositionBook, Position

logger = logging.getLogger("quantlab.execution.portfolio_book")


@dataclass
class PortfolioSnapshot:
    """组合快照（时点状态）"""
    timestamp: int
    cash: float
    equity: float
    margin: float
    exposure: float
    realized_pnl: float
    unrealized_pnl: float
    n_positions: int

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "cash": self.cash,
            "equity": self.equity,
            "margin": self.margin,
            "exposure": self.exposure,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "n_positions": self.n_positions,
        }


class PortfolioBook:
    """
    组合簿 — 维护账户级别的资金状态

    内部使用 PositionBook 维护持仓
    """

    def __init__(self, initial_capital: float = 100000.0) -> None:
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position_book = PositionBook()
        self._equity_history: List[PortfolioSnapshot] = []
        self._max_equity: float = initial_capital
        self._max_drawdown: float = 0.0

    @property
    def positions(self) -> Dict[str, Position]:
        return self.position_book.positions

    # ------------------------------------------------------------------
    # 应用成交
    # ------------------------------------------------------------------
    def apply_fill(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        commission: float = 0.0,
        strategy_id: str = "",
    ) -> Position:
        """应用成交"""
        trade_value = price * qty
        # 现金变化
        if side == "BUY":
            self.cash -= trade_value
        else:
            self.cash += trade_value
        self.cash -= commission

        # 更新持仓
        return self.position_book.apply_fill(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            commission=commission,
            strategy_id=strategy_id,
        )

    # ------------------------------------------------------------------
    # 更新市场价格
    # ------------------------------------------------------------------
    def update_prices(self, prices: Dict[str, float]) -> None:
        """更新市场价格"""
        self.position_book.update_prices(prices)
        # 记录快照
        self._record_snapshot()

    def update_price(self, symbol: str, price: float) -> None:
        self.update_prices({symbol: price})

    # ------------------------------------------------------------------
    # 账户指标
    # ------------------------------------------------------------------
    def invested_value(self) -> float:
        """投资市值（持仓绝对值总和）"""
        return self.position_book.total_market_value()

    def net_invested(self) -> float:
        """净持仓市值"""
        return self.position_book.net_market_value()

    def equity(self) -> float:
        """总净值 = cash + 净持仓市值"""
        return self.cash + self.net_invested()

    def margin(self) -> float:
        """保证金占用（简化：等于 invested_value）"""
        return self.invested_value()

    def exposure(self) -> float:
        """敞口 = invested_value / equity"""
        eq = self.equity()
        return self.invested_value() / eq if eq > 0 else 0.0

    def long_exposure(self) -> float:
        return self.position_book.long_exposure()

    def short_exposure(self) -> float:
        return self.position_book.short_exposure()

    def realized_pnl(self) -> float:
        return self.position_book.total_realized_pnl()

    def unrealized_pnl(self) -> float:
        return self.position_book.total_unrealized_pnl()

    def total_pnl(self) -> float:
        return self.equity() - self.initial_capital

    def total_return(self) -> float:
        """总收益率"""
        if self.initial_capital <= 0:
            return 0.0
        return self.total_pnl() / self.initial_capital

    # ------------------------------------------------------------------
    # 回撤
    # ------------------------------------------------------------------
    def max_drawdown(self) -> float:
        """最大回撤（百分比，正数）"""
        return self._max_drawdown

    def current_drawdown(self) -> float:
        """当前回撤"""
        eq = self.equity()
        if self._max_equity <= 0 or eq >= self._max_equity:
            return 0.0
        return (self._max_equity - eq) / self._max_equity

    # ------------------------------------------------------------------
    # 持仓查询
    # ------------------------------------------------------------------
    def get_position(self, symbol: str) -> Optional[Position]:
        return self.position_book.get_position(symbol)

    def get_positions(self, include_closed: bool = False) -> List[Position]:
        return self.position_book.get_positions(include_closed=include_closed)

    def n_open_positions(self) -> int:
        return self.position_book.n_open_positions()

    # ------------------------------------------------------------------
    # 历史
    # ------------------------------------------------------------------
    def equity_history(self) -> List[PortfolioSnapshot]:
        return list(self._equity_history)

    def _record_snapshot(self) -> None:
        """记录快照"""
        eq = self.equity()
        now = int(time.time() * 1000)

        # 更新最大净值和回撤
        if eq > self._max_equity:
            self._max_equity = eq

        dd = self.current_drawdown()
        if dd > self._max_drawdown:
            self._max_drawdown = dd

        snapshot = PortfolioSnapshot(
            timestamp=now,
            cash=self.cash,
            equity=eq,
            margin=self.margin(),
            exposure=self.exposure(),
            realized_pnl=self.realized_pnl(),
            unrealized_pnl=self.unrealized_pnl(),
            n_positions=self.n_open_positions(),
        )
        self._equity_history.append(snapshot)

        # 限制历史长度
        if len(self._equity_history) > 10000:
            self._equity_history = self._equity_history[-5000:]

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "equity": self.equity(),
            "invested_value": self.invested_value(),
            "net_invested": self.net_invested(),
            "margin": self.margin(),
            "exposure": self.exposure(),
            "long_exposure": self.long_exposure(),
            "short_exposure": self.short_exposure(),
            "realized_pnl": self.realized_pnl(),
            "unrealized_pnl": self.unrealized_pnl(),
            "total_pnl": self.total_pnl(),
            "total_return": self.total_return(),
            "max_drawdown": self.max_drawdown(),
            "current_drawdown": self.current_drawdown(),
            "n_open_positions": self.n_open_positions(),
            "positions": self.position_book.to_dict(),
        }

    def snapshot(self) -> Dict:
        """导出快照（用于持久化）"""
        return {
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "max_equity": self._max_equity,
            "max_drawdown": self._max_drawdown,
            "positions": self.position_book.snapshot(),
        }

    def restore(self, data: Dict) -> None:
        """从快照恢复"""
        self.initial_capital = data.get("initial_capital", 100000)
        self.cash = data.get("cash", self.initial_capital)
        self._max_equity = data.get("max_equity", self.cash)
        self._max_drawdown = data.get("max_drawdown", 0.0)
        self.position_book.restore(data.get("positions", []))
        logger.info(
            f"PortfolioBook restored: cash={self.cash}, "
            f"positions={self.n_open_positions()}"
        )

    def reset(self) -> None:
        """重置到初始状态"""
        self.cash = self.initial_capital
        self.position_book.reset()
        self._equity_history.clear()
        self._max_equity = self.initial_capital
        self._max_drawdown = 0.0

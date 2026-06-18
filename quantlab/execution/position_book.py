"""
Position Book — 本地持仓簿

T1 第四模块：不依赖交易所返回，本地维护持仓

为什么本地维护？
  - Replay 依赖它
  - Risk 依赖它
  - Performance 依赖它
  - 交易所返回的持仓有延迟，不可靠

结构：
  symbol
  qty
  avg_price
  realized_pnl
  unrealized_pnl

用法：
    book = PositionBook()
    book.apply_fill(symbol="BTCUSDT", side="BUY", qty=0.1, price=50000, commission=5.0)
    book.update_prices({"BTCUSDT": 51000})
    positions = book.get_positions()
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.position_book")


@dataclass
class Position:
    """单个持仓"""
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    market_price: float = 0.0
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    strategy_id: str = ""
    updated_at: int = 0

    # 统计字段
    n_fills: int = 0
    total_cost: float = 0.0      # 累计买入成本
    total_proceeds: float = 0.0  # 累计卖出收入

    @property
    def market_value(self) -> float:
        return self.qty * self.market_price

    @property
    def side(self) -> str:
        if self.qty > 1e-10:
            return "LONG"
        elif self.qty < -1e-10:
            return "SHORT"
        return "FLAT"

    @property
    def is_open(self) -> bool:
        return abs(self.qty) > 1e-10

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": self.unrealized_pnl,
            "side": self.side,
            "strategy_id": self.strategy_id,
            "n_fills": self.n_fills,
            "updated_at": self.updated_at,
        }


class PositionBook:
    """
    本地持仓簿 — Single Source of Truth

    用法：
        book = PositionBook()
        book.apply_fill("BTCUSDT", "BUY", 0.1, 50000, commission=5.0)
        book.update_prices({"BTCUSDT": 51000})
        print(book.get_position("BTCUSDT"))
    """

    def __init__(self) -> None:
        self._positions: Dict[str, Position] = {}

    @property
    def positions(self) -> Dict[str, Position]:
        return self._positions

    def get_position(self, symbol: str) -> Optional[Position]:
        return self._positions.get(symbol)

    def get_positions(self, include_closed: bool = False) -> List[Position]:
        """获取持仓列表"""
        if include_closed:
            return list(self._positions.values())
        return [p for p in self._positions.values() if p.is_open]

    def get_open_symbols(self) -> List[str]:
        """获取所有有持仓的品种"""
        return [s for s, p in self._positions.items() if p.is_open]

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
        """应用一笔成交到持仓簿"""
        if qty <= 0:
            raise ValueError(f"qty must be positive, got {qty}")

        signed_qty = qty if side == "BUY" else -qty
        now = int(time.time() * 1000)

        if symbol not in self._positions:
            self._positions[symbol] = Position(
                symbol=symbol,
                strategy_id=strategy_id,
                updated_at=now,
            )

        pos = self._positions[symbol]
        pos.n_fills += 1
        pos.updated_at = now

        # 累计成本/收入
        if side == "BUY":
            pos.total_cost += price * qty + commission
        else:
            pos.total_proceeds += price * qty - commission

        old_qty = pos.qty

        if old_qty == 0:
            # 新建仓
            pos.qty = signed_qty
            pos.avg_price = price
        elif (old_qty > 0) == (signed_qty > 0):
            # 加仓
            total_qty = old_qty + signed_qty
            pos.avg_price = (pos.avg_price * old_qty + price * signed_qty) / total_qty
            pos.qty = total_qty
        else:
            # 减仓或反手
            closing_qty = min(abs(signed_qty), abs(old_qty))
            if old_qty > 0:
                realized = (price - pos.avg_price) * closing_qty
            else:
                realized = (pos.avg_price - price) * closing_qty
            pos.realized_pnl += realized

            new_qty = old_qty + signed_qty
            if abs(new_qty) < 1e-10:
                # 清仓
                pos.qty = 0
                pos.avg_price = 0
            elif (new_qty > 0) != (old_qty > 0):
                # 反手
                pos.qty = new_qty
                pos.avg_price = price
            else:
                # 部分减仓
                pos.qty = new_qty

        # 更新未实现盈亏
        if pos.market_price > 0:
            pos.unrealized_pnl = (pos.market_price - pos.avg_price) * pos.qty

        if strategy_id and not pos.strategy_id:
            pos.strategy_id = strategy_id

        return pos

    # ------------------------------------------------------------------
    # 更新市场价格
    # ------------------------------------------------------------------
    def update_prices(self, prices: Dict[str, float]) -> None:
        """更新市场价格，重算未实现盈亏"""
        now = int(time.time() * 1000)
        for symbol, price in prices.items():
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.market_price = price
                pos.unrealized_pnl = (price - pos.avg_price) * pos.qty
                pos.updated_at = now

    def update_price(self, symbol: str, price: float) -> None:
        """更新单个品种的市场价格"""
        self.update_prices({symbol: price})

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------
    def total_realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self._positions.values())

    def total_unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self._positions.values() if p.is_open)

    def total_market_value(self) -> float:
        """总市值（多头 + 空头绝对值）"""
        return sum(abs(p.market_value) for p in self._positions.values() if p.is_open)

    def net_market_value(self) -> float:
        """净市值（多头 - 空头）"""
        return sum(p.market_value for p in self._positions.values() if p.is_open)

    def long_exposure(self) -> float:
        """多头敞口"""
        return sum(
            p.market_value for p in self._positions.values()
            if p.qty > 0
        )

    def short_exposure(self) -> float:
        """空头敞口"""
        return sum(
            abs(p.market_value) for p in self._positions.values()
            if p.qty < 0
        )

    def n_open_positions(self) -> int:
        return len(self.get_positions())

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict:
        return {
            "positions": {s: p.to_dict() for s, p in self._positions.items()},
            "total_realized_pnl": self.total_realized_pnl(),
            "total_unrealized_pnl": self.total_unrealized_pnl(),
            "total_market_value": self.total_market_value(),
            "net_market_value": self.net_market_value(),
            "long_exposure": self.long_exposure(),
            "short_exposure": self.short_exposure(),
            "n_open_positions": self.n_open_positions(),
        }

    def snapshot(self) -> List[Dict]:
        """导出所有持仓快照（用于持久化）"""
        return [p.to_dict() for p in self._positions.values()]

    def restore(self, positions: List[Dict]) -> None:
        """从快照恢复"""
        self._positions.clear()
        for p_dict in positions:
            symbol = p_dict["symbol"]
            self._positions[symbol] = Position(
                symbol=symbol,
                qty=p_dict.get("qty", 0),
                avg_price=p_dict.get("avg_price", 0),
                market_price=p_dict.get("market_price", 0),
                realized_pnl=p_dict.get("realized_pnl", 0),
                unrealized_pnl=p_dict.get("unrealized_pnl", 0),
                strategy_id=p_dict.get("strategy_id", ""),
                n_fills=p_dict.get("n_fills", 0),
                total_cost=p_dict.get("total_cost", 0),
                total_proceeds=p_dict.get("total_proceeds", 0),
            )
        logger.info(f"PositionBook restored {len(positions)} positions")

    def reset(self) -> None:
        """清空持仓簿"""
        self._positions.clear()

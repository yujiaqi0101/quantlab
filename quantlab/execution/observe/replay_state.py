"""
Replay State — 重放状态

随着事件推进不断更新：
    - positions  持仓
    - orders     订单
    - equity     权益
    - pnl        盈亏

ReplayEngine 重放事件时，每个事件应用到 ReplayState，
前端可以看到事件推进时状态的变化。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .event_store import StoredEvent

logger = logging.getLogger("quantlab.execution.observe.replay_state")


@dataclass
class ReplayPosition:
    """重放中的持仓"""
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0
    realized_pnl: float = 0.0
    # 当前市价（由 MarketEvent 更新）
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        if self.qty == 0 or self.avg_price == 0:
            return 0.0
        return (self.current_price - self.avg_price) * self.qty

    @property
    def market_value(self) -> float:
        return self.qty * self.current_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "realized_pnl": self.realized_pnl,
            "current_price": self.current_price,
            "unrealized_pnl": self.unrealized_pnl,
            "market_value": self.market_value,
        }


@dataclass
class ReplayOrder:
    """重放中的订单"""
    order_id: str
    symbol: str
    side: str  # BUY / SELL
    qty: float
    price: Optional[float]
    status: str  # CREATED / SUBMITTED / FILLED / CANCELLED / REJECTED
    filled_qty: float = 0.0
    filled_price: float = 0.0
    timestamp: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "price": self.price,
            "status": self.status,
            "filled_qty": self.filled_qty,
            "filled_price": self.filled_price,
            "timestamp": self.timestamp,
        }


@dataclass
class ReplayState:
    """
    重放状态

    随着事件推进，apply(event) 更新状态。
    """
    # 初始现金
    initial_cash: float = 10000.0
    # 当前现金
    cash: float = 10000.0
    # 持仓 {symbol: ReplayPosition}
    positions: Dict[str, ReplayPosition] = field(default_factory=dict)
    # 订单 {order_id: ReplayOrder}
    orders: Dict[str, ReplayOrder] = field(default_factory=dict)
    # 当前事件索引
    current_event_idx: int = -1
    # 当前时间戳
    current_timestamp: int = 0
    # 已处理事件数
    n_processed: int = 0
    # 最近一次市价 {symbol: price}
    last_prices: Dict[str, float] = field(default_factory=dict)

    @property
    def equity(self) -> float:
        """总权益 = 现金 + 持仓市值"""
        return self.cash + sum(p.market_value for p in self.positions.values())

    @property
    def unrealized_pnl(self) -> float:
        return sum(p.unrealized_pnl for p in self.positions.values())

    @property
    def realized_pnl(self) -> float:
        return sum(p.realized_pnl for p in self.positions.values())

    @property
    def total_pnl(self) -> float:
        return self.equity - self.initial_cash

    @property
    def n_open_orders(self) -> int:
        return sum(1 for o in self.orders.values() if o.status in ("CREATED", "SUBMITTED"))

    @property
    def n_positions(self) -> int:
        return sum(1 for p in self.positions.values() if p.qty != 0)

    def reset(self) -> None:
        """重置状态"""
        self.cash = self.initial_cash
        self.positions.clear()
        self.orders.clear()
        self.current_event_idx = -1
        self.current_timestamp = 0
        self.n_processed = 0
        self.last_prices.clear()

    def apply(self, event: StoredEvent) -> None:
        """应用事件，更新状态"""
        self.current_event_idx += 1
        self.current_timestamp = event.timestamp
        self.n_processed += 1

        try:
            handler = self._handlers.get(event.event_type)
            if handler:
                handler(event)
        except Exception as e:
            logger.warning(f"ReplayState apply error for {event.event_type}: {e}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_cash": self.initial_cash,
            "cash": self.cash,
            "equity": self.equity,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "total_pnl": self.total_pnl,
            "n_positions": self.n_positions,
            "n_open_orders": self.n_open_orders,
            "n_processed": self.n_processed,
            "current_event_idx": self.current_event_idx,
            "current_timestamp": self.current_timestamp,
            "positions": [p.to_dict() for p in self.positions.values()],
            "orders": [o.to_dict() for o in self.orders.values()],
            "last_prices": self.last_prices,
        }

    # ------------------------------------------------------------------
    # 事件处理器
    # ------------------------------------------------------------------

    def _on_market(self, event: StoredEvent) -> None:
        p = event.payload
        sym = p.get("symbol", "")
        price = p.get("price", 0.0)
        if sym and price:
            self.last_prices[sym] = price
            if sym in self.positions:
                self.positions[sym].current_price = price

    def _on_signal(self, event: StoredEvent) -> None:
        # 信号不直接改变状态，仅记录
        pass

    def _on_order(self, event: StoredEvent) -> None:
        p = event.payload
        oid = p.get("order_id", event.event_id)
        status = p.get("status", "SUBMITTED")

        if oid in self.orders:
            # 更新现有订单
            order = self.orders[oid]
            if "status" in p:
                order.status = p["status"]
            if "filled_qty" in p:
                order.filled_qty = p["filled_qty"]
            if "filled_price" in p:
                order.filled_price = p["filled_price"]
        else:
            # 新订单
            self.orders[oid] = ReplayOrder(
                order_id=oid,
                symbol=p.get("symbol", ""),
                side=p.get("side", "BUY"),
                qty=float(p.get("qty", p.get("quantity", 0))),
                price=p.get("price"),
                status=status,
                filled_qty=float(p.get("filled_qty", 0)),
                filled_price=float(p.get("filled_price", 0)),
                timestamp=event.timestamp,
            )

    def _on_fill(self, event: StoredEvent) -> None:
        p = event.payload
        oid = p.get("order_id", event.event_id)
        sym = p.get("symbol", "")
        side = p.get("side", "BUY")
        qty = float(p.get("qty", p.get("filled_qty", 0)))
        price = float(p.get("price", p.get("filled_price", 0)))
        fee = float(p.get("fee", 0))

        if not sym or qty <= 0:
            return

        # 更新订单
        if oid in self.orders:
            order = self.orders[oid]
            order.status = "FILLED"
            order.filled_qty = qty
            order.filled_price = price
        else:
            self.orders[oid] = ReplayOrder(
                order_id=oid,
                symbol=sym,
                side=side,
                qty=qty,
                price=price,
                status="FILLED",
                filled_qty=qty,
                filled_price=price,
                timestamp=event.timestamp,
            )

        # 更新持仓
        pos = self.positions.setdefault(sym, ReplayPosition(symbol=sym))
        if sym in self.last_prices:
            pos.current_price = self.last_prices[sym]
        else:
            pos.current_price = price

        if side.upper() == "BUY":
            # 买入：增加持仓，扣现金
            new_qty = pos.qty + qty
            if new_qty > 0:
                pos.avg_price = (pos.qty * pos.avg_price + qty * price) / new_qty
            pos.qty = new_qty
            self.cash -= qty * price + fee
        else:
            # 卖出：减少持仓，实现盈亏
            sell_qty = min(qty, pos.qty)
            if sell_qty > 0:
                realized = (price - pos.avg_price) * sell_qty
                pos.realized_pnl += realized
                pos.qty -= sell_qty
                self.cash += sell_qty * price - fee
                if pos.qty == 0:
                    pos.avg_price = 0.0
            else:
                # 空头卖出（简化处理）
                pos.qty -= qty
                pos.avg_price = price if pos.avg_price == 0 else pos.avg_price
                self.cash += qty * price - fee

    def _on_position_update(self, event: StoredEvent) -> None:
        p = event.payload
        sym = p.get("symbol", "")
        if not sym:
            return
        pos = self.positions.setdefault(sym, ReplayPosition(symbol=sym))
        if "qty" in p or "quantity" in p:
            pos.qty = float(p.get("qty", p.get("quantity", 0)))
        if "avg_price" in p:
            pos.avg_price = float(p["avg_price"])
        if "current_price" in p:
            pos.current_price = float(p["current_price"])

    def _on_risk(self, event: StoredEvent) -> None:
        # 风险事件不直接改变状态
        pass

    # 处理器映射（在 __post_init__ 中初始化）
    _handlers: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._handlers = {
            "MARKET_TICK": self._on_market,
            "MARKET_BAR": self._on_market,
            "MARKET": self._on_market,
            "SIGNAL": self._on_signal,
            "ORDER_NEW": self._on_order,
            "ORDER_UPDATE": self._on_order,
            "ORDER": self._on_order,
            "FILL": self._on_fill,
            "POSITION_UPDATE": self._on_position_update,
            "POSITION": self._on_position_update,
            "RISK_ALERT": self._on_risk,
            "RISK": self._on_risk,
            "KILL_SWITCH": self._on_risk,
        }

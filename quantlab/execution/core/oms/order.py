"""
OMS Order — 订单对象

OMS 是订单的唯一真相（Single Source of Truth）
所有订单创建、状态变更必须通过 OMS
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OrderState(str, Enum):
    """订单状态机"""
    NEW = "NEW"
    PENDING_SUBMIT = "PENDING_SUBMIT"
    SUBMITTED = "SUBMITTED"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


# 合法状态转换
VALID_TRANSITIONS: Dict[OrderState, List[OrderState]] = {
    OrderState.NEW: [OrderState.PENDING_SUBMIT, OrderState.CANCELLED, OrderState.REJECTED],
    OrderState.PENDING_SUBMIT: [OrderState.SUBMITTED, OrderState.REJECTED, OrderState.CANCELLED],
    OrderState.SUBMITTED: [OrderState.PARTIAL, OrderState.FILLED, OrderState.CANCELLED, OrderState.REJECTED, OrderState.EXPIRED],
    OrderState.PARTIAL: [OrderState.FILLED, OrderState.CANCELLED, OrderState.EXPIRED],
    OrderState.FILLED: [],
    OrderState.CANCELLED: [],
    OrderState.REJECTED: [],
    OrderState.EXPIRED: [],
}


@dataclass
class OMSOrder:
    """
    OMS 订单 — 系统内唯一的订单表示

    幂等性：通过 client_order_id 保证
    可追溯：完整的状态变更历史
    """
    symbol: str
    side: OrderSide
    quantity: int
    order_type: OrderType = OrderType.MARKET
    price: Optional[float] = None
    stop_price: Optional[float] = None

    # IDs
    id: str = field(default_factory=lambda: f"OMS-{uuid.uuid4().hex[:12]}")
    client_order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    broker_order_id: str = ""

    # 状态
    state: OrderState = OrderState.NEW
    filled_qty: int = 0
    avg_fill_price: float = 0.0
    reject_reason: str = ""

    # 时间戳
    created_at: int = 0
    submitted_at: int = 0
    filled_at: int = 0
    updated_at: int = 0

    # 来源
    strategy_id: str = ""
    signal_id: str = ""          # 幂等 key
    account_id: str = ""

    # 状态变更历史
    state_history: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        import time
        now = int(time.time() * 1000)
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        self._record_state(self.state, "ORDER_CREATED")

    @property
    def remaining_qty(self) -> int:
        return self.quantity - self.filled_qty

    @property
    def is_active(self) -> bool:
        return self.state in (
            OrderState.NEW,
            OrderState.PENDING_SUBMIT,
            OrderState.SUBMITTED,
            OrderState.PARTIAL,
        )

    @property
    def is_terminal(self) -> bool:
        return self.state in (
            OrderState.FILLED,
            OrderState.CANCELLED,
            OrderState.REJECTED,
            OrderState.EXPIRED,
        )

    def can_transition_to(self, new_state: OrderState) -> bool:
        return new_state in VALID_TRANSITIONS.get(self.state, [])

    def transition_to(
        self,
        new_state: OrderState,
        reason: str = "",
    ) -> bool:
        """状态转换（带合法性检查）"""
        if not self.can_transition_to(new_state):
            return False
        import time
        old_state = self.state
        self.state = new_state
        self.updated_at = int(time.time() * 1000)
        if new_state == OrderState.SUBMITTED and not self.submitted_at:
            self.submitted_at = self.updated_at
        if new_state == OrderState.FILLED:
            self.filled_at = self.updated_at
        self._record_state(new_state, reason or f"{old_state}→{new_state}")
        return True

    def apply_fill(self, fill_qty: int, fill_price: float) -> None:
        """应用成交"""
        if fill_qty <= 0:
            return
        total_cost = self.avg_fill_price * self.filled_qty + fill_price * fill_qty
        self.filled_qty += fill_qty
        self.avg_fill_price = total_cost / self.filled_qty if self.filled_qty > 0 else 0.0
        self.updated_at = int(time.time() * 1000)

        if self.filled_qty >= self.quantity:
            self.transition_to(OrderState.FILLED, "FULLY_FILLED")
        elif self.filled_qty > 0:
            self.transition_to(OrderState.PARTIAL, f"PARTIAL_{fill_qty}")

    def _record_state(self, state: OrderState, reason: str) -> None:
        import time
        self.state_history.append({
            "state": state.value,
            "reason": reason,
            "timestamp": int(time.time() * 1000),
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "price": self.price,
            "stop_price": self.stop_price,
            "state": self.state.value,
            "filled_qty": self.filled_qty,
            "avg_fill_price": self.avg_fill_price,
            "remaining_qty": self.remaining_qty,
            "reject_reason": self.reject_reason,
            "strategy_id": self.strategy_id,
            "signal_id": self.signal_id,
            "account_id": self.account_id,
            "created_at": self.created_at,
            "submitted_at": self.submitted_at,
            "filled_at": self.filled_at,
            "updated_at": self.updated_at,
            "state_history": self.state_history,
        }

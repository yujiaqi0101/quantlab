"""
OMS Order Manager — 订单管理器

OMS 是订单的唯一真相（Source of Truth）
所有订单操作必须通过 OrderManager

核心能力：
  1. 创建订单（带幂等检查）
  2. 状态管理（状态机）
  3. 订单查询
  4. 去重（client_order_id / signal_id）
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from .order import OMSOrder, OrderState, OrderSide, OrderType

logger = logging.getLogger("quantlab.execution.core.oms")


class OrderManager:
    """
    订单管理器 — OMS 核心

    用法：
        oms = OrderManager()
        order = oms.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=100,
            signal_id="sig_001",
        )
        oms.submit(order.id, broker_order_id="EX123")
        oms.apply_fill(order.id, fill_qty=100, fill_price=50000)
    """

    def __init__(self) -> None:
        self._orders: Dict[str, OMSOrder] = {}              # order_id → order
        self._client_id_map: Dict[str, str] = {}             # client_order_id → order_id
        self._signal_id_map: Dict[str, str] = {}             # signal_id → order_id
        self._broker_id_map: Dict[str, str] = {}             # broker_order_id → order_id

    def create_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        signal_id: str = "",
        strategy_id: str = "",
        account_id: str = "",
        client_order_id: str = "",
    ) -> Optional[OMSOrder]:
        """
        创建订单（带幂等检查）

        如果 signal_id 已存在，返回已有订单（幂等）
        如果 client_order_id 已存在，返回已有订单
        """
        # 幂等检查：signal_id
        if signal_id and signal_id in self._signal_id_map:
            existing_id = self._signal_id_map[signal_id]
            existing = self._orders[existing_id]
            logger.info(
                f"Idempotent: signal_id={signal_id} "
                f"already has order {existing_id} "
                f"(state={existing.state})"
            )
            return existing

        # 幂等检查：client_order_id
        if client_order_id and client_order_id in self._client_id_map:
            existing_id = self._client_id_map[client_order_id]
            return self._orders[existing_id]

        # 创建新订单
        order = OMSOrder(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=order_type,
            price=price,
            signal_id=signal_id,
            strategy_id=strategy_id,
            account_id=account_id,
            client_order_id=client_order_id or "",
        )

        self._register(order)
        logger.info(
            f"OMS create: {order.id} "
            f"{side.value} {quantity} {symbol} "
            f"signal_id={signal_id}"
        )
        return order

    def submit(
        self,
        order_id: str,
        broker_order_id: str = "",
    ) -> bool:
        """订单提交到交易所"""
        order = self._get(order_id)
        if not order:
            return False
        if broker_order_id:
            order.broker_order_id = broker_order_id
            self._broker_id_map[broker_order_id] = order_id
        return order.transition_to(OrderState.SUBMITTED, "BROKER_ACCEPTED")

    def reject(
        self,
        order_id: str,
        reason: str = "",
    ) -> bool:
        """订单被拒绝"""
        order = self._get(order_id)
        if not order:
            return False
        order.reject_reason = reason
        return order.transition_to(OrderState.REJECTED, reason)

    def cancel(self, order_id: str) -> bool:
        """取消订单"""
        order = self._get(order_id)
        if not order:
            return False
        return order.transition_to(OrderState.CANCELLED, "USER_CANCEL")

    def apply_fill(
        self,
        order_id: str,
        fill_qty: int,
        fill_price: float,
    ) -> bool:
        """应用成交回报"""
        order = self._get(order_id)
        if not order:
            return False
        order.apply_fill(fill_qty, fill_price)
        logger.info(
            f"OMS fill: {order_id} "
            f"qty={fill_qty} price={fill_price} "
            f"state={order.state}"
        )
        return True

    def get_order(self, order_id: str) -> Optional[OMSOrder]:
        return self._orders.get(order_id)

    def get_by_client_id(self, client_order_id: str) -> Optional[OMSOrder]:
        oid = self._client_id_map.get(client_order_id)
        return self._orders.get(oid) if oid else None

    def get_by_broker_id(self, broker_order_id: str) -> Optional[OMSOrder]:
        oid = self._broker_id_map.get(broker_order_id)
        return self._orders.get(oid) if oid else None

    def get_by_signal_id(self, signal_id: str) -> Optional[OMSOrder]:
        oid = self._signal_id_map.get(signal_id)
        return self._orders.get(oid) if oid else None

    def get_active_orders(self) -> List[OMSOrder]:
        return [o for o in self._orders.values() if o.is_active]

    def get_all_orders(self) -> List[OMSOrder]:
        return list(self._orders.values())

    def get_orders_by_strategy(self, strategy_id: str) -> List[OMSOrder]:
        return [o for o in self._orders.values() if o.strategy_id == strategy_id]

    def get_orders_by_symbol(self, symbol: str) -> List[OMSOrder]:
        return [o for o in self._orders.values() if o.symbol == symbol]

    def cancel_all(self, strategy_id: str = "") -> int:
        """取消所有活动订单（Kill Switch 用）"""
        count = 0
        for order in self._orders.values():
            if order.is_active:
                if not strategy_id or order.strategy_id == strategy_id:
                    if order.transition_to(OrderState.CANCELLED, "CANCEL_ALL"):
                        count += 1
        logger.warning(f"OMS cancel_all: {count} orders cancelled")
        return count

    def restore(self, orders: List[OMSOrder]) -> None:
        """从持久化恢复订单"""
        for order in orders:
            self._register(order)
        logger.info(f"OMS restored {len(orders)} orders")

    def snapshot(self) -> List[Dict]:
        """导出所有订单（用于持久化）"""
        return [o.to_dict() for o in self._orders.values()]

    def _register(self, order: OMSOrder) -> None:
        self._orders[order.id] = order
        self._client_id_map[order.client_order_id] = order.id
        if order.signal_id:
            self._signal_id_map[order.signal_id] = order.id
        if order.broker_order_id:
            self._broker_id_map[order.broker_order_id] = order.id

    def _get(self, order_id: str) -> Optional[OMSOrder]:
        order = self._orders.get(order_id)
        if not order:
            logger.warning(f"OMS: order not found: {order_id}")
        return order

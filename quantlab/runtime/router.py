"""
OrderRouter：Order → Account → Broker（V3.4）

V3.4 关键：
    一个 strategy 输出的 Order
    需要按 allocation 拆到 N 个 account
    每个 account 找自己的 broker
    投递

OrderRouter 与 StrategyRuntime 的协作：
    1) StrategyRuntime.on_bar() 产生 orders
    2) Router.route(orders, runtime_id)
        → 按 allocation 拆
        → 调对应 account 的 broker.submit_order()

为什么独立成 Router：
    拆单逻辑共享（不要在每个 runtime 里复制）
    测试更容易（mock broker 即可）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..core.order import Order
from .account_manager import AccountManager
from .allocation import AllocationEngine


logger = logging.getLogger("quantlab.order_router")


@dataclass
class RoutedOrder:
    """V3.4 路由后的子单"""
    parent_order: Order
    account_id: str
    broker: Any
    quantity: int                          # 拆后数量
    original_qty: int                       # 原数量
    client_order_id: str = ""


class OrderRouter:
    """
    V3.4 OrderRouter

    用法：
        router = OrderRouter(
            account_manager=am,
            allocation_engine=ae,
        )
        # 注册 strategy → runtime
        router.register_runtime("strategy_A", broker=broker_a)
        router.register_runtime("strategy_B", broker=broker_b)

        # 在主循环里：
        for rt in runtimes:
            for o in rt.execution_orders():
                routed = router.route(
                    order=o,
                    strategy_id=rt.strategy_id,
                )
                for ro in routed:
                    ro.broker.submit_order(ro.order)
    """

    def __init__(
        self,
        account_manager: AccountManager,
        allocation_engine: AllocationEngine,
    ):
        self.am = account_manager
        self.ae = allocation_engine

        # strategy_id → broker 映射
        # （V3.4 简化：每个 strategy 对应一个 broker）
        self.strategy_brokers: Dict[str, Any] = {}

    def register_runtime(
        self,
        strategy_id: str,
        broker: Any,
    ) -> None:
        self.strategy_brokers[strategy_id] = broker

    def route(
        self,
        order: Order,
        strategy_id: str,
    ) -> List[RoutedOrder]:
        """
        拆单 → 路由

        输入：1 个 Order (symbol, quantity)
        输出：N 个 RoutedOrder，每个绑定 account + broker
        """
        if strategy_id not in self.strategy_brokers:
            logger.warning(
                f"strategy {strategy_id!r} has no broker"
            )
            return []

        # 1) 按 allocation 拆
        splits = self.ae.split(
            strategy_id=strategy_id,
            shares=abs(order.quantity),
            account_manager=self.am,
        )

        if not splits:
            return []

        sign = 1 if order.quantity > 0 else -1
        out: List[RoutedOrder] = []
        broker = self.strategy_brokers[strategy_id]

        for acc_id, qty in splits:
            sub_qty = sign * qty
            if sub_qty == 0:
                continue

            # 子单：保留 client_order_id 不变（同一笔决策）
            # 加 sub_id 区分多个子单
            sub = Order(
                symbol=order.symbol,
                quantity=sub_qty,
                price=order.price,
                order_type=order.order_type,
                client_order_id=order.client_order_id,
            )
            sub.id = f"{order.id or 'X'}.{acc_id}"
            sub.side = "BUY" if sub_qty > 0 else "SELL"

            out.append(RoutedOrder(
                parent_order=order,
                account_id=acc_id,
                broker=broker,
                quantity=sub_qty,
                original_qty=order.quantity,
                client_order_id=sub.client_order_id,
            ))

        return out

    def route_and_submit(
        self,
        order: Order,
        strategy_id: str,
    ) -> List[str]:
        """
        直接路由 + 提交
        返回 broker 返回的 broker_id 列表
        """
        routed = self.route(order, strategy_id)
        broker_ids: List[str] = []
        for ro in routed:
            try:
                bid = ro.broker.submit_order(ro.order)
                broker_ids.append(bid)
            except Exception as e:
                logger.warning(
                    f"submit fail on acc {ro.account_id}: {e}"
                )
        return broker_ids

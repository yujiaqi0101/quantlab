"""
Order Recovery — 订单恢复

系统重启后同步交易所订单状态：
  1. 查询交易所所有活动订单
  2. 对比本地 OMS 状态
  3. 同步状态差异
"""

from __future__ import annotations

import logging
from typing import Dict, List

from ...core.oms.order_manager import OrderManager
from ...core.oms.order import OrderState

logger = logging.getLogger("quantlab.execution.runtime.recovery.order_recovery")


class OrderRecovery:
    """
    订单恢复器

    用法：
        recovery = OrderRecovery(oms=oms)
        recovery.sync_from_exchange(
            fetch_active_orders=broker.get_active_orders,
            fetch_fills=broker.get_recent_fills,
        )
    """

    def __init__(self, oms: OrderManager) -> None:
        self.oms = oms

    def sync_from_exchange(
        self,
        fetch_active_orders: callable,
        fetch_fills: callable = None,
    ) -> Dict:
        """
        从交易所同步订单状态

        返回同步统计
        """
        stats = {
            "synced": 0,
            "updated": 0,
            "new_fills": 0,
            "errors": 0,
        }

        # 1. 同步活动订单
        try:
            exchange_orders = fetch_active_orders()
            for ex_order in exchange_orders:
                broker_id = ex_order.get("broker_order_id", "")
                if not broker_id:
                    continue

                local_order = self.oms.get_by_broker_id(broker_id)
                if not local_order:
                    logger.warning(
                        f"OrderRecovery: exchange order {broker_id} "
                        f"not found locally"
                    )
                    continue

                # 同步状态
                ex_state = ex_order.get("state", "")
                if ex_state and ex_state != local_order.state.value:
                    try:
                        new_state = OrderState(ex_state)
                        if local_order.can_transition_to(new_state):
                            local_order.transition_to(new_state, "EXCHANGE_SYNC")
                            stats["updated"] += 1
                    except ValueError:
                        pass

                # 同步成交量
                ex_filled = ex_order.get("filled_qty", 0)
                if ex_filled > local_order.filled_qty:
                    fill_price = ex_order.get("avg_fill_price", 0)
                    delta = ex_filled - local_order.filled_qty
                    self.oms.apply_fill(local_order.id, delta, fill_price)
                    stats["new_fills"] += 1

                stats["synced"] += 1

        except Exception as e:
            logger.error(f"OrderRecovery: sync failed: {e}")
            stats["errors"] += 1

        # 2. 同步最近成交
        if fetch_fills:
            try:
                recent_fills = fetch_fills()
                for fill_data in recent_fills:
                    broker_id = fill_data.get("broker_order_id", "")
                    local_order = self.oms.get_by_broker_id(broker_id)
                    if local_order and fill_data.get("fill_qty", 0) > 0:
                        # 检查是否已处理
                        existing_fills = self.oms.get_order(local_order.id)
                        if existing_fills and existing_fills.filled_qty < fill_data.get("total_filled", 0):
                            delta = fill_data["total_filled"] - existing_fills.filled_qty
                            self.oms.apply_fill(
                                local_order.id,
                                delta,
                                fill_data.get("fill_price", 0),
                            )
                            stats["new_fills"] += 1
            except Exception as e:
                logger.error(f"OrderRecovery: fill sync failed: {e}")
                stats["errors"] += 1

        logger.info(
            f"OrderRecovery: synced={stats['synced']}, "
            f"updated={stats['updated']}, "
            f"new_fills={stats['new_fills']}, "
            f"errors={stats['errors']}"
        )
        return stats

    def cancel_orphaned_orders(self) -> int:
        """取消本地活动但交易所不存在的订单"""
        active = self.oms.get_active_orders()
        count = 0
        for order in active:
            if order.transition_to(OrderState.CANCELLED, "ORPHANED_RECOVERY"):
                count += 1
                logger.warning(
                    f"OrderRecovery: cancelled orphaned order {order.id}"
                )
        return count

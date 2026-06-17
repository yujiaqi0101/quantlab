"""
Self-Healing System — 自愈系统

当检测到异常时自动执行恢复：
  1. 数据异常 → 重新订阅行情
  2. 订单失败 → 重试或取消
  3. 连接断开 → 自动重连
  4. 状态不一致 → 触发对账
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from .recovery.state_restore import StateRestorer
from .recovery.order_recovery import OrderRecovery
from .recovery.position_recovery import PositionRecovery

logger = logging.getLogger("quantlab.execution.runtime.self_healing")


class HealingAction(str, Enum):
    RECONNECT_WEBSOCKET = "RECONNECT_WEBSOCKET"
    RESUBSCRIBE_MARKET = "RESUBSCRIBE_MARKET"
    RETRY_ORDER = "RETRY_ORDER"
    CANCEL_ORDER = "CANCEL_ORDER"
    RECONCILE_POSITIONS = "RECONCILE_POSITIONS"
    RECONCILE_ORDERS = "RECONCILE_ORDERS"
    RESTORE_STATE = "RESTORE_STATE"
    RESTART_STRATEGY = "RESTART_STRATEGY"


@dataclass
class HealingEvent:
    """自愈事件"""
    action: HealingAction
    reason: str
    timestamp: int
    success: bool = False
    error: str = ""
    context: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "action": self.action.value,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "success": self.success,
            "error": self.error,
            "context": self.context,
        }


class SelfHealingSystem:
    """
    自愈系统

    用法：
        healing = SelfHealingSystem(
            state_restorer=restorer,
            order_recovery=order_recovery,
            position_recovery=position_recovery,
        )
        healing.register_action(HealingAction.RECONNECT_WEBSOCKET, ws_reconnect_fn)
        healing.register_action(HealingAction.RESUBSCRIBE_MARKET, resubscribe_fn)
        healing.trigger(HealingAction.RECONNECT_WEBSOCKET, "WebSocket disconnected")
    """

    def __init__(
        self,
        state_restorer: Optional[StateRestorer] = None,
        order_recovery: Optional[OrderRecovery] = None,
        position_recovery: Optional[PositionRecovery] = None,
    ) -> None:
        self.state_restorer = state_restorer
        self.order_recovery = order_recovery
        self.position_recovery = position_recovery

        self._actions: Dict[HealingAction, Callable] = {}
        self._history: List[HealingEvent] = []
        self._lock = threading.RLock()
        self._max_retries: int = 3
        self._retry_delay: float = 1.0

    def register_action(
        self,
        action: HealingAction,
        callback: Callable,
    ) -> None:
        self._actions[action] = callback
        logger.info(f"SelfHealing: registered action {action.value}")

    def trigger(
        self,
        action: HealingAction,
        reason: str,
        context: Dict = None,
    ) -> bool:
        """触发自愈动作"""
        callback = self._actions.get(action)
        if not callback:
            logger.warning(f"SelfHealing: no handler for {action.value}")
            return False

        event = HealingEvent(
            action=action,
            reason=reason,
            timestamp=int(time.time() * 1000),
            context=context or {},
        )

        for attempt in range(self._max_retries):
            try:
                callback(**context or {})
                event.success = True
                logger.info(
                    f"SelfHealing: {action.value} succeeded "
                    f"(attempt {attempt + 1})"
                )
                break
            except Exception as e:
                event.error = str(e)
                logger.error(
                    f"SelfHealing: {action.value} attempt {attempt + 1} "
                    f"failed: {e}"
                )
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay * (attempt + 1))

        with self._lock:
            self._history.append(event)

        return event.success

    def heal_data_anomaly(self, symbol: str, reason: str) -> bool:
        """数据异常自愈"""
        return self.trigger(
            HealingAction.RESUBSCRIBE_MARKET,
            reason=f"Data anomaly for {symbol}: {reason}",
            context={"symbol": symbol},
        )

    def heal_connection_lost(self, reason: str = "") -> bool:
        """连接断开自愈"""
        return self.trigger(
            HealingAction.RECONNECT_WEBSOCKET,
            reason=f"Connection lost: {reason}",
        )

    def heal_order_failed(self, order_id: str, reason: str) -> bool:
        """订单失败自愈"""
        return self.trigger(
            HealingAction.RETRY_ORDER,
            reason=f"Order {order_id} failed: {reason}",
            context={"order_id": order_id},
        )

    def heal_state_inconsistency(self, reason: str) -> bool:
        """状态不一致自愈"""
        # 先尝试对账
        success = self.trigger(
            HealingAction.RECONCILE_POSITIONS,
            reason=f"State inconsistency: {reason}",
        )
        if not success:
            # 对账失败，尝试完整状态恢复
            success = self.trigger(
                HealingAction.RESTORE_STATE,
                reason=f"Reconciliation failed, full restore: {reason}",
            )
        return success

    def get_history(self, limit: int = 50) -> List[HealingEvent]:
        with self._lock:
            return self._history[-limit:]

    def get_stats(self) -> Dict:
        with self._lock:
            total = len(self._history)
            success = sum(1 for e in self._history if e.success)
            return {
                "total_heals": total,
                "successful": success,
                "failed": total - success,
                "success_rate": success / total if total > 0 else 0.0,
            }

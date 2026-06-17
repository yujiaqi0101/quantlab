"""
Idempotent Execution — 幂等执行

实盘核心中的核心：
  - 同一个信号执行两次 → 不会下两笔单
  - signal_id 唯一
  - 重复执行 = 0 影响

基于 OMS 的 signal_id 去重机制
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from ..core.oms.order_manager import OrderManager
from ..core.oms.order import OMSOrder, OrderSide, OrderType

logger = logging.getLogger("quantlab.execution.runtime.idempotent")


@dataclass
class SignalFingerprint:
    """信号指纹 — 用于幂等检查"""
    signal_id: str
    strategy_id: str
    symbol: str
    side: str
    qty: float
    price: Optional[float]
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not self.fingerprint:
            raw = f"{self.strategy_id}|{self.symbol}|{self.side}|{self.qty}|{self.price or 0}"
            self.fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:16]


class IdempotentExecutor:
    """
    幂等执行器

    保证：
      1. 同一 signal_id 不会创建多个订单
      2. 同一信号指纹不会创建多个订单
      3. 重复执行 = 0 影响

    用法：
        executor = IdempotentExecutor(oms=oms)
        order, is_new = executor.execute_signal(
            signal_id="sig_001",
            strategy_id="s1",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            qty=100,
        )
        if is_new:
            print(f"New order created: {order.id}")
        else:
            print(f"Duplicate signal, existing order: {order.id}")
    """

    def __init__(self, oms: OrderManager) -> None:
        self.oms = oms
        self._fingerprints: Dict[str, str] = {}  # fingerprint → order_id
        self._execution_log: list = []

    def execute_signal(
        self,
        signal_id: str,
        strategy_id: str,
        symbol: str,
        side: OrderSide,
        qty: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
    ) -> Tuple[Optional[OMSOrder], bool]:
        """
        幂等执行信号

        返回 (order, is_new)
          - is_new=True: 新建订单
          - is_new=False: 重复信号，返回已有订单
        """
        # 1. signal_id 去重（OMS 内置）
        existing = self.oms.get_by_signal_id(signal_id)
        if existing:
            logger.info(
                f"Idempotent: signal_id={signal_id} "
                f"already executed as order {existing.id} "
                f"(state={existing.state})"
            )
            self._log_execution(signal_id, existing.id, is_new=False, reason="signal_id_exists")
            return existing, False

        # 2. 指纹去重（防止不同 signal_id 但相同参数）
        fingerprint = SignalFingerprint(
            signal_id=signal_id,
            strategy_id=strategy_id,
            symbol=symbol,
            side=side.value,
            qty=qty,
            price=price,
        )

        if fingerprint.fingerprint in self._fingerprints:
            existing_id = self._fingerprints[fingerprint.fingerprint]
            existing_order = self.oms.get_order(existing_id)
            if existing_order:
                logger.warning(
                    f"Idempotent: fingerprint match for signal_id={signal_id} "
                    f"→ existing order {existing_id}"
                )
                self._log_execution(
                    signal_id, existing_id, is_new=False,
                    reason="fingerprint_match",
                )
                return existing_order, False

        # 3. 创建新订单
        order = self.oms.create_order(
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type=order_type,
            price=price,
            signal_id=signal_id,
            strategy_id=strategy_id,
        )

        if order:
            self._fingerprints[fingerprint.fingerprint] = order.id
            self._log_execution(signal_id, order.id, is_new=True)
            logger.info(
                f"Idempotent: new order {order.id} for signal_id={signal_id}"
            )

        return order, True

    def _log_execution(
        self,
        signal_id: str,
        order_id: str,
        is_new: bool,
        reason: str = "",
    ) -> None:
        self._execution_log.append({
            "signal_id": signal_id,
            "order_id": order_id,
            "is_new": is_new,
            "reason": reason,
            "timestamp": int(time.time() * 1000),
        })

    def get_execution_log(self, limit: int = 100) -> list:
        return self._execution_log[-limit:]

    def get_stats(self) -> Dict:
        """获取幂等执行统计"""
        total = len(self._execution_log)
        duplicates = sum(1 for e in self._execution_log if not e["is_new"])
        return {
            "total_executions": total,
            "duplicates_blocked": duplicates,
            "new_orders": total - duplicates,
            "dedup_rate": duplicates / total if total > 0 else 0.0,
        }

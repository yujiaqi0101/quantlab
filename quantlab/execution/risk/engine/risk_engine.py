"""
Risk Engine — 风控引擎

所有订单必须经过 Risk Engine
Risk Engine 串联所有 RiskLimit

核心原则：
  所有订单 → Risk Engine → 通过/拒绝
  Kill Switch 触发后 → 拒绝所有新单
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..limits import RiskLimit

logger = logging.getLogger("quantlab.execution.risk.engine")


class RiskEngine:
    """
    风控引擎

    用法：
        engine = RiskEngine()
        engine.add_limit(PositionLimit(max_qty=10000))
        engine.add_limit(ExposureLimit(max_exposure=0.8))
        engine.add_limit(LossLimit(max_loss=-0.05))

        ok, reason = engine.check(
            order_qty=100,
            symbol="BTCUSDT",
            current_positions=portfolio.positions,
            current_equity=portfolio.equity(),
            price=50000,
        )
        if not ok:
            logger.warning(f"Order rejected: {reason}")
    """

    def __init__(self) -> None:
        self._limits: List[RiskLimit] = []
        self._kill_switch_active: bool = False
        self._reject_log: List[Dict] = []

    def add_limit(self, limit: RiskLimit) -> None:
        self._limits.append(limit)
        logger.info(f"RiskEngine add limit: {limit.name}")

    def remove_limit(self, name: str) -> None:
        self._limits = [l for l in self._limits if l.name != name]

    def activate_kill_switch(self) -> None:
        """激活 Kill Switch — 拒绝所有新单"""
        self._kill_switch_active = True
        logger.critical("RiskEngine: KILL SWITCH ACTIVATED")

    def deactivate_kill_switch(self) -> None:
        self._kill_switch_active = False
        logger.info("RiskEngine: Kill switch deactivated")

    @property
    def kill_switch_active(self) -> bool:
        return self._kill_switch_active

    def check(
        self,
        order_qty: int,
        symbol: str,
        current_positions: Dict[str, float],
        current_equity: float,
        price: float = 0.0,
        daily_pnl: float = 0.0,
    ) -> tuple[bool, str]:
        """检查订单是否通过风控"""
        if self._kill_switch_active:
            reason = "Kill switch active - all orders rejected"
            self._reject_log.append({
                "symbol": symbol,
                "qty": order_qty,
                "reason": reason,
            })
            return False, reason

        for limit in self._limits:
            try:
                ok, reason = limit.check(
                    order_qty=order_qty,
                    symbol=symbol,
                    current_positions=current_positions,
                    current_equity=current_equity,
                    price=price,
                    daily_pnl=daily_pnl,
                )
            except Exception as e:
                logger.error(f"Risk limit {limit.name} error: {e}")
                ok, reason = False, f"Risk check error: {e}"

            if not ok:
                self._reject_log.append({
                    "symbol": symbol,
                    "qty": order_qty,
                    "limit": limit.name,
                    "reason": reason,
                })
                logger.warning(f"RiskEngine reject: {reason}")
                return False, reason

        return True, ""

    @property
    def rejects(self) -> List[Dict]:
        return list(self._reject_log)

    def reset_rejects(self) -> None:
        self._reject_log.clear()

    def get_limits(self) -> List[RiskLimit]:
        return list(self._limits)

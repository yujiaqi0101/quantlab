"""
RiskManager：串联多个 RiskCheck

V3.1：迁移自 risk/risk_manager.py
"""

from typing import Dict, List, Optional

from ...core.order import Order
from .checks import RiskCheck


class RiskManager:
    """
    V1 简化：
        - 所有 check 全过才算通过
        - 第一个失败即拒
        - 不做软警告
    """

    def __init__(self, checks: Optional[List[RiskCheck]] = None):
        self.checks: List[RiskCheck] = checks or []
        self._reject_log: List[Dict] = []

    def add_check(self, check: RiskCheck) -> None:
        self.checks.append(check)

    def check(
        self,
        order: Order,
        context: Optional[Dict] = None,
    ) -> bool:
        ctx = context or {}
        for c in self.checks:
            try:
                ok = c.check(order, ctx)
            except Exception:
                ok = False
            if not ok:
                self._reject_log.append({
                    "order": order,
                    "check": c.name,
                    "context": ctx,
                })
                return False
        return True

    @property
    def rejects(self) -> List[Dict]:
        return list(self._reject_log)

    def reset_rejects(self) -> None:
        self._reject_log.clear()

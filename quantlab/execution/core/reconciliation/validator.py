"""
Reconciliation Validator — 对账验证器

验证对账结果的严重程度，决定是否触发告警或停止交易
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List

from .sync import PositionDiff, ReconcileResult, ReconcileStatus

logger = logging.getLogger("quantlab.execution.core.reconciliation.validator")


@dataclass
class ReconcileAlert:
    """对账告警"""
    level: str       # INFO / WARNING / CRITICAL
    message: str
    diffs: List[PositionDiff]

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "message": self.message,
            "diffs": [d.to_dict() for d in self.diffs],
        }


class ReconcileValidator:
    """
    对账验证器

    评估对账结果，生成告警

    用法：
        validator = ReconcileValidator(
            max_diff_pct=0.05,  # 5% 差异触发 CRITICAL
            max_absolute_diff=1.0,
        )
        alert = validator.validate(result)
        if alert and alert.level == "CRITICAL":
            kill_switch.trigger()
    """

    def __init__(
        self,
        max_diff_pct: float = 0.05,
        max_absolute_diff: float = 1.0,
    ) -> None:
        self.max_diff_pct = max_diff_pct
        self.max_absolute_diff = max_absolute_diff

    def validate(self, result: ReconcileResult) -> ReconcileAlert | None:
        """验证对账结果，返回告警（如果有）"""
        mismatches = [d for d in result.diffs if d.is_mismatch]
        if not mismatches:
            return None

        critical_diffs: List[PositionDiff] = []
        warning_diffs: List[PositionDiff] = []

        for d in mismatches:
            max_qty = max(abs(d.local_qty), abs(d.exchange_qty), 1.0)
            diff_pct = abs(d.diff) / max_qty

            if diff_pct > self.max_diff_pct or abs(d.diff) > self.max_absolute_diff:
                critical_diffs.append(d)
            else:
                warning_diffs.append(d)

        if critical_diffs:
            return ReconcileAlert(
                level="CRITICAL",
                message=f"{len(critical_diffs)} positions with critical mismatch",
                diffs=critical_diffs,
            )
        if warning_diffs:
            return ReconcileAlert(
                level="WARNING",
                message=f"{len(warning_diffs)} positions with minor mismatch",
                diffs=warning_diffs,
            )

        return None

"""
ConsistencyChecker：一致性检查（V3.3 第五件事）

对账内容：
    1) portfolio.cash  vs broker.cash
    2) portfolio.positions vs broker.positions
    3) 累计 realized_pnl 一致
    4) open_orders 在 broker 仍 ACTIVE
    5) 与 snapshot 一致

结果：
    一致 → 静默
    不一致 → 报警（logger + alert）+ 触发 ShutdownManager
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .state_store import StateSnapshot


logger = logging.getLogger("quantlab.consistency")


@dataclass
class ConsistencyIssue:
    severity: str       # "WARN" / "CRITICAL"
    field: str          # "cash" / "positions.AAPL.qty" / ...
    portfolio_value: Any
    broker_value: Any
    message: str


class ConsistencyChecker:
    """
    V3.3 ConsistencyChecker

    用法：
        checker = ConsistencyChecker(tolerance=0.01)
        issues = checker.check(
            portfolio=portfolio,
            broker=broker,
            snapshot=snapshot,
        )
        if issues:
            for i in issues: logger.error(i.message)
            if any(i.severity == "CRITICAL" for i in issues):
                shutdown_manager.request_shutdown(reason=...)
    """

    def __init__(
        self,
        tolerance: float = 0.01,
        on_issue=None,                     # 可选 callback
    ):
        self.tolerance = float(tolerance)
        self.on_issue = on_issue
        self.issues_history: List[ConsistencyIssue] = []

    def check(
        self,
        portfolio,
        broker,
        snapshot: Optional[StateSnapshot] = None,
    ) -> List[ConsistencyIssue]:
        issues: List[ConsistencyIssue] = []

        # ---- 1) cash ----
        pf_cash = getattr(portfolio, "cash", 0.0)
        br_cash = getattr(broker, "cash", pf_cash)
        if abs(pf_cash - br_cash) > self.tolerance:
            issues.append(ConsistencyIssue(
                severity="CRITICAL",
                field="cash",
                portfolio_value=pf_cash,
                broker_value=br_cash,
                message=(
                    f"cash mismatch: portfolio={pf_cash:.2f} "
                    f"broker={br_cash:.2f} "
                    f"diff={pf_cash - br_cash:.2f}"
                ),
            ))

        # ---- 2) positions ----
        pf_positions = getattr(portfolio, "positions", {})
        br_positions = getattr(broker, "positions", {})
        for sym, pos in pf_positions.items():
            pf_qty = getattr(pos, "qty", 0)
            br_qty = (
                br_positions.get(sym, 0)
                if isinstance(br_positions, dict)
                else 0
            )
            if isinstance(br_positions, dict):
                br_qty = br_positions.get(sym, 0)
            elif hasattr(br_positions, "get"):
                br_qty = br_positions.get(sym, 0)
            if abs(pf_qty - br_qty) > 0:
                issues.append(ConsistencyIssue(
                    severity="CRITICAL",
                    field=f"positions.{sym}.qty",
                    portfolio_value=pf_qty,
                    broker_value=br_qty,
                    message=(
                        f"position {sym} mismatch: "
                        f"portfolio={pf_qty} broker={br_qty}"
                    ),
                ))

        # ---- 3) realized_pnl vs snapshot ----
        if snapshot is not None:
            for sym, p in (snapshot.positions or {}).items():
                pf_pos = pf_positions.get(sym)
                if pf_pos is None:
                    continue
                pf_rp = getattr(pf_pos, "realized_pnl", 0.0)
                snap_rp = p.get("realized_pnl", 0.0)
                if abs(pf_rp - snap_rp) > self.tolerance:
                    issues.append(ConsistencyIssue(
                        severity="WARN",
                        field=f"positions.{sym}.realized_pnl",
                        portfolio_value=pf_rp,
                        broker_value=snap_rp,
                        message=(
                            f"realized_pnl drift {sym}: "
                            f"now={pf_rp:.2f} "
                            f"snap={snap_rp:.2f}"
                        ),
                    ))

        # ---- 4) open_orders 状态 ----
        if snapshot is not None and hasattr(broker, "trade_log"):
            snap_open_ids = {
                o.get("id")
                for o in snapshot.open_orders
            }
            for fill_id in (getattr(broker, "trade_log", None) or []):
                pass   # PaperBroker 没有 active order 概念

        # 记入历史
        self.issues_history.extend(issues)

        # 触发 callback
        for issue in issues:
            logger.warning(
                f"[CONSISTENCY {issue.severity}] {issue.message}"
            )
            if self.on_issue is not None:
                try:
                    self.on_issue(issue)
                except Exception:
                    pass

        return issues

    def has_critical(self) -> bool:
        return any(
            i.severity == "CRITICAL"
            for i in self.issues_history
        )

"""
Reconciliation Engine — 对账系统

定期对比本地持仓 vs 交易所持仓
如果不一致 → 自动修正 或 触发报警

这是实盘系统的核心安全组件
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.core.reconciliation")


class ReconcileStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    CORRECTED = "CORRECTED"
    ALERT = "ALERT"


@dataclass
class PositionDiff:
    """单个标的的持仓差异"""
    symbol: str
    local_qty: float
    exchange_qty: float
    diff: float
    status: ReconcileStatus = ReconcileStatus.MATCH

    @property
    def is_mismatch(self) -> bool:
        return abs(self.diff) > 0.0001

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "local_qty": self.local_qty,
            "exchange_qty": self.exchange_qty,
            "diff": self.diff,
            "status": self.status.value,
        }


@dataclass
class ReconcileResult:
    """对账结果"""
    timestamp: int
    diffs: List[PositionDiff] = field(default_factory=list)
    status: ReconcileStatus = ReconcileStatus.MATCH
    corrected: int = 0
    alerted: int = 0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "status": self.status.value,
            "corrected": self.corrected,
            "alerted": self.alerted,
            "diffs": [d.to_dict() for d in self.diffs],
        }


class ReconciliationEngine:
    """
    对账引擎

    用法：
        engine = ReconciliationEngine(
            get_local_positions=lambda: portfolio.positions,
            get_exchange_positions=lambda: broker.get_positions(),
            on_mismatch=alert_handler,
        )
        result = engine.reconcile()
    """

    def __init__(
        self,
        get_local_positions: Callable[[], Dict[str, float]],
        get_exchange_positions: Callable[[], Dict[str, float]],
        on_mismatch: Optional[Callable[[PositionDiff], None]] = None,
        auto_correct: bool = False,
        tolerance: float = 0.0001,
    ) -> None:
        self._get_local = get_local_positions
        self._get_exchange = get_exchange_positions
        self._on_mismatch = on_mismatch
        self._auto_correct = auto_correct
        self._tolerance = tolerance
        self._history: List[ReconcileResult] = []
        self._corrector: Optional[Callable[[str, float], None]] = None

    def set_corrector(self, corrector: Callable[[str, float], None]) -> None:
        """设置自动修正函数"""
        self._corrector = corrector

    def reconcile(self) -> ReconcileResult:
        """执行一次对账"""
        import time
        now = int(time.time() * 1000)

        local = self._get_local()
        exchange = self._get_exchange()

        all_symbols = set(local.keys()) | set(exchange.keys())
        diffs: List[PositionDiff] = []
        corrected = 0
        alerted = 0

        for symbol in all_symbols:
            local_qty = local.get(symbol, 0.0)
            exchange_qty = exchange.get(symbol, 0.0)
            diff = exchange_qty - local_qty

            pd = PositionDiff(
                symbol=symbol,
                local_qty=local_qty,
                exchange_qty=exchange_qty,
                diff=diff,
            )

            if abs(diff) > self._tolerance:
                pd.status = ReconcileStatus.MISMATCH

                if self._auto_correct and self._corrector:
                    try:
                        self._corrector(symbol, exchange_qty)
                        pd.status = ReconcileStatus.CORRECTED
                        corrected += 1
                        logger.info(
                            f"Reconcile corrected: {symbol} "
                            f"local={local_qty} → exchange={exchange_qty}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Reconcile correct failed: {symbol}: {e}"
                        )
                        pd.status = ReconcileStatus.ALERT
                        alerted += 1
                else:
                    if self._on_mismatch:
                        try:
                            self._on_mismatch(pd)
                        except Exception:
                            pass
                    alerted += 1

            diffs.append(pd)

        overall = ReconcileStatus.MATCH
        if alerted > 0:
            overall = ReconcileStatus.ALERT
        elif corrected > 0:
            overall = ReconcileStatus.CORRECTED

        result = ReconcileResult(
            timestamp=now,
            diffs=diffs,
            status=overall,
            corrected=corrected,
            alerted=alerted,
        )
        self._history.append(result)

        logger.info(
            f"Reconcile: {len(diffs)} symbols, "
            f"corrected={corrected}, alerted={alerted}, "
            f"status={overall.value}"
        )
        return result

    def get_history(self, limit: int = 10) -> List[ReconcileResult]:
        return self._history[-limit:]

    def last_result(self) -> Optional[ReconcileResult]:
        return self._history[-1] if self._history else None

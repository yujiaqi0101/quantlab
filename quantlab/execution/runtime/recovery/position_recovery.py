"""
Position Recovery — 持仓恢复

系统重启后恢复持仓状态：
  1. 从交易所获取真实持仓
  2. 对比本地 portfolio
  3. 自动修正
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

logger = logging.getLogger("quantlab.execution.runtime.recovery.position_recovery")


class PositionRecovery:
    """
    持仓恢复器

    用法：
        recovery = PositionRecovery()
        recovery.recover(
            get_exchange_positions=broker.get_positions,
            get_local_positions=lambda: portfolio.positions,
            corrector=lambda symbol, qty: portfolio.set_position(symbol, qty),
        )
    """

    def __init__(self, tolerance: float = 0.0001) -> None:
        self.tolerance = tolerance
        self._recovery_count: int = 0

    @property
    def recovery_count(self) -> int:
        return self._recovery_count

    def recover(
        self,
        get_exchange_positions: callable,
        get_local_positions: callable,
        corrector: Optional[callable] = None,
        auto_correct: bool = True,
    ) -> Dict:
        """
        恢复持仓

        返回恢复统计
        """
        stats = {
            "checked": 0,
            "mismatched": 0,
            "corrected": 0,
            "errors": 0,
        }

        try:
            exchange_positions = get_exchange_positions()
            local_positions = get_local_positions()

            all_symbols = set(exchange_positions.keys()) | set(
                local_positions.keys() if isinstance(local_positions, dict)
                else [p.symbol for p in local_positions.values()]
            )

            for symbol in all_symbols:
                stats["checked"] += 1

                ex_qty = exchange_positions.get(symbol, 0.0)
                if isinstance(local_positions, dict):
                    local_qty = local_positions.get(symbol, 0.0)
                else:
                    pos = local_positions.get(symbol)
                    local_qty = pos.qty if pos else 0.0

                diff = ex_qty - local_qty
                if abs(diff) > self.tolerance:
                    stats["mismatched"] += 1
                    logger.warning(
                        f"PositionRecovery: {symbol} mismatch "
                        f"local={local_qty} exchange={ex_qty} diff={diff}"
                    )

                    if auto_correct and corrector:
                        try:
                            corrector(symbol, ex_qty)
                            stats["corrected"] += 1
                            self._recovery_count += 1
                            logger.info(
                                f"PositionRecovery: corrected {symbol} "
                                f"→ {ex_qty}"
                            )
                        except Exception as e:
                            stats["errors"] += 1
                            logger.error(
                                f"PositionRecovery: correct failed {symbol}: {e}"
                            )

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"PositionRecovery: failed: {e}")

        logger.info(
            f"PositionRecovery: checked={stats['checked']}, "
            f"mismatched={stats['mismatched']}, "
            f"corrected={stats['corrected']}"
        )
        return stats

"""
State Restore — 状态恢复

系统重启后恢复所有状态：
  1. Portfolio 恢复
  2. OMS 订单恢复
  3. Fill Engine 恢复
  4. Capital Allocator 恢复
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.runtime.recovery.state_restore")


@dataclass
class SystemSnapshot:
    """系统完整快照"""
    timestamp: int
    version: str = "1.0"
    portfolio: Dict = field(default_factory=dict)
    orders: List[Dict] = field(default_factory=list)
    fills: List[Dict] = field(default_factory=list)
    allocations: Dict = field(default_factory=dict)
    strategy_states: Dict = field(default_factory=dict)
    metrics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "portfolio": self.portfolio,
            "orders": self.orders,
            "fills": self.fills,
            "allocations": self.allocations,
            "strategy_states": self.strategy_states,
            "metrics": self.metrics,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SystemSnapshot":
        return cls(
            timestamp=data.get("timestamp", 0),
            version=data.get("version", "1.0"),
            portfolio=data.get("portfolio", {}),
            orders=data.get("orders", []),
            fills=data.get("fills", []),
            allocations=data.get("allocations", {}),
            strategy_states=data.get("strategy_states", {}),
            metrics=data.get("metrics", {}),
        )


class StateRestorer:
    """
    状态恢复器

    用法：
        restorer = StateRestorer(persist_path="storage/system_state.json")
        snapshot = restorer.save(portfolio, oms, fill_engine, allocator)
        restored = restorer.load()
        restorer.restore_all(restored, portfolio, oms, fill_engine, allocator)
    """

    def __init__(self, persist_path: str = "storage/system_state.json") -> None:
        self._path = persist_path

    def save(
        self,
        portfolio=None,
        oms=None,
        fill_engine=None,
        allocator=None,
        strategy_states: Dict = None,
        metrics: Dict = None,
    ) -> SystemSnapshot:
        """保存系统完整状态"""
        snapshot = SystemSnapshot(
            timestamp=int(time.time() * 1000),
            portfolio=portfolio.to_dict() if portfolio else {},
            orders=oms.snapshot() if oms else [],
            fills=[f.to_dict() for f in fill_engine.get_all_fills()] if fill_engine else [],
            allocations=allocator.to_dict() if allocator else {},
            strategy_states=strategy_states or {},
            metrics=metrics or {},
        )

        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(
            f"StateRestorer: saved snapshot to {self._path} "
            f"({len(snapshot.orders)} orders, "
            f"{len(snapshot.fills)} fills)"
        )
        return snapshot

    def load(self) -> Optional[SystemSnapshot]:
        """加载系统状态"""
        if not os.path.exists(self._path):
            logger.info("StateRestorer: no snapshot found, fresh start")
            return None

        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            snapshot = SystemSnapshot.from_dict(data)
            logger.info(
                f"StateRestorer: loaded snapshot from {self._path} "
                f"(timestamp={snapshot.timestamp})"
            )
            return snapshot
        except Exception as e:
            logger.error(f"StateRestorer: load failed: {e}")
            return None

    def restore_all(
        self,
        snapshot: SystemSnapshot,
        portfolio=None,
        oms=None,
        fill_engine=None,
        allocator=None,
    ) -> None:
        """恢复所有组件状态"""
        logger.info("StateRestorer: restoring all components...")

        if portfolio and snapshot.portfolio:
            self._restore_portfolio(portfolio, snapshot.portfolio)

        if oms and snapshot.orders:
            self._restore_oms(oms, snapshot.orders)

        if fill_engine and snapshot.fills:
            self._restore_fills(fill_engine, snapshot.fills)

        logger.info("StateRestorer: restore complete")

    def _restore_portfolio(self, portfolio, data: Dict) -> None:
        """恢复 portfolio"""
        if hasattr(portfolio, "cash"):
            portfolio.cash = data.get("cash", 0.0)
        if hasattr(portfolio, "initial_capital"):
            portfolio.initial_capital = data.get("initial_capital", 0.0)
        if hasattr(portfolio, "_positions"):
            portfolio._positions.clear()
            for sym, pos_data in data.get("positions", {}).items():
                from ..capital.portfolio import Position
                pos = Position(symbol=sym)
                pos.qty = pos_data.get("qty", 0.0)
                pos.avg_price = pos_data.get("avg_price", 0.0)
                pos.market_price = pos_data.get("market_price", 0.0)
                pos.realized_pnl = pos_data.get("realized_pnl", 0.0)
                portfolio._positions[sym] = pos
        logger.info(f"StateRestorer: portfolio restored (cash={data.get('cash', 0)})")

    def _restore_oms(self, oms, orders: List[Dict]) -> None:
        """恢复 OMS"""
        from ...core.oms.order import OMSOrder, OrderSide, OrderType, OrderState
        restored = []
        for od in orders:
            try:
                order = OMSOrder(
                    symbol=od["symbol"],
                    side=OrderSide(od.get("side", "BUY")),
                    quantity=od.get("quantity", 0),
                    order_type=OrderType(od.get("order_type", "MARKET")),
                    price=od.get("price"),
                    id=od.get("id", ""),
                    client_order_id=od.get("client_order_id", ""),
                    broker_order_id=od.get("broker_order_id", ""),
                    signal_id=od.get("signal_id", ""),
                    strategy_id=od.get("strategy_id", ""),
                )
                order.state = OrderState(od.get("state", "NEW"))
                order.filled_qty = od.get("filled_qty", 0)
                order.avg_fill_price = od.get("avg_fill_price", 0.0)
                restored.append(order)
            except Exception as e:
                logger.error(f"StateRestorer: restore order failed: {e}")
        oms.restore(restored)
        logger.info(f"StateRestorer: OMS restored {len(restored)} orders")

    def _restore_fills(self, fill_engine, fills: List[Dict]) -> None:
        """恢复 Fill Engine"""
        from ...core.fills.fill_engine import Fill
        restored = []
        for fd in fills:
            try:
                fill = Fill(
                    id=fd.get("id", ""),
                    order_id=fd.get("order_id", ""),
                    symbol=fd.get("symbol", ""),
                    side=fd.get("side", ""),
                    fill_qty=fd.get("fill_qty", 0),
                    fill_price=fd.get("fill_price", 0.0),
                    commission=fd.get("commission", 0.0),
                    slippage=fd.get("slippage", 0.0),
                    timestamp=fd.get("timestamp", 0),
                    source=fd.get("source", ""),
                )
                restored.append(fill)
            except Exception as e:
                logger.error(f"StateRestorer: restore fill failed: {e}")
        fill_engine.restore(restored)
        logger.info(f"StateRestorer: FillEngine restored {len(restored)} fills")

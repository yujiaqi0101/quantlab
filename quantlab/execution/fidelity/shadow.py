"""
Execution Shadow Mode — 影子模式

实盘前最后一步：
  Live trading running
    ↓
  Paper engine also running
    ↓
  对比结果

比较：Paper fills vs Live fills
如果偏差 → 立即报警
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .reconciliation import FillReconciliationV2, ReconciliationReport

logger = logging.getLogger("quantlab.execution.fidelity.shadow")


@dataclass
class ShadowComparison:
    """影子模式对比结果"""
    timestamp: int
    order_id: str
    symbol: str
    paper_fill: Optional[Dict] = None
    live_fill: Optional[Dict] = None
    price_diff_bps: float = 0.0
    qty_diff: float = 0.0
    latency_diff_ms: float = 0.0
    severity: str = "OK"    # OK / WARNING / CRITICAL
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "paper_fill": self.paper_fill,
            "live_fill": self.live_fill,
            "price_diff_bps": self.price_diff_bps,
            "qty_diff": self.qty_diff,
            "latency_diff_ms": self.latency_diff_ms,
            "severity": self.severity,
            "notes": self.notes,
        }


class ShadowModeEngine:
    """
    影子模式引擎

    用法：
        shadow = ShadowModeEngine(
            price_tolerance_bps=10.0,
            qty_tolerance=0.001,
        )
        # 实盘成交
        shadow.record_live_fill(order_id="o1", symbol="BTCUSDT", qty=10, price=50001)
        # 纸面成交
        shadow.record_paper_fill(order_id="o1", symbol="BTCUSDT", qty=10, price=50000)
        # 对比
        comparison = shadow.compare(order_id="o1")
        if comparison.severity == "CRITICAL":
            shadow.trigger_alert(comparison)
    """

    def __init__(
        self,
        price_tolerance_bps: float = 10.0,
        qty_tolerance: float = 0.001,
        latency_tolerance_ms: float = 500.0,
        alert_callback: Optional[Callable] = None,
    ) -> None:
        self.price_tolerance_bps = price_tolerance_bps
        self.qty_tolerance = qty_tolerance
        self.latency_tolerance_ms = latency_tolerance_ms
        self.alert_callback = alert_callback

        self._paper_fills: Dict[str, Dict] = {}
        self._live_fills: Dict[str, Dict] = {}
        self._comparisons: List[ShadowComparison] = []
        self._alerts: List[Dict] = []
        self._reconciliation = FillReconciliationV2(
            qty_tolerance=qty_tolerance,
            price_tolerance_bps=price_tolerance_bps,
            auto_correct=False,
        )

    def record_paper_fill(
        self,
        order_id: str,
        symbol: str,
        qty: float,
        price: float,
        timestamp: int = 0,
    ) -> None:
        """记录纸面成交"""
        self._paper_fills[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "fill_qty": qty,
            "fill_price": price,
            "timestamp": timestamp or int(time.time() * 1000),
        }

    def record_live_fill(
        self,
        order_id: str,
        symbol: str,
        qty: float,
        price: float,
        timestamp: int = 0,
    ) -> None:
        """记录实盘成交"""
        self._live_fills[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "fill_qty": qty,
            "fill_price": price,
            "timestamp": timestamp or int(time.time() * 1000),
        }

    def compare(self, order_id: str) -> ShadowComparison:
        """对比单个订单"""
        paper = self._paper_fills.get(order_id)
        live = self._live_fills.get(order_id)

        comparison = ShadowComparison(
            timestamp=int(time.time() * 1000),
            order_id=order_id,
            symbol=(paper or live or {}).get("symbol", ""),
            paper_fill=paper,
            live_fill=live,
        )

        if not paper and not live:
            comparison.notes = "No fills recorded"
            comparison.severity = "OK"
        elif not paper:
            comparison.notes = "Paper fill missing"
            comparison.severity = "WARNING"
        elif not live:
            comparison.notes = "Live fill missing"
            comparison.severity = "WARNING"
        else:
            # 计算差异
            comparison.qty_diff = paper["fill_qty"] - live["fill_qty"]
            if paper["fill_price"] > 0:
                comparison.price_diff_bps = (
                    (paper["fill_price"] - live["fill_price"])
                    / paper["fill_price"] * 10000
                )
            comparison.latency_diff_ms = paper["timestamp"] - live["timestamp"]

            # 评估严重性
            severity = "OK"
            if abs(comparison.qty_diff) > self.qty_tolerance * max(paper["fill_qty"], 1):
                severity = "WARNING"
            if abs(comparison.price_diff_bps) > self.price_tolerance_bps:
                severity = "CRITICAL"
            if abs(comparison.latency_diff_ms) > self.latency_tolerance_ms:
                severity = "CRITICAL" if severity != "OK" else "WARNING"

            comparison.severity = severity

        self._comparisons.append(comparison)

        if comparison.severity == "CRITICAL":
            self.trigger_alert(comparison)

        return comparison

    def compare_all(self) -> List[ShadowComparison]:
        """对比所有订单"""
        all_orders = set(self._paper_fills.keys()) | set(self._live_fills.keys())
        return [self.compare(oid) for oid in all_orders]

    def trigger_alert(self, comparison: ShadowComparison) -> None:
        """触发告警"""
        alert = {
            "timestamp": comparison.timestamp,
            "order_id": comparison.order_id,
            "severity": comparison.severity,
            "message": (
                f"Shadow mode alert: {comparison.order_id} "
                f"price_diff={comparison.price_diff_bps:.1f}bps "
                f"qty_diff={comparison.qty_diff} "
                f"latency_diff={comparison.latency_diff_ms}ms"
            ),
        }
        self._alerts.append(alert)
        logger.warning(alert["message"])

        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def get_summary(self) -> Dict:
        """获取影子模式汇总"""
        total = len(self._comparisons)
        critical = sum(1 for c in self._comparisons if c.severity == "CRITICAL")
        warning = sum(1 for c in self._comparisons if c.severity == "WARNING")
        ok = sum(1 for c in self._comparisons if c.severity == "OK")

        return {
            "total_comparisons": total,
            "critical": critical,
            "warning": warning,
            "ok": ok,
            "alerts": len(self._alerts),
            "paper_fills": len(self._paper_fills),
            "live_fills": len(self._live_fills),
            "tolerances": {
                "price_bps": self.price_tolerance_bps,
                "qty": self.qty_tolerance,
                "latency_ms": self.latency_tolerance_ms,
            },
        }

    def get_comparisons(self, limit: int = 100) -> List[Dict]:
        return [c.to_dict() for c in self._comparisons[-limit:]]

    def get_alerts(self, limit: int = 50) -> List[Dict]:
        return self._alerts[-limit:]

    def reset(self) -> None:
        """重置"""
        self._paper_fills.clear()
        self._live_fills.clear()
        self._comparisons.clear()
        self._alerts.clear()

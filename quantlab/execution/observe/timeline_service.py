"""
Timeline Service — 时间线服务

从 EventStore 读取事件，生成前端可视化用的时间线。

例如：
    09:00:00  MarketEvent   BTCUSDT price=50000
    09:00:01  SignalEvent   BUY strength=0.81
    09:00:01  OrderEvent    BUY 0.5 @ 50000
    09:00:03  FillEvent     filled 0.5 @ 50001
    09:00:03  PositionUpdate BTCUSDT qty=0.5
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .event_store import EventStore, StoredEvent, get_event_store

logger = logging.getLogger("quantlab.execution.observe.timeline_service")


@dataclass
class TimelineItem:
    """时间线条目"""
    event_id: str
    timestamp: int
    timestamp_str: str
    event_type: str
    source: str
    trace_id: str
    session_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    # 渲染辅助
    category: str = ""
    label: str = ""
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "timestamp_str": self.timestamp_str,
            "event_type": self.event_type,
            "source": self.source,
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "payload": self.payload,
            "category": self.category,
            "label": self.label,
            "summary": self.summary,
        }


class TimelineService:
    """
    时间线服务

    用法：
        svc = TimelineService()
        items = svc.get_timeline(session_id="s1", limit=100)
        item = svc.get_event_detail(event_id="abc")
    """

    # 事件类型 → 类别映射
    TYPE_CATEGORY = {
        "MARKET_TICK": "market",
        "MARKET_BAR": "market",
        "MARKET": "market",
        "SIGNAL": "signal",
        "ORDER_NEW": "order",
        "ORDER_UPDATE": "order",
        "ORDER": "order",
        "FILL": "fill",
        "POSITION_UPDATE": "position",
        "POSITION": "position",
        "RISK_ALERT": "risk",
        "RISK": "risk",
        "KILL_SWITCH": "risk",
        "SYSTEM": "system",
    }

    def __init__(self, store: Optional[EventStore] = None) -> None:
        self.store = store or get_event_store()

    def get_timeline(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        trace_id: Optional[str] = None,
        start_ts: Optional[int] = None,
        end_ts: Optional[int] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[TimelineItem]:
        """获取时间线"""
        events = self.store.query(
            session_id=session_id,
            event_type=event_type,
            trace_id=trace_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=limit,
            offset=offset,
            order="asc",
        )
        return [self._to_item(e) for e in events]

    def get_event_detail(self, event_id: str) -> Optional[TimelineItem]:
        """获取事件详情"""
        event = self.store.get_event(event_id)
        return self._to_item(event) if event else None

    def get_trace_timeline(self, trace_id: str) -> List[TimelineItem]:
        """获取同一 trace 的事件链"""
        events = self.store.get_trace(trace_id)
        return [self._to_item(e) for e in events]

    def get_categories(self, session_id: Optional[str] = None) -> Dict[str, int]:
        """获取各类别事件数"""
        events = self.store.query(session_id=session_id, limit=100000)
        counts: Dict[str, int] = {}
        for e in events:
            cat = self.TYPE_CATEGORY.get(e.event_type, "other")
            counts[cat] = counts.get(cat, 0) + 1
        return counts

    def _to_item(self, event: StoredEvent) -> TimelineItem:
        cat = self.TYPE_CATEGORY.get(event.event_type, "other")
        label = event.event_type
        summary = self._build_summary(event)
        return TimelineItem(
            event_id=event.event_id,
            timestamp=event.timestamp,
            timestamp_str=datetime.fromtimestamp(event.timestamp / 1000).isoformat(),
            event_type=event.event_type,
            source=event.source,
            trace_id=event.trace_id,
            session_id=event.session_id,
            payload=event.payload,
            category=cat,
            label=label,
            summary=summary,
        )

    def _build_summary(self, event: StoredEvent) -> str:
        """生成人类可读摘要"""
        p = event.payload
        t = event.event_type
        if t in ("MARKET_TICK", "MARKET_BAR", "MARKET"):
            sym = p.get("symbol", "")
            price = p.get("price", "")
            return f"{sym} @ {price}"
        if t == "SIGNAL":
            sym = p.get("symbol", "")
            side = p.get("side", p.get("signal", ""))
            score = p.get("score", p.get("strength", ""))
            return f"{side} {sym} score={score}"
        if t in ("ORDER_NEW", "ORDER_UPDATE", "ORDER"):
            sym = p.get("symbol", "")
            side = p.get("side", "")
            qty = p.get("qty", p.get("quantity", ""))
            price = p.get("price", "")
            return f"{side} {qty} {sym} @ {price}"
        if t == "FILL":
            sym = p.get("symbol", "")
            qty = p.get("qty", p.get("filled_qty", ""))
            price = p.get("price", p.get("filled_price", ""))
            return f"filled {qty} {sym} @ {price}"
        if t in ("POSITION_UPDATE", "POSITION"):
            sym = p.get("symbol", "")
            qty = p.get("qty", p.get("quantity", ""))
            return f"{sym} qty={qty}"
        if t in ("RISK_ALERT", "RISK"):
            return p.get("message", p.get("reason", t))
        if t == "KILL_SWITCH":
            return p.get("reason", "kill switch triggered")
        # 默认：返回 message 或 type
        return p.get("message", t)

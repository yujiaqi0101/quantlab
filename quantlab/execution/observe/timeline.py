"""
Event Timeline View — 事件时间线视图

基于 EventTracer 的 Span 数据，聚合为前端可视化用的时间线。

例如：
  09:30 MarketEvent    BTCUSDT price=50000
  09:30 SignalEvent    BUY strength=0.8
  09:30 OrderEvent     BUY 0.5 BTCUSDT
  09:30 FillEvent      filled 0.5 @ 50001
  09:31 PositionUpdate BTCUSDT qty=0.5
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.observe.timeline")


@dataclass
class TimelineEntry:
    """时间线条目"""
    timestamp: float
    timestamp_str: str
    trace_id: str
    label: str
    category: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "timestamp_str": self.timestamp_str,
            "trace_id": self.trace_id,
            "label": self.label,
            "category": self.category,
            "payload": self.payload,
            "duration_ms": self.duration_ms,
        }


@dataclass
class TraceSummary:
    """单个 trace 的摘要"""
    trace_id: str
    start_time: str
    end_time: str
    duration_ms: float
    n_spans: int
    labels: List[str] = field(default_factory=list)
    status: str = ""
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "n_spans": self.n_spans,
            "labels": self.labels,
            "status": self.status,
            "summary": self.summary,
        }


class TimelineView:
    """事件时间线视图"""

    LABEL_CATEGORY = {
        "MARKET": "market",
        "SIGNAL": "signal",
        "ORDER": "order",
        "FILL": "fill",
        "RISK": "risk",
        "POSITION": "position",
        "PORTFOLIO": "portfolio",
        "STRATEGY": "strategy",
        "ERROR": "error",
    }

    def __init__(self, tracer: Optional[Any] = None) -> None:
        self.tracer = tracer

    def set_tracer(self, tracer: Any) -> None:
        self.tracer = tracer

    def get_timeline(
        self,
        limit: int = 100,
        category: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[TimelineEntry]:
        if self.tracer is None:
            return []

        spans = self._collect_spans(trace_id=trace_id)

        entries: List[TimelineEntry] = []
        for sp in spans:
            cat = self.LABEL_CATEGORY.get(sp.label.upper(), sp.label.lower())
            if category and cat != category:
                continue

            entries.append(TimelineEntry(
                timestamp=sp.timestamp,
                timestamp_str=datetime.fromtimestamp(sp.timestamp).isoformat(),
                trace_id=sp.trace_id,
                label=sp.label,
                category=cat,
                payload=sp.payload,
                duration_ms=sp.duration_ms,
            ))

        entries.sort(key=lambda e: e.timestamp)

        if limit > 0:
            entries = entries[-limit:]

        return entries

    def _collect_spans(self, trace_id: Optional[str] = None) -> List[Any]:
        if self.tracer is None:
            return []

        spans: List[Any] = []

        if trace_id:
            trace_spans = self.tracer.get_trace(trace_id)
            if trace_spans:
                spans.extend(trace_spans)
        else:
            traces = getattr(self.tracer, "_traces", {})
            for tid, trace_spans in traces.items():
                spans.extend(trace_spans)

        return spans

    def get_by_trace(self, trace_id: str) -> Optional[TraceSummary]:
        if self.tracer is None:
            return None

        spans = self.tracer.get_trace(trace_id)
        if not spans:
            return None

        return self._build_summary(trace_id, spans)

    def list_traces(self, limit: int = 50) -> List[TraceSummary]:
        if self.tracer is None:
            return []

        traces = getattr(self.tracer, "_traces", {})
        summaries: List[TraceSummary] = []

        for tid, spans in traces.items():
            summaries.append(self._build_summary(tid, spans))

        summaries.sort(key=lambda s: s.start_time, reverse=True)

        return summaries[:limit]

    def _build_summary(self, trace_id: str, spans: List[Any]) -> TraceSummary:
        if not spans:
            return TraceSummary(
                trace_id=trace_id,
                start_time="",
                end_time="",
                duration_ms=0.0,
                n_spans=0,
            )

        timestamps = [s.timestamp for s in spans]
        start_ts = min(timestamps)
        end_ts = max(timestamps)
        duration_ms = (end_ts - start_ts) * 1000

        labels = [s.label for s in spans]

        has_fill = any(s.label.upper() == "FILL" for s in spans)
        has_order = any(s.label.upper() == "ORDER" for s in spans)
        has_signal = any(s.label.upper() == "SIGNAL" for s in spans)

        if has_fill:
            status = "complete"
        elif has_order:
            status = "partial"
        elif has_signal:
            status = "signal_only"
        else:
            status = "open"

        summary_parts: List[str] = []
        for s in spans:
            if s.label.upper() == "SIGNAL":
                side = s.payload.get("side", "")
                sym = s.payload.get("symbol", "")
                summary_parts.append(f"Signal {side} {sym}")
            elif s.label.upper() == "ORDER":
                sym = s.payload.get("symbol", "")
                qty = s.payload.get("quantity", s.payload.get("qty", ""))
                summary_parts.append(f"Order {sym} {qty}")
            elif s.label.upper() == "FILL":
                sym = s.payload.get("symbol", "")
                price = s.payload.get("price", "")
                summary_parts.append(f"Fill {sym} @ {price}")

        return TraceSummary(
            trace_id=trace_id,
            start_time=datetime.fromtimestamp(start_ts).isoformat(),
            end_time=datetime.fromtimestamp(end_ts).isoformat(),
            duration_ms=duration_ms,
            n_spans=len(spans),
            labels=labels,
            status=status,
            summary=" | ".join(summary_parts) if summary_parts else "",
        )

    def stats(self) -> Dict[str, Any]:
        if self.tracer is None:
            return {"n_traces": 0, "n_spans": 0}

        traces = getattr(self.tracer, "_traces", {})
        n_spans = sum(len(v) for v in traces.values())

        from collections import Counter
        label_counts: Counter = Counter()
        for spans in traces.values():
            for s in spans:
                label_counts[s.label] += 1

        return {
            "n_traces": len(traces),
            "n_spans": n_spans,
            "by_label": dict(label_counts),
        }

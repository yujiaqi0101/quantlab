"""
Event Timeline View — 事件时间线视图

基于 EventTracer 的 Span 数据，聚合为前端可视化用的时间线。

例如：
  09:30 MarketEvent    BTCUSDT price=50000
  09:30 SignalEvent    BUY strength=0.8
  09:30 OrderEvent     BUY 0.5 BTCUSDT
  09:30 FillEvent      filled 0.5 @ 50001
  09:31 PositionUpdate BTCUSDT qty=0.5

用法：
    from quantlab.observe.timeline import TimelineView
    from quantlab.monitoring import EventTracer

    tracer = EventTracer(log_to_file=False)
    # ... tracer.begin / span / end ...

    view = TimelineView(tracer)
    timeline = view.get_timeline(limit=100)
    by_trace = view.get_by_trace("trace_001")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.observe.timeline")


# ------------------------------------------------------------------
# TimelineEntry
# ------------------------------------------------------------------

@dataclass
class TimelineEntry:
    """时间线条目"""
    timestamp: float                    # epoch seconds
    timestamp_str: str                  # 可读时间
    trace_id: str
    label: str                          # MARKET / SIGNAL / ORDER / FILL / ...
    category: str = ""                  # market / signal / order / fill / risk / position
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


# ------------------------------------------------------------------
# TraceSummary
# ------------------------------------------------------------------

@dataclass
class TraceSummary:
    """单个 trace 的摘要"""
    trace_id: str
    start_time: str
    end_time: str
    duration_ms: float
    n_spans: int
    labels: List[str] = field(default_factory=list)
    status: str = ""                    # complete / partial / open
    summary: str = ""                   # 人类可读摘要

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


# ------------------------------------------------------------------
# TimelineView
# ------------------------------------------------------------------

class TimelineView:
    """
    事件时间线视图

    从 EventTracer 读取 Span，聚合为时间线。
    """

    # label → category 映射
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
        """
        参数：
          tracer  EventTracer 实例（可选，可后续 set）
        """
        self.tracer = tracer

    def set_tracer(self, tracer: Any) -> None:
        self.tracer = tracer

    # ------------------------------------------------------------------
    # 时间线
    # ------------------------------------------------------------------

    def get_timeline(
        self,
        limit: int = 100,
        category: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[TimelineEntry]:
        """
        获取时间线

        参数：
          limit     最多返回条数
          category  按分类过滤（market/signal/order/fill/...）
          trace_id  按 trace_id 过滤
        """
        if self.tracer is None:
            return []

        spans = self._collect_spans(trace_id=trace_id)

        # 转 TimelineEntry
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

        # 按时间排序
        entries.sort(key=lambda e: e.timestamp)

        # 限制条数（取最近 N 条）
        if limit > 0:
            entries = entries[-limit:]

        return entries

    def _collect_spans(self, trace_id: Optional[str] = None) -> List[Any]:
        """从 tracer 收集所有 Span"""
        if self.tracer is None:
            return []

        spans: List[Any] = []

        if trace_id:
            # 单个 trace
            trace_spans = self.tracer.get_trace(trace_id)
            if trace_spans:
                spans.extend(trace_spans)
        else:
            # 所有 trace
            # EventTracer 内部用 _traces: Dict[trace_id, List[Span]]
            traces = getattr(self.tracer, "_traces", {})
            for tid, trace_spans in traces.items():
                spans.extend(trace_spans)

        return spans

    # ------------------------------------------------------------------
    # 按 trace 分组
    # ------------------------------------------------------------------

    def get_by_trace(self, trace_id: str) -> Optional[TraceSummary]:
        """获取单个 trace 的摘要"""
        if self.tracer is None:
            return None

        spans = self.tracer.get_trace(trace_id)
        if not spans:
            return None

        return self._build_summary(trace_id, spans)

    def list_traces(self, limit: int = 50) -> List[TraceSummary]:
        """列出所有 trace 摘要"""
        if self.tracer is None:
            return []

        traces = getattr(self.tracer, "_traces", {})
        summaries: List[TraceSummary] = []

        for tid, spans in traces.items():
            summaries.append(self._build_summary(tid, spans))

        # 按开始时间倒序
        summaries.sort(key=lambda s: s.start_time, reverse=True)

        return summaries[:limit]

    def _build_summary(self, trace_id: str, spans: List[Any]) -> TraceSummary:
        """构建 trace 摘要"""
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

        # 状态判断
        has_fill = any(s.label.upper() == "FILL" for s in spans)
        has_order = any(s.label.upper() == "ORDER" for s in spans)
        has_signal = any(s.label.upper() == "SIGNAL" for s in spans)

        if has_fill:
            status = "complete"
        elif has_order:
            status = "partial"   # 下了单没成交
        elif has_signal:
            status = "signal_only"
        else:
            status = "open"

        # 人类可读摘要
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

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        if self.tracer is None:
            return {"n_traces": 0, "n_spans": 0}

        traces = getattr(self.tracer, "_traces", {})
        n_spans = sum(len(v) for v in traces.values())

        # 按 label 统计
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

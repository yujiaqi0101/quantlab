"""
EventTracer：事件链路追踪（V3.2）

V3.2 关键能力：
    1) 同一笔交易（同一 trace_id）从 MarketEvent → SignalEvent → OrderEvent → FillEvent 全程绑定
    2) 一笔亏损可以反查：是不是 signal 错了？是不是 broker 滑点太大？
    3) 内存缓冲 + JSON Lines 持久化

trace_id 生命周期：
    - 起点：通常是某根 bar 或某个 signal 决策
    - 终点：该决策引发的最后一笔 Fill（或超时无 fill）
    - 一棵 trace 可能包含多个 child (一笔 trade 内多次调仓？)

API:
    trace = tracer.begin(trace_id, label="BUY_AAPL")
    tracer.span(trace_id, "SIGNAL", payload={...})
    tracer.span(trace_id, "ORDER", payload={...})
    tracer.span(trace_id, "FILL", payload={...})
    tracer.end(trace_id, "FILL")
    tracer.get_trace(trace_id)  # 返回整条链路
    tracer.recent(n=10)         # 最近 n 条
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Span:
    """单个事件"""
    trace_id: str
    label: str              # "MARKET" / "SIGNAL" / "ORDER" / "FILL" / ...
    timestamp: float        # epoch seconds
    payload: Dict = field(default_factory=dict)
    parent_span_id: str = ""
    span_id: str = ""
    duration_ms: float = 0.0


class EventTracer:
    """
    V3.2 事件链路追踪

    用法：
        tracer = EventTracer(log_to_file=True)
        tid = tracer.begin(label="AAPL_BUY")
        tracer.span(tid, "SIGNAL", score=0.85)
        tracer.span(tid, "ORDER", qty=100)
        tracer.span(tid, "FILL", price=150.0, qty=100)
        tracer.end(tid)
        for span in tracer.get_trace(tid):
            print(span)
    """

    def __init__(
        self,
        log_dir: str = "logs",
        log_to_file: bool = True,
    ):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._traces: Dict[str, List[Span]] = {}
        self._open: Dict[str, float] = {}    # trace_id -> start ts
        self._log_path = os.path.join(
            log_dir, "traces.jsonl"
        )
        self._log_to_file = log_to_file

    def begin(
        self,
        trace_id: Optional[str] = None,
        label: str = "ROOT",
        parent_span_id: str = "",
    ) -> str:
        tid = trace_id or uuid.uuid4().hex[:8]
        ts = time.time()
        self._open[tid] = ts
        self._traces.setdefault(tid, [])
        self._traces[tid].append(Span(
            trace_id=tid,
            label=label,
            timestamp=ts,
            parent_span_id=parent_span_id,
            span_id=uuid.uuid4().hex[:8],
        ))
        return tid

    def span(
        self,
        trace_id: str,
        label: str,
        parent_span_id: str = "",
        **payload: Any,
    ) -> Span:
        if trace_id not in self._traces:
            # 没 begin 过 → 自动开
            self.begin(trace_id=trace_id, label=label)
        ts = time.time()
        start = self._open.get(trace_id, ts)
        sp = Span(
            trace_id=trace_id,
            label=label,
            timestamp=ts,
            parent_span_id=parent_span_id,
            span_id=uuid.uuid4().hex[:8],
            duration_ms=(ts - start) * 1000.0,
            payload=dict(payload),
        )
        self._traces[trace_id].append(sp)
        if self._log_to_file:
            self._append_to_file(sp)
        return sp

    def end(
        self,
        trace_id: str,
        label: str = "END",
        **payload: Any,
    ) -> None:
        ts = time.time()
        start = self._open.pop(trace_id, ts)
        if trace_id in self._traces:
            self._traces[trace_id].append(Span(
                trace_id=trace_id,
                label=label,
                timestamp=ts,
                payload=dict(payload),
                duration_ms=(ts - start) * 1000.0,
            ))
        if self._log_to_file:
            self._append_to_file(Span(
                trace_id=trace_id,
                label=label,
                timestamp=ts,
                payload=dict(payload),
                duration_ms=(ts - start) * 1000.0,
            ))

    def get_trace(self, trace_id: str) -> List[Span]:
        return list(self._traces.get(trace_id, []))

    def recent(self, n: int = 10) -> List[Span]:
        out: List[Span] = []
        for spans in self._traces.values():
            out.extend(spans)
        out.sort(key=lambda s: s.timestamp, reverse=True)
        return out[:n]

    def _append_to_file(self, span: Span) -> None:
        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(
                    asdict(span), default=str
                ) + "\n")
        except Exception:
            pass

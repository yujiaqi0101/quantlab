"""
Root Cause Analysis — 根因分析

Replay 的真正价值：定位交易链路。

例如用户点击亏损交易，自动定位：
    SignalEvent → OrderEvent → FillEvent → RiskEvent

直接看到：为什么亏。

用法：
    rca = RootCauseAnalysis(store)
    chain = rca.analyze_trace(trace_id="abc123")
    chain = rca.analyze_fill(event_id="fill_xxx")
    chain = rca.analyze_position(session_id="s1", symbol="BTCUSDT")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .event_store import EventStore, StoredEvent, get_event_store

logger = logging.getLogger("quantlab.execution.observe.rca")


@dataclass
class TradeChain:
    """交易链路"""
    trace_id: str = ""
    symbol: str = ""
    session_id: str = ""
    # 链路节点
    nodes: List[StoredEvent] = field(default_factory=list)
    # 摘要
    summary: str = ""
    # 总盈亏
    pnl: Optional[float] = None
    # 耗时（毫秒）
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "session_id": self.session_id,
            "nodes": [n.to_dict() for n in self.nodes],
            "summary": self.summary,
            "pnl": self.pnl,
            "duration_ms": self.duration_ms,
        }


class RootCauseAnalysis:
    """
    根因分析

    用法：
        rca = RootCauseAnalysis()
        chain = rca.analyze_trace("trace_id")
        chain = rca.analyze_fill("fill_event_id")
        chains = rca.find_traces_for_session("session_id")
    """

    # 链路相关事件类型
    CHAIN_TYPES = {
        "SIGNAL",
        "ORDER_NEW", "ORDER_UPDATE", "ORDER",
        "FILL",
        "POSITION_UPDATE", "POSITION",
        "RISK_ALERT", "RISK", "KILL_SWITCH",
    }

    def __init__(self, store: Optional[EventStore] = None) -> None:
        self.store = store or get_event_store()

    def analyze_trace(self, trace_id: str) -> TradeChain:
        """分析同一 trace 的事件链"""
        events = self.store.get_trace(trace_id)
        return self._build_chain(events, trace_id=trace_id)

    def analyze_event(self, event_id: str) -> TradeChain:
        """从单个事件出发分析链路"""
        event = self.store.get_event(event_id)
        if not event:
            return TradeChain()
        if event.trace_id:
            return self.analyze_trace(event.trace_id)
        # 无 trace_id，返回单事件
        return self._build_chain([event], trace_id="")

    def analyze_fill(self, event_id: str) -> TradeChain:
        """分析成交事件链路"""
        return self.analyze_event(event_id)

    def find_traces_for_session(
        self,
        session_id: str,
        symbol: Optional[str] = None,
    ) -> List[TradeChain]:
        """查找会话中所有交易链路"""
        events = self.store.query(session_id=session_id, limit=100000)
        # 按 trace_id 分组
        traces: Dict[str, List[StoredEvent]] = {}
        for e in events:
            if e.event_type not in self.CHAIN_TYPES:
                continue
            tid = e.trace_id or e.event_id
            traces.setdefault(tid, []).append(e)

        chains = []
        for tid, evs in traces.items():
            chain = self._build_chain(evs, trace_id=tid)
            if symbol and chain.symbol != symbol:
                continue
            chains.append(chain)
        return chains

    def find_loss_trades(
        self,
        session_id: str,
        top_n: int = 10,
    ) -> List[TradeChain]:
        """查找亏损交易链路"""
        chains = self.find_traces_for_session(session_id)
        losses = [c for c in chains if c.pnl is not None and c.pnl < 0]
        losses.sort(key=lambda c: c.pnl or 0)
        return losses[:top_n]

    def find_anomalies(self, session_id: str) -> Dict[str, Any]:
        """查找异常"""
        events = self.store.query(session_id=session_id, limit=100000)
        anomalies: List[Dict[str, Any]] = []
        fills_no_signal = 0
        orders_no_fill = 0
        risk_events: List[StoredEvent] = []

        # 按 trace 分组
        traces: Dict[str, List[StoredEvent]] = {}
        for e in events:
            tid = e.trace_id or e.event_id
            traces.setdefault(tid, []).append(e)

        for tid, evs in traces.items():
            types = {e.event_type for e in evs}
            has_signal = "SIGNAL" in types
            has_order = types & {"ORDER_NEW", "ORDER_UPDATE", "ORDER"}
            has_fill = "FILL" in types
            has_risk = types & {"RISK_ALERT", "RISK", "KILL_SWITCH"}

            if has_fill and not has_signal:
                fills_no_signal += 1
                anomalies.append({
                    "type": "fill_without_signal",
                    "trace_id": tid,
                    "message": "成交无对应信号",
                })
            if has_order and not has_fill:
                orders_no_fill += 1
                anomalies.append({
                    "type": "order_without_fill",
                    "trace_id": tid,
                    "message": "订单未成交",
                })
            if has_risk:
                for e in evs:
                    if e.event_type in ("RISK_ALERT", "RISK", "KILL_SWITCH"):
                        risk_events.append(e)
                        anomalies.append({
                            "type": "risk_event",
                            "trace_id": tid,
                            "event_id": e.event_id,
                            "message": e.payload.get("message", e.payload.get("reason", e.event_type)),
                        })

        return {
            "n_traces": len(traces),
            "n_anomalies": len(anomalies),
            "fills_without_signal": fills_no_signal,
            "orders_without_fill": orders_no_fill,
            "n_risk_events": len(risk_events),
            "anomalies": anomalies[:100],
        }

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _build_chain(
        self,
        events: List[StoredEvent],
        trace_id: str = "",
    ) -> TradeChain:
        """构建交易链路"""
        # 按时间排序
        events = sorted(events, key=lambda e: e.timestamp)

        # 过滤链路相关事件
        nodes = [e for e in events if e.event_type in self.CHAIN_TYPES]

        # 提取 symbol
        symbol = ""
        for e in nodes:
            sym = e.payload.get("symbol", "")
            if sym:
                symbol = sym
                break

        # 提取 session_id
        session_id = nodes[0].session_id if nodes else ""

        # 计算盈亏
        pnl: Optional[float] = None
        for e in nodes:
            if e.event_type == "FILL":
                p = e.payload
                if "pnl" in p:
                    pnl = (pnl or 0) + float(p["pnl"])
            if e.event_type in ("POSITION_UPDATE", "POSITION"):
                p = e.payload
                if "realized_pnl" in p and p["realized_pnl"] is not None:
                    pnl = float(p["realized_pnl"])

        # 计算耗时
        duration_ms = 0
        if len(nodes) >= 2:
            duration_ms = nodes[-1].timestamp - nodes[0].timestamp

        # 生成摘要
        summary = self._build_summary(nodes, symbol, pnl)

        return TradeChain(
            trace_id=trace_id,
            symbol=symbol,
            session_id=session_id,
            nodes=nodes,
            summary=summary,
            pnl=pnl,
            duration_ms=duration_ms,
        )

    def _build_summary(
        self,
        nodes: List[StoredEvent],
        symbol: str,
        pnl: Optional[float],
    ) -> str:
        """生成链路摘要"""
        if not nodes:
            return "空链路"

        parts = []
        if symbol:
            parts.append(symbol)

        types = [n.event_type for n in nodes]
        # 简化展示
        flow = []
        if "SIGNAL" in types:
            # 提取信号方向
            for n in nodes:
                if n.event_type == "SIGNAL":
                    side = n.payload.get("side", n.payload.get("signal", ""))
                    flow.append(f"Signal({side})")
                    break
        if any(t in types for t in ("ORDER_NEW", "ORDER_UPDATE", "ORDER")):
            flow.append("Order")
        if "FILL" in types:
            flow.append("Fill")
        if any(t in types for t in ("POSITION_UPDATE", "POSITION")):
            flow.append("Position")
        if any(t in types for t in ("RISK_ALERT", "RISK", "KILL_SWITCH")):
            flow.append("Risk")

        parts.append(" → ".join(flow))

        if pnl is not None:
            parts.append(f"PnL={pnl:+.2f}")

        return " | ".join(parts)

"""
Trade Trace — 交易链路核心对象

把一次交易的完整链路串起来：
    SignalEvent → OrderEvent → FillEvent → PositionUpdate → (Exit) → FillEvent

TradeTrace 是 V3 RCA 的基础数据结构，比 V2 的 TradeChain 更丰富：
  - 区分入场/出场
  - 计算滑点、持仓时间、市场变动
  - 关联所有相关事件
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..event_store import StoredEvent

logger = logging.getLogger("quantlab.execution.observe.analysis.trace")


@dataclass
class TradeLeg:
    """交易一条腿（入场或出场）"""
    side: str = ""           # BUY / SELL
    price: float = 0.0       # 成交价
    qty: float = 0.0         # 成交数量
    timestamp: int = 0
    order_id: str = ""
    # 信号信息
    signal_score: Optional[float] = None
    signal_strategy: str = ""
    # 订单信息
    order_price: Optional[float] = None  # 订单报价（计算滑点用）
    # 事件引用
    signal_event: Optional[StoredEvent] = None
    order_event: Optional[StoredEvent] = None
    fill_event: Optional[StoredEvent] = None

    @property
    def slippage(self) -> float:
        """滑点（百分比，正数表示不利方向）"""
        if self.order_price and self.price and self.order_price > 0:
            if self.side.upper() == "BUY":
                return (self.price - self.order_price) / self.order_price
            else:
                return (self.order_price - self.price) / self.order_price
        return 0.0

    @property
    def slippage_bps(self) -> float:
        """滑点（基点）"""
        return self.slippage * 10000

    def to_dict(self) -> Dict[str, Any]:
        return {
            "side": self.side,
            "price": self.price,
            "qty": self.qty,
            "timestamp": self.timestamp,
            "order_id": self.order_id,
            "signal_score": self.signal_score,
            "signal_strategy": self.signal_strategy,
            "order_price": self.order_price,
            "slippage": self.slippage,
            "slippage_bps": self.slippage_bps,
            "signal_event": self.signal_event.to_dict() if self.signal_event else None,
            "order_event": self.order_event.to_dict() if self.order_event else None,
            "fill_event": self.fill_event.to_dict() if self.fill_event else None,
        }


@dataclass
class TradeTrace:
    """
    交易链路 — 一次完整的交易

    入场 → 持仓 → 出场

    包含：
      - entry: 入场腿
      - exit: 出场腿（可选，未平仓时为 None）
      - pnl: 盈亏
      - pnl_pct: 盈亏百分比
      - holding_ms: 持仓时间（毫秒）
      - market_change: 持仓期间市场变动
      - events: 所有相关事件
      - risk_events: 风险事件
    """
    trace_id: str = ""
    symbol: str = ""
    session_id: str = ""
    strategy: str = ""

    # 入场/出场
    entry: Optional[TradeLeg] = None
    exit: Optional[TradeLeg] = None

    # 盈亏
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    fee: float = 0.0

    # 持仓时间（毫秒）
    holding_ms: int = 0

    # 持仓期间市场变动
    entry_price: float = 0.0
    exit_price: float = 0.0
    max_price: float = 0.0
    min_price: float = 0.0
    market_change: float = 0.0  # (exit_price - entry_price) / entry_price

    # 所有事件
    events: List[StoredEvent] = field(default_factory=list)
    risk_events: List[StoredEvent] = field(default_factory=list)

    # 是否已平仓
    is_closed: bool = False

    # 是否盈利
    @property
    def is_win(self) -> bool:
        return (self.pnl or 0) > 0

    @property
    def is_loss(self) -> bool:
        return (self.pnl or 0) < 0

    @property
    def holding_seconds(self) -> float:
        return self.holding_ms / 1000.0

    @property
    def holding_minutes(self) -> float:
        return self.holding_ms / 60000.0

    @property
    def holding_hours(self) -> float:
        return self.holding_ms / 3600000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "session_id": self.session_id,
            "strategy": self.strategy,
            "entry": self.entry.to_dict() if self.entry else None,
            "exit": self.exit.to_dict() if self.exit else None,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "fee": self.fee,
            "holding_ms": self.holding_ms,
            "holding_seconds": self.holding_seconds,
            "holding_minutes": self.holding_minutes,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "max_price": self.max_price,
            "min_price": self.min_price,
            "market_change": self.market_change,
            "is_closed": self.is_closed,
            "is_win": self.is_win,
            "is_loss": self.is_loss,
            "n_events": len(self.events),
            "n_risk_events": len(self.risk_events),
            "events": [e.to_dict() for e in self.events],
            "risk_events": [e.to_dict() for e in self.risk_events],
        }


class TraceBuilder:
    """
    交易链路构建器

    从 EventStore 的事件构建 TradeTrace。

    用法：
        builder = TraceBuilder()
        trace = builder.build_from_trace_id("trace_xxx")
        traces = builder.build_session_traces("session_id")
    """

    def __init__(self, store) -> None:
        self.store = store

    def build_from_trace_id(self, trace_id: str) -> TradeTrace:
        """从 trace_id 构建交易链路"""
        events = self.store.get_trace(trace_id)
        return self._build(trace_id, events)

    def build_from_event(self, event_id: str) -> TradeTrace:
        """从单个事件出发构建链路"""
        event = self.store.get_event(event_id)
        if not event:
            return TradeTrace()
        if event.trace_id:
            return self.build_from_trace_id(event.trace_id)
        return self._build(event.event_id, [event])

    def build_session_traces(
        self,
        session_id: str,
        symbol: Optional[str] = None,
    ) -> List[TradeTrace]:
        """构建会话所有交易链路"""
        events = self.store.query(session_id=session_id, limit=100000)
        # 按 trace_id 分组
        traces: Dict[str, List[StoredEvent]] = {}
        for e in events:
            tid = e.trace_id or e.event_id
            traces.setdefault(tid, []).append(e)

        result = []
        for tid, evs in traces.items():
            trace = self._build(tid, evs)
            if symbol and trace.symbol != symbol:
                continue
            result.append(trace)
        return result

    def build_loss_traces(
        self,
        session_id: str,
        top_n: int = 10,
    ) -> List[TradeTrace]:
        """构建亏损交易链路"""
        traces = self.build_session_traces(session_id)
        losses = [t for t in traces if t.is_loss and t.is_closed]
        losses.sort(key=lambda t: t.pnl or 0)
        return losses[:top_n]

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _build(self, trace_id: str, events: List[StoredEvent]) -> TradeTrace:
        """构建 TradeTrace"""
        events = sorted(events, key=lambda e: e.timestamp)

        trace = TradeTrace(trace_id=trace_id)
        trace.events = events

        # 提取 symbol / session_id / strategy
        for e in events:
            if not trace.symbol:
                trace.symbol = e.payload.get("symbol", "")
            if not trace.session_id:
                trace.session_id = e.session_id
            if not trace.strategy:
                trace.strategy = e.payload.get("strategy", e.source or "")
            if trace.symbol:
                break

        # 分类事件
        signals = [e for e in events if e.event_type.upper() == "SIGNAL"]
        orders = [e for e in events if e.event_type.upper() in ("ORDER_NEW", "ORDER_UPDATE", "ORDER")]
        fills = [e for e in events if e.event_type.upper() == "FILL"]
        positions = [e for e in events if e.event_type.upper() in ("POSITION_UPDATE", "POSITION")]
        risks = [e for e in events if e.event_type.upper() in ("RISK_ALERT", "RISK", "KILL_SWITCH")]
        markets = [e for e in events if e.event_type.upper() in ("MARKET_TICK", "MARKET_BAR", "MARKET")]

        trace.risk_events = risks

        # 构建 legs
        # 简化逻辑：第一个 BUY fill 是入场，第一个 SELL fill 是出场
        # （或反过来：第一个 SELL 是入场空头，BUY 是平仓）
        entry_fill = None
        exit_fill = None
        for f in fills:
            side = f.payload.get("side", "").upper()
            if not entry_fill:
                entry_fill = f
            elif not exit_fill and side != entry_fill.payload.get("side", "").upper():
                exit_fill = f
            elif exit_fill:
                # 多于 2 笔成交，取最后一笔作为最终出场
                exit_fill = f

        if entry_fill:
            trace.entry = self._build_leg(entry_fill, signals, orders)
            trace.entry_price = trace.entry.price

        if exit_fill:
            trace.exit = self._build_leg(exit_fill, signals, orders)
            trace.exit_price = trace.exit.price
            trace.is_closed = True

        # 计算 PnL
        if trace.entry and trace.exit:
            entry_cost = trace.entry.price * trace.entry.qty
            exit_value = trace.exit.price * trace.exit.qty
            entry_fee = trace.entry.fill_event.payload.get("fee", 0) if trace.entry.fill_event else 0
            exit_fee = trace.exit.fill_event.payload.get("fee", 0) if trace.exit.fill_event else 0
            trace.fee = float(entry_fee) + float(exit_fee)

            if trace.entry.side.upper() == "BUY":
                # 多头：买入 → 卖出
                trace.pnl = exit_value - entry_cost - trace.fee
            else:
                # 空头：卖出 → 买入
                trace.pnl = entry_cost - exit_value - trace.fee

            if entry_cost > 0:
                trace.pnl_pct = (trace.pnl / entry_cost) * 100

            # 持仓时间
            trace.holding_ms = trace.exit.timestamp - trace.entry.timestamp

            # 市场变动
            if trace.entry_price > 0:
                trace.market_change = (trace.exit_price - trace.entry_price) / trace.entry_price

        # 计算最大/最小价格
        prices = [m.payload.get("price", 0) for m in markets if m.payload.get("price")]
        if trace.entry_price:
            prices.append(trace.entry_price)
        if trace.exit_price:
            prices.append(trace.exit_price)
        prices = [p for p in prices if p > 0]
        if prices:
            trace.max_price = max(prices)
            trace.min_price = min(prices)

        return trace

    def _build_leg(
        self,
        fill: StoredEvent,
        signals: List[StoredEvent],
        orders: List[StoredEvent],
    ) -> TradeLeg:
        """构建交易腿"""
        leg = TradeLeg(
            side=fill.payload.get("side", ""),
            price=float(fill.payload.get("price", fill.payload.get("filled_price", 0))),
            qty=float(fill.payload.get("qty", fill.payload.get("filled_qty", 0))),
            timestamp=fill.timestamp,
            order_id=fill.payload.get("order_id", ""),
            fill_event=fill,
        )

        # 关联订单
        oid = leg.order_id
        if oid:
            for o in orders:
                if o.payload.get("order_id") == oid:
                    leg.order_event = o
                    leg.order_price = o.payload.get("price")
                    break

        # 关联信号（取 fill 之前最近的信号）
        for s in reversed(signals):
            if s.timestamp <= fill.timestamp:
                leg.signal_event = s
                leg.signal_score = s.payload.get("score", s.payload.get("strength"))
                leg.signal_strategy = s.payload.get("strategy", s.source or "")
                break

        return leg

"""
Symbol Attribution — 品种归因 + Long/Short 归因

回答：
  1. 哪些品种赚钱？（Symbol Leaderboard）
  2. 多空分别赚多少？（Long/Short PnL）

示例：
    Symbol         PnL       Trades  WinRate
    BTCUSDT      +4200        80     60%
    ETHUSDT      +1300        60     55%
    SOLUSDT       -800        30     40%
    BNBUSDT       +300        20     50%

    Long PnL:  +12000
    Short PnL: -8000
    说明：策略做空能力很弱

用法：
    attr = SymbolAttribution(store)
    report = attr.analyze(session_id="s1")
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..event_store import EventStore, StoredEvent

logger = logging.getLogger("quantlab.execution.observe.attribution.symbol")


@dataclass
class SymbolMetric:
    """单品种指标"""
    symbol: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    win_rate: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    profit_factor: float = 0.0
    # 多空
    long_pnl: float = 0.0
    short_pnl: float = 0.0
    n_long: int = 0
    n_short: int = 0
    # 平均
    avg_pnl: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "n_losses": self.n_losses,
            "win_rate": round(self.win_rate, 4),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "profit_factor": round(self.profit_factor, 4),
            "long_pnl": round(self.long_pnl, 2),
            "short_pnl": round(self.short_pnl, 2),
            "n_long": self.n_long,
            "n_short": self.n_short,
            "avg_pnl": round(self.avg_pnl, 2),
        }


@dataclass
class LongShortMetric:
    """多空归因"""
    long_pnl: float = 0.0
    short_pnl: float = 0.0
    total_pnl: float = 0.0
    long_pct: float = 0.0
    short_pct: float = 0.0
    n_long: int = 0
    n_short: int = 0
    n_total: int = 0
    long_win_rate: float = 0.0
    short_win_rate: float = 0.0
    # 评价
    bias: str = ""  # long_bias / short_bias / balanced
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "long_pnl": round(self.long_pnl, 2),
            "short_pnl": round(self.short_pnl, 2),
            "total_pnl": round(self.total_pnl, 2),
            "long_pct": round(self.long_pct, 2),
            "short_pct": round(self.short_pct, 2),
            "n_long": self.n_long,
            "n_short": self.n_short,
            "n_total": self.n_total,
            "long_win_rate": round(self.long_win_rate, 4),
            "short_win_rate": round(self.short_win_rate, 4),
            "bias": self.bias,
            "note": self.note,
        }


@dataclass
class SymbolAttributionReport:
    """品种归因报告"""
    start_ts: int = 0
    end_ts: int = 0
    total_pnl: float = 0.0
    total_trades: int = 0
    # 品种排行榜
    symbols: List[SymbolMetric] = field(default_factory=list)
    best_symbol: str = ""
    worst_symbol: str = ""
    # 多空归因
    long_short: LongShortMetric = field(default_factory=LongShortMetric)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "symbols": [s.to_dict() for s in self.symbols],
            "best_symbol": self.best_symbol,
            "worst_symbol": self.worst_symbol,
            "long_short": self.long_short.to_dict(),
        }


class SymbolAttribution:
    """
    品种归因 + 多空归因

    用法：
        attr = SymbolAttribution(store)
        report = attr.analyze(session_id="s1")
    """

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def analyze(self, session_id: str) -> SymbolAttributionReport:
        """分析整个会话"""
        events = self.store.query(session_id=session_id, limit=100000)
        return self._build(events)

    def analyze_range(
        self,
        start_ts: int,
        end_ts: int,
        session_id: Optional[str] = None,
    ) -> SymbolAttributionReport:
        """分析时间范围"""
        events = self.store.query(
            session_id=session_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=100000,
        )
        return self._build(events)

    # ------------------------------------------------------------------

    def _build(self, events: List[StoredEvent]) -> SymbolAttributionReport:
        """构建报告"""
        report = SymbolAttributionReport()
        if not events:
            return report

        report.start_ts = events[0].timestamp
        report.end_ts = events[-1].timestamp

        # 按 trace 分组
        traces: Dict[str, List[StoredEvent]] = defaultdict(list)
        for e in events:
            tid = e.trace_id or e.event_id
            traces[tid].append(e)

        # 提取每笔交易
        # records: List[(symbol, pnl, side)]
        records: List[Tuple[str, float, str]] = []
        for tid, evs in traces.items():
            symbol, pnl, side = self._extract_trade(evs)
            if pnl is not None and symbol:
                records.append((symbol, pnl, side))

        if not records:
            return report

        total_pnl = sum(p for _, p, _ in records)
        report.total_pnl = total_pnl
        report.total_trades = len(records)

        # 按品种聚合
        symbol_records: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        for symbol, pnl, side in records:
            symbol_records[symbol].append((pnl, side))

        for symbol, recs in symbol_records.items():
            m = SymbolMetric(symbol=symbol)
            m.pnl = sum(p for p, _ in recs)
            m.pnl_pct = (m.pnl / total_pnl * 100) if total_pnl != 0 else 0
            m.n_trades = len(recs)
            m.n_wins = sum(1 for p, _ in recs if p > 0)
            m.n_losses = sum(1 for p, _ in recs if p < 0)
            m.win_rate = m.n_wins / m.n_trades if m.n_trades else 0
            m.gross_profit = sum(p for p, _ in recs if p > 0)
            m.gross_loss = abs(sum(p for p, _ in recs if p < 0))
            m.profit_factor = m.gross_profit / m.gross_loss if m.gross_loss > 0 else float('inf')
            m.avg_pnl = m.pnl / m.n_trades if m.n_trades else 0
            # 多空
            m.long_pnl = sum(p for p, s in recs if s.upper() == "BUY")
            m.short_pnl = sum(p for p, s in recs if s.upper() == "SELL")
            m.n_long = sum(1 for _, s in recs if s.upper() == "BUY")
            m.n_short = sum(1 for _, s in recs if s.upper() == "SELL")
            report.symbols.append(m)

        # 按 PnL 降序
        report.symbols.sort(key=lambda s: s.pnl, reverse=True)
        if report.symbols:
            report.best_symbol = report.symbols[0].symbol
            report.worst_symbol = report.symbols[-1].symbol

        # 多空归因
        ls = LongShortMetric()
        ls.long_pnl = sum(p for _, p, s in records if s.upper() == "BUY")
        ls.short_pnl = sum(p for _, p, s in records if s.upper() == "SELL")
        ls.total_pnl = total_pnl
        ls.n_long = sum(1 for _, _, s in records if s.upper() == "BUY")
        ls.n_short = sum(1 for _, _, s in records if s.upper() == "SELL")
        ls.n_total = len(records)
        if total_pnl != 0:
            ls.long_pct = ls.long_pnl / total_pnl * 100
            ls.short_pct = ls.short_pnl / total_pnl * 100
        long_wins = sum(1 for _, p, s in records if s.upper() == "BUY" and p > 0)
        short_wins = sum(1 for _, p, s in records if s.upper() == "SELL" and p > 0)
        ls.long_win_rate = long_wins / ls.n_long if ls.n_long else 0
        ls.short_win_rate = short_wins / ls.n_short if ls.n_short else 0

        # 评价
        if ls.n_long > 0 and ls.n_short == 0:
            ls.bias = "long_only"
            ls.note = "仅做多"
        elif ls.n_short > 0 and ls.n_long == 0:
            ls.bias = "short_only"
            ls.note = "仅做空"
        elif ls.long_pnl > 0 and ls.short_pnl < 0:
            ls.bias = "long_bias"
            ls.note = "做多盈利，做空亏损，做空能力弱"
        elif ls.short_pnl > 0 and ls.long_pnl < 0:
            ls.bias = "short_bias"
            ls.note = "做空盈利，做多亏损"
        else:
            ls.bias = "balanced"
            ls.note = "多空均衡"

        report.long_short = ls
        return report

    def _extract_trade(
        self,
        events: List[StoredEvent],
    ) -> Tuple[str, Optional[float], str]:
        """
        提取单笔交易的 (symbol, pnl, side)

        side: 入场方向 BUY / SELL
        """
        events = sorted(events, key=lambda e: e.timestamp)

        # symbol
        symbol = ""
        for e in events:
            symbol = e.payload.get("symbol", "")
            if symbol:
                break

        # pnl
        pnl = None
        for e in events:
            if e.event_type.upper() == "FILL":
                p = e.payload.get("pnl")
                if p is not None:
                    pnl = float(p)
                    break

        if pnl is None:
            fills = [e for e in events if e.event_type.upper() == "FILL"]
            if len(fills) >= 2:
                entry = fills[0]
                exit = fills[-1]
                entry_price = float(entry.payload.get("price", 0))
                exit_price = float(exit.payload.get("price", 0))
                qty = float(entry.payload.get("qty", 0))
                entry_side = entry.payload.get("side", "BUY").upper()
                if entry_price and exit_price and qty:
                    if entry_side == "BUY":
                        pnl = (exit_price - entry_price) * qty
                    else:
                        pnl = (entry_price - exit_price) * qty

        # side（入场方向）
        side = "BUY"
        for e in events:
            if e.event_type.upper() == "FILL":
                side = e.payload.get("side", "BUY")
                break
            if e.event_type.upper() == "SIGNAL":
                side = e.payload.get("side", side)
                # 不 break，FILL 优先

        return symbol, pnl, side

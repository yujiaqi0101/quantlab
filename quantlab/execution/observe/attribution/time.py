"""
Time Attribution — 时间归因 + Regime 归因

回答：
  1. 什么时候赚钱？（亚洲/欧洲/美洲时段）
  2. 哪个市场状态下赚钱？（Bull/Bear/Sideways）

示例：
    时段归因：
        亚洲   +1000
        欧洲   +6000
        美洲   -2000

    Regime 归因：
        Bull      +20%
        Bear      -5%
        Sideways  -3%
        发现：策略只适合牛市

用法：
    attr = TimeAttribution(store)
    report = attr.analyze(session_id="s1")
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..event_store import EventStore, StoredEvent

logger = logging.getLogger("quantlab.execution.observe.attribution.time")


# 时段定义（UTC 小时范围）
# 亚洲：00:00-08:00 UTC（对应北京时间 08:00-16:00）
# 欧洲：08:00-14:00 UTC（对应北京时间 16:00-22:00）
# 美洲：14:00-24:00 UTC（对应北京时间 22:00-06:00）
SESSIONS_UTC = {
    "asia": (0, 8),
    "europe": (8, 14),
    "america": (14, 24),
}


@dataclass
class TimeSlotMetric:
    """时段指标"""
    slot: str = ""  # asia / europe / america
    label: str = ""  # 亚洲 / 欧洲 / 美洲
    pnl: float = 0.0
    pnl_pct: float = 0.0
    n_trades: int = 0
    n_wins: int = 0
    win_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slot": self.slot,
            "label": self.label,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "win_rate": round(self.win_rate, 4),
        }


@dataclass
class RegimeMetric:
    """市场状态指标"""
    regime: str = ""  # bull / bear / sideways
    label: str = ""   # 牛市 / 熊市 / 震荡
    pnl: float = 0.0
    pnl_pct: float = 0.0
    n_trades: int = 0
    n_wins: int = 0
    win_rate: float = 0.0
    # 该状态持续时间占比
    duration_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime,
            "label": self.label,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "n_trades": self.n_trades,
            "n_wins": self.n_wins,
            "win_rate": round(self.win_rate, 4),
            "duration_pct": round(self.duration_pct, 2),
        }


@dataclass
class TimeAttributionReport:
    """时间归因报告"""
    start_ts: int = 0
    end_ts: int = 0
    total_pnl: float = 0.0
    total_trades: int = 0
    # 时段归因
    time_slots: List[TimeSlotMetric] = field(default_factory=list)
    best_slot: str = ""
    worst_slot: str = ""
    # Regime 归因
    regimes: List[RegimeMetric] = field(default_factory=list)
    best_regime: str = ""
    worst_regime: str = ""
    regime_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "time_slots": [t.to_dict() for t in self.time_slots],
            "best_slot": self.best_slot,
            "worst_slot": self.worst_slot,
            "regimes": [r.to_dict() for r in self.regimes],
            "best_regime": self.best_regime,
            "worst_regime": self.worst_regime,
            "regime_note": self.regime_note,
        }


class TimeAttribution:
    """
    时间归因 + Regime 归因

    用法：
        attr = TimeAttribution(store)
        report = attr.analyze(session_id="s1")
    """

    # Regime 判定阈值
    BULL_THRESHOLD = 0.02   # 上涨 2% 以上算牛市
    BEAR_THRESHOLD = -0.02  # 下跌 2% 以上算熊市

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def analyze(self, session_id: str) -> TimeAttributionReport:
        """分析整个会话"""
        events = self.store.query(session_id=session_id, limit=100000)
        return self._build(events)

    def analyze_range(
        self,
        start_ts: int,
        end_ts: int,
        session_id: Optional[str] = None,
    ) -> TimeAttributionReport:
        """分析时间范围"""
        events = self.store.query(
            session_id=session_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=100000,
        )
        return self._build(events)

    # ------------------------------------------------------------------

    def _build(self, events: List[StoredEvent]) -> TimeAttributionReport:
        """构建报告"""
        report = TimeAttributionReport()
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
        # records: List[(pnl, entry_ts, regime)]
        records: List[Tuple[float, int, str]] = []
        for tid, evs in traces.items():
            pnl, entry_ts = self._extract_trade_pnl(evs)
            if pnl is not None:
                # 判定 regime
                regime = self._detect_regime(evs)
                records.append((pnl, entry_ts, regime))

        if not records:
            return report

        total_pnl = sum(p for p, _, _ in records)
        report.total_pnl = total_pnl
        report.total_trades = len(records)

        # 时段归因
        report.time_slots = self._build_time_slots(records, total_pnl)
        if report.time_slots:
            sorted_slots = sorted(report.time_slots, key=lambda t: t.pnl, reverse=True)
            report.best_slot = sorted_slots[0].slot
            report.worst_slot = sorted_slots[-1].slot

        # Regime 归因
        report.regimes = self._build_regimes(records, total_pnl)
        if report.regimes:
            sorted_regimes = sorted(report.regimes, key=lambda r: r.pnl, reverse=True)
            report.best_regime = sorted_regimes[0].regime
            report.worst_regime = sorted_regimes[-1].regime
            report.regime_note = self._regime_note(report.regimes)

        return report

    def _build_time_slots(
        self,
        records: List[Tuple[float, int, str]],
        total_pnl: float,
    ) -> List[TimeSlotMetric]:
        """构建时段归因"""
        slot_data: Dict[str, List[float]] = defaultdict(list)
        for pnl, ts, _ in records:
            slot = self._get_time_slot(ts)
            slot_data[slot].append(pnl)

        result = []
        for slot, (start_h, end_h) in SESSIONS_UTC.items():
            pnls = slot_data.get(slot, [])
            m = TimeSlotMetric(
                slot=slot,
                label={"asia": "亚洲", "europe": "欧洲", "america": "美洲"}.get(slot, slot),
                pnl=sum(pnls),
                n_trades=len(pnls),
                n_wins=sum(1 for p in pnls if p > 0),
            )
            m.pnl_pct = (m.pnl / total_pnl * 100) if total_pnl != 0 else 0
            m.win_rate = m.n_wins / m.n_trades if m.n_trades else 0
            result.append(m)

        return result

    def _build_regimes(
        self,
        records: List[Tuple[float, int, str]],
        total_pnl: float,
    ) -> List[RegimeMetric]:
        """构建 Regime 归因"""
        regime_data: Dict[str, List[float]] = defaultdict(list)
        for pnl, _, regime in records:
            regime_data[regime].append(pnl)

        result = []
        for regime in ["bull", "bear", "sideways"]:
            pnls = regime_data.get(regime, [])
            m = RegimeMetric(
                regime=regime,
                label={"bull": "牛市", "bear": "熊市", "sideways": "震荡"}.get(regime, regime),
                pnl=sum(pnls),
                n_trades=len(pnls),
                n_wins=sum(1 for p in pnls if p > 0),
            )
            m.pnl_pct = (m.pnl / total_pnl * 100) if total_pnl != 0 else 0
            m.win_rate = m.n_wins / m.n_trades if m.n_trades else 0
            m.duration_pct = len(pnls) / len(records) * 100 if records else 0
            result.append(m)

        return result

    def _get_time_slot(self, ts_ms: int) -> str:
        """根据时间戳判断时段（UTC）"""
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        hour = dt.hour
        for slot, (start, end) in SESSIONS_UTC.items():
            if start <= hour < end:
                return slot
        return "america"  # 默认

    def _detect_regime(self, events: List[StoredEvent]) -> str:
        """
        判定市场状态

        基于交易期间的市场价格变动：
          - 上涨超过 BULL_THRESHOLD → bull
          - 下跌超过 BEAR_THRESHOLD → bear
          - 其他 → sideways
        """
        # 找市场价格
        prices: List[Tuple[int, float]] = []
        for e in events:
            if e.event_type.upper() in ("MARKET_TICK", "MARKET_BAR", "MARKET"):
                price = e.payload.get("price") or e.payload.get("close")
                if price:
                    prices.append((e.timestamp, float(price)))

        if len(prices) < 2:
            return "sideways"

        prices.sort(key=lambda x: x[0])
        first_price = prices[0][1]
        last_price = prices[-1][1]

        if first_price <= 0:
            return "sideways"

        change = (last_price - first_price) / first_price
        if change > self.BULL_THRESHOLD:
            return "bull"
        elif change < self.BEAR_THRESHOLD:
            return "bear"
        else:
            return "sideways"

    def _regime_note(self, regimes: List[RegimeMetric]) -> str:
        """生成 Regime 评价"""
        bull = next((r for r in regimes if r.regime == "bull"), None)
        bear = next((r for r in regimes if r.regime == "bear"), None)

        if bull and bear:
            if bull.pnl > 0 and bear.pnl < 0:
                return "策略只适合牛市"
            elif bull.pnl < 0 and bear.pnl > 0:
                return "策略适合熊市"
        elif bull and bull.pnl > 0 and not bear:
            return "策略在牛市表现良好"
        elif bear and bear.pnl > 0 and not bull:
            return "策略在熊市表现良好"
        return ""

    def _extract_trade_pnl(
        self,
        events: List[StoredEvent],
    ) -> Tuple[Optional[float], int]:
        """提取单笔交易的 (pnl, entry_timestamp)"""
        events = sorted(events, key=lambda e: e.timestamp)

        # entry timestamp：第一个 FILL 或 SIGNAL
        entry_ts = events[0].timestamp
        for e in events:
            if e.event_type.upper() in ("FILL", "SIGNAL"):
                entry_ts = e.timestamp
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

        return pnl, entry_ts

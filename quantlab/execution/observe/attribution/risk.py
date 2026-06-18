"""
Risk Attribution — 风险归因 + Drawdown 归因

回答：
  1. 哪个策略贡献最多风险？
  2. 谁导致回撤？

示例：
    风险归因：
        BTC_Momentum  收益贡献 40%  风险贡献 80%  → 收益质量差
        LGBM_Trend    收益贡献 28%  风险贡献 15%  → 收益质量好

    回撤归因：
        最大回撤 -12%
        BTC_Momentum  -8%
        ETH_MeanRev   -3%
        Others        -1%

用法：
    attr = RiskAttribution(store)
    report = attr.analyze(session_id="s1")
"""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..event_store import EventStore, StoredEvent

logger = logging.getLogger("quantlab.execution.observe.attribution.risk")


@dataclass
class RiskContribution:
    """单策略风险贡献"""
    strategy: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0       # 收益贡献
    pnl_std: float = 0.0       # PnL 波动率
    risk_pct: float = 0.0      # 风险贡献
    # 收益质量 = 收益贡献 / 风险贡献
    quality_ratio: float = 0.0
    quality_label: str = ""    # good / bad / neutral
    # Sharpe（简化版）
    sharpe: float = 0.0
    n_trades: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "pnl_std": round(self.pnl_std, 2),
            "risk_pct": round(self.risk_pct, 2),
            "quality_ratio": round(self.quality_ratio, 4),
            "quality_label": self.quality_label,
            "sharpe": round(self.sharpe, 4),
            "n_trades": self.n_trades,
        }


@dataclass
class DrawdownContribution:
    """单策略回撤贡献"""
    strategy: str = ""
    max_drawdown: float = 0.0   # 该策略最大回撤
    drawdown_pct: float = 0.0   # 占总回撤百分比
    # 回撤期间
    peak_ts: int = 0
    trough_ts: int = 0
    duration_ms: int = 0
    n_trades: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy,
            "max_drawdown": round(self.max_drawdown, 2),
            "drawdown_pct": round(self.drawdown_pct, 2),
            "peak_ts": self.peak_ts,
            "trough_ts": self.trough_ts,
            "duration_ms": self.duration_ms,
            "n_trades": self.n_trades,
        }


@dataclass
class RiskAttributionReport:
    """风险归因报告"""
    start_ts: int = 0
    end_ts: int = 0
    total_pnl: float = 0.0
    total_trades: int = 0
    # 风险归因
    risk_contributions: List[RiskContribution] = field(default_factory=list)
    best_quality_strategy: str = ""
    worst_quality_strategy: str = ""
    # 回撤归因
    overall_max_drawdown: float = 0.0
    drawdown_contributions: List[DrawdownContribution] = field(default_factory=list)
    drawdown_culprit: str = ""  # 回撤元凶

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "risk_contributions": [r.to_dict() for r in self.risk_contributions],
            "best_quality_strategy": self.best_quality_strategy,
            "worst_quality_strategy": self.worst_quality_strategy,
            "overall_max_drawdown": round(self.overall_max_drawdown, 2),
            "drawdown_contributions": [d.to_dict() for d in self.drawdown_contributions],
            "drawdown_culprit": self.drawdown_culprit,
        }


class RiskAttribution:
    """
    风险归因 + 回撤归因

    用法：
        attr = RiskAttribution(store)
        report = attr.analyze(session_id="s1")
    """

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def analyze(self, session_id: str) -> RiskAttributionReport:
        """分析整个会话"""
        events = self.store.query(session_id=session_id, limit=100000)
        return self._build(events)

    def analyze_range(
        self,
        start_ts: int,
        end_ts: int,
        session_id: Optional[str] = None,
    ) -> RiskAttributionReport:
        """分析时间范围"""
        events = self.store.query(
            session_id=session_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=100000,
        )
        return self._build(events)

    # ------------------------------------------------------------------

    def _build(self, events: List[StoredEvent]) -> RiskAttributionReport:
        """构建报告"""
        report = RiskAttributionReport()
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
        # records: List[(strategy, pnl, ts)]
        records: List[Tuple[str, float, int]] = []
        for tid, evs in traces.items():
            pnl, strategy, ts = self._extract_trade(evs)
            if pnl is not None:
                records.append((strategy, pnl, ts))

        if not records:
            return report

        total_pnl = sum(p for _, p, _ in records)
        report.total_pnl = total_pnl
        report.total_trades = len(records)

        # 按策略聚合
        strategy_records: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        for strategy, pnl, ts in records:
            strategy_records[strategy].append((pnl, ts))

        # 风险归因
        report.risk_contributions = self._build_risk(strategy_records, total_pnl)
        if report.risk_contributions:
            sorted_q = sorted(
                report.risk_contributions,
                key=lambda r: r.quality_ratio,
                reverse=True,
            )
            report.best_quality_strategy = sorted_q[0].strategy
            report.worst_quality_strategy = sorted_q[-1].strategy

        # 回撤归因
        report.drawdown_contributions = self._build_drawdown(strategy_records)
        if report.drawdown_contributions:
            report.overall_max_drawdown = sum(d.max_drawdown for d in report.drawdown_contributions)
            sorted_dd = sorted(
                report.drawdown_contributions,
                key=lambda d: d.max_drawdown,
            )
            report.drawdown_culprit = sorted_dd[0].strategy

        return report

    def _build_risk(
        self,
        strategy_records: Dict[str, List[Tuple[float, int]]],
        total_pnl: float,
    ) -> List[RiskContribution]:
        """构建风险归因"""
        # 计算每个策略的 PnL 标准差
        strategy_stds: Dict[str, float] = {}
        for strategy, recs in strategy_records.items():
            pnls = [p for p, _ in recs]
            strategy_stds[strategy] = self._std(pnls)

        total_std = sum(strategy_stds.values())

        result = []
        for strategy, recs in strategy_records.items():
            pnls = [p for p, _ in recs]
            pnl = sum(pnls)
            std = strategy_stds[strategy]

            rc = RiskContribution(
                strategy=strategy,
                pnl=pnl,
                pnl_pct=(pnl / total_pnl * 100) if total_pnl != 0 else 0,
                pnl_std=std,
                risk_pct=(std / total_std * 100) if total_std > 0 else 0,
                n_trades=len(pnls),
                sharpe=(pnl / std) if std > 0 else 0,
            )

            # 收益质量 = 收益贡献 / 风险贡献
            if rc.risk_pct > 0:
                rc.quality_ratio = rc.pnl_pct / rc.risk_pct
                if rc.quality_ratio > 1.5:
                    rc.quality_label = "good"
                elif rc.quality_ratio < 0.5:
                    rc.quality_label = "bad"
                else:
                    rc.quality_label = "neutral"
            else:
                rc.quality_label = "neutral"

            result.append(rc)

        # 按 PnL 降序
        result.sort(key=lambda r: r.pnl, reverse=True)
        return result

    def _build_drawdown(
        self,
        strategy_records: Dict[str, List[Tuple[float, int]]],
    ) -> List[DrawdownContribution]:
        """构建回撤归因"""
        result = []
        for strategy, recs in strategy_records.items():
            # 按时间排序
            sorted_recs = sorted(recs, key=lambda x: x[1])

            # 计算累计 PnL 曲线
            cum_pnl = 0.0
            peak = 0.0
            max_dd = 0.0
            peak_ts = sorted_recs[0][1] if sorted_recs else 0
            trough_ts = peak_ts

            for pnl, ts in sorted_recs:
                cum_pnl += pnl
                if cum_pnl > peak:
                    peak = cum_pnl
                    peak_ts = ts
                dd = cum_pnl - peak
                if dd < max_dd:
                    max_dd = dd
                    trough_ts = ts

            dc = DrawdownContribution(
                strategy=strategy,
                max_drawdown=max_dd,
                peak_ts=peak_ts,
                trough_ts=trough_ts,
                duration_ms=trough_ts - peak_ts,
                n_trades=len(recs),
            )
            result.append(dc)

        # 按回撤升序（最负在前）
        result.sort(key=lambda d: d.max_drawdown)
        return result

    def _extract_trade(
        self,
        events: List[StoredEvent],
    ) -> Tuple[Optional[float], str, int]:
        """提取 (pnl, strategy, entry_ts)"""
        events = sorted(events, key=lambda e: e.timestamp)

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

        # strategy
        strategy = "unknown"
        for e in events:
            if e.event_type.upper() == "SIGNAL":
                strategy = e.payload.get("strategy", e.source or "unknown")
                break
        if strategy == "unknown":
            for e in events:
                if e.session_id:
                    session = self.store.get_session(e.session_id)
                    if session and session.strategy:
                        strategy = session.strategy
                    break

        return pnl, strategy, entry_ts

    def _std(self, values: List[float]) -> float:
        """标准差"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(var)

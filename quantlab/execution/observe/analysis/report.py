"""
Report — 报告生成 + 异常检测

聚合 TradeTrace + RootCause + Explanation，生成完整报告。
同时提供会话级异常检测：
  - 连续亏损 N 笔
  - 滑点异常
  - 策略无信号

用法：
    reporter = AnalysisReporter(store)
    report = reporter.analyze_trace(trace_id)
    anomalies = reporter.detect_anomalies(session_id)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .explain import Explanation, ExplainEngine
from .root_cause import CauseSeverity, CauseType, RootCause, RootCauseAnalyzer
from .trace import TradeTrace, TraceBuilder

logger = logging.getLogger("quantlab.execution.observe.analysis.report")


@dataclass
class TraceReport:
    """单笔交易分析报告"""
    trace: TradeTrace
    causes: List[RootCause] = field(default_factory=list)
    explanation: Optional[Explanation] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace": self.trace.to_dict(),
            "causes": [c.to_dict() for c in self.causes],
            "explanation": self.explanation.to_dict() if self.explanation else None,
        }


@dataclass
class Anomaly:
    """异常"""
    type: str = ""           # consecutive_losses / slippage_spike / no_signal / etc.
    severity: CauseSeverity = CauseSeverity.WARNING
    title: str = ""
    description: str = ""
    # 相关数据
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "data": self.data,
        }


@dataclass
class AnomalyReport:
    """异常报告"""
    session_id: str = ""
    n_traces: int = 0
    n_anomalies: int = 0
    anomalies: List[Anomaly] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "n_traces": self.n_traces,
            "n_anomalies": self.n_anomalies,
            "anomalies": [a.to_dict() for a in self.anomalies],
        }


class AnalysisReporter:
    """
    分析报告生成器

    用法：
        reporter = AnalysisReporter(store)
        report = reporter.analyze_trace(trace_id)
        report = reporter.analyze_event(event_id)
        losses = reporter.analyze_losses(session_id)
        anomalies = reporter.detect_anomalies(session_id)
    """

    def __init__(self, store) -> None:
        self.store = store
        self.trace_builder = TraceBuilder(store)
        self.analyzer = RootCauseAnalyzer()
        self.explainer = ExplainEngine()

    # ------------------------------------------------------------------
    # 单笔交易分析
    # ------------------------------------------------------------------

    def analyze_trace(self, trace_id: str) -> TraceReport:
        """分析单笔交易（按 trace_id）"""
        trace = self.trace_builder.build_from_trace_id(trace_id)
        return self._build_report(trace)

    def analyze_event(self, event_id: str) -> TraceReport:
        """分析单笔交易（按事件 ID）"""
        trace = self.trace_builder.build_from_event(event_id)
        return self._build_report(trace)

    def analyze_losses(
        self,
        session_id: str,
        top_n: int = 10,
    ) -> List[TraceReport]:
        """分析会话中的亏损交易"""
        loss_traces = self.trace_builder.build_loss_traces(session_id, top_n=top_n)
        return [self._build_report(t) for t in loss_traces]

    def analyze_session(self, session_id: str) -> List[TraceReport]:
        """分析会话所有交易"""
        traces = self.trace_builder.build_session_traces(session_id)
        return [self._build_report(t) for t in traces]

    def _build_report(self, trace: TradeTrace) -> TraceReport:
        """构建报告"""
        causes = self.analyzer.analyze(trace)
        explanation = self.explainer.explain(trace, causes) if causes else None
        return TraceReport(trace=trace, causes=causes, explanation=explanation)

    # ------------------------------------------------------------------
    # 异常检测
    # ------------------------------------------------------------------

    def detect_anomalies(
        self,
        session_id: str,
        consecutive_losses_threshold: int = 3,
        slippage_threshold_bps: float = 50.0,
        no_signal_hours: float = 24.0,
    ) -> AnomalyReport:
        """
        检测会话异常

        检测项：
          - consecutive_losses: 连续亏损 N 笔
          - slippage_spike: 滑点异常
          - no_signal: 策略长时间无信号
          - fill_without_signal: 成交无对应信号
          - order_without_fill: 订单未成交
        """
        report = AnomalyReport(session_id=session_id)

        # 获取所有交易
        traces = self.trace_builder.build_session_traces(session_id)
        report.n_traces = len(traces)

        # 1. 连续亏损
        report.anomalies.extend(self._detect_consecutive_losses(
            traces, consecutive_losses_threshold
        ))

        # 2. 滑点异常
        report.anomalies.extend(self._detect_slippage_spike(
            traces, slippage_threshold_bps
        ))

        # 3. 无信号
        report.anomalies.extend(self._detect_no_signal(
            session_id, no_signal_hours
        ))

        # 4. 成交无信号 / 订单未成交（基于事件）
        report.anomalies.extend(self._detect_event_anomalies(session_id))

        report.n_anomalies = len(report.anomalies)
        return report

    def _detect_consecutive_losses(
        self,
        traces: List[TradeTrace],
        threshold: int,
    ) -> List[Anomaly]:
        """检测连续亏损"""
        anomalies = []

        # 按时间排序
        closed = sorted(
            [t for t in traces if t.is_closed],
            key=lambda t: t.entry.timestamp if t.entry else 0,
        )

        streak = 0
        streak_traces: List[TradeTrace] = []
        for t in closed:
            if t.is_loss:
                streak += 1
                streak_traces.append(t)
            else:
                if streak >= threshold:
                    anomalies.append(Anomaly(
                        type="consecutive_losses",
                        severity=CauseSeverity.WARNING if streak < 5 else CauseSeverity.CRITICAL,
                        title=f"连续亏损 {streak} 笔",
                        description=f"策略在会话中出现连续 {streak} 笔亏损交易",
                        data={
                            "streak": streak,
                            "trace_ids": [t.trace_id for t in streak_traces],
                            "total_loss": sum(t.pnl or 0 for t in streak_traces),
                        },
                    ))
                streak = 0
                streak_traces = []

        # 末尾检查
        if streak >= threshold:
            anomalies.append(Anomaly(
                type="consecutive_losses",
                severity=CauseSeverity.WARNING if streak < 5 else CauseSeverity.CRITICAL,
                title=f"连续亏损 {streak} 笔",
                description=f"策略在会话中出现连续 {streak} 笔亏损交易",
                data={
                    "streak": streak,
                    "trace_ids": [t.trace_id for t in streak_traces],
                    "total_loss": sum(t.pnl or 0 for t in streak_traces),
                },
            ))

        return anomalies

    def _detect_slippage_spike(
        self,
        traces: List[TradeTrace],
        threshold_bps: float,
    ) -> List[Anomaly]:
        """检测滑点异常"""
        anomalies = []

        for t in traces:
            for leg_name, leg in [("entry", t.entry), ("exit", t.exit)]:
                if leg and leg.slippage_bps > threshold_bps:
                    anomalies.append(Anomaly(
                        type="slippage_spike",
                        severity=CauseSeverity.CRITICAL,
                        title=f"滑点异常 {leg.slippage_bps:.1f} bps",
                        description=f"{t.symbol} {leg_name} 滑点 {leg.slippage_bps:.1f} bps，超过阈值 {threshold_bps} bps",
                        data={
                            "trace_id": t.trace_id,
                            "symbol": t.symbol,
                            "leg": leg_name,
                            "slippage_bps": leg.slippage_bps,
                        },
                    ))

        return anomalies

    def _detect_no_signal(
        self,
        session_id: str,
        threshold_hours: float,
    ) -> List[Anomaly]:
        """检测策略长时间无信号"""
        anomalies = []

        # 查询所有 SIGNAL 事件
        signals = self.store.query(
            session_id=session_id,
            event_type="SIGNAL",
            limit=100000,
        )

        if not signals:
            # 整个会话无信号
            sessions = self.store.list_sessions()
            for s in sessions:
                if s["session_id"] == session_id:
                    duration_ms = s.get("end_time", 0) - s.get("start_time", 0)
                    if duration_ms > threshold_hours * 3600000:
                        anomalies.append(Anomaly(
                            type="no_signal",
                            severity=CauseSeverity.WARNING,
                            title=f"策略 {threshold_hours} 小时无信号",
                            description=f"会话 {session_id} 期间无任何信号产生",
                            data={"session_id": session_id},
                        ))
                    break
            return anomalies

        # 检查信号间隔
        signals = sorted(signals, key=lambda e: e.timestamp)
        threshold_ms = threshold_hours * 3600000

        for i in range(1, len(signals)):
            gap = signals[i].timestamp - signals[i-1].timestamp
            if gap > threshold_ms:
                anomalies.append(Anomaly(
                    type="no_signal",
                    severity=CauseSeverity.WARNING,
                    title=f"策略 {gap/3600000:.1f} 小时无信号",
                    description=f"从 {signals[i-1].timestamp} 到 {signals[i].timestamp} 无信号",
                    data={
                        "gap_ms": gap,
                        "gap_hours": gap / 3600000,
                    },
                ))

        return anomalies

    def _detect_event_anomalies(self, session_id: str) -> List[Anomaly]:
        """检测事件级异常（成交无信号、订单未成交）"""
        anomalies = []

        # 按 trace_id 分组
        events = self.store.query(session_id=session_id, limit=100000)
        traces: Dict[str, List[Any]] = defaultdict(list)
        for e in events:
            tid = e.trace_id or e.event_id
            traces[tid].append(e)

        for tid, evs in traces.items():
            types = {e.event_type.upper() for e in evs}

            # 成交无信号
            if "FILL" in types and "SIGNAL" not in types:
                anomalies.append(Anomaly(
                    type="fill_without_signal",
                    severity=CauseSeverity.WARNING,
                    title="成交无对应信号",
                    description=f"trace {tid} 有成交但无信号事件",
                    data={"trace_id": tid},
                ))

            # 订单未成交
            if "ORDER_NEW" in types and "FILL" not in types:
                anomalies.append(Anomaly(
                    type="order_without_fill",
                    severity=CauseSeverity.WARNING,
                    title="订单未成交",
                    description=f"trace {tid} 有订单但无成交事件",
                    data={"trace_id": tid},
                ))

        return anomalies

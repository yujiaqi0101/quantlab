"""
Observe Studio V3 — Analysis 模块

根因分析（Root Cause Analysis）：
  - TradeTrace: 交易链路核心对象
  - RootCauseAnalyzer: 根因分析器（5 种原因类型）
  - ExplainEngine: 解释引擎（生成自然语言）
  - AnalysisReporter: 报告生成 + 异常检测

用法：
    from quantlab.execution.observe.analysis import (
        AnalysisReporter,
        TraceBuilder,
        RootCauseAnalyzer,
        ExplainEngine,
    )

    reporter = AnalysisReporter(store)
    report = reporter.analyze_trace("trace_xxx")
    print(report.explanation.to_text())
"""

from .explain import ExplainEngine, Explanation
from .report import AnalysisReporter, Anomaly, AnomalyReport, TraceReport
from .root_cause import CauseSeverity, CauseType, RootCause, RootCauseAnalyzer
from .trace import TradeLeg, TradeTrace, TraceBuilder

__all__ = [
    # trace
    "TradeLeg",
    "TradeTrace",
    "TraceBuilder",
    # root cause
    "CauseType",
    "CauseSeverity",
    "RootCause",
    "RootCauseAnalyzer",
    # explain
    "Explanation",
    "ExplainEngine",
    # report
    "TraceReport",
    "Anomaly",
    "AnomalyReport",
    "AnalysisReporter",
]

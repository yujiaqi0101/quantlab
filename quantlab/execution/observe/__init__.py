"""
Observability 生命线 — 可观测性

五个核心能力：
  1. Metrics — PnL / Latency / Exposure / Error Rate
  2. Logging — 结构化日志
  3. Tracing — 分布式追踪
  4. Journal — 人为解释层
  5. Replay — 完整交易重放

Observe Studio 扩展：
  6. TradeAnalytics — 交易分析（profit_factor / expectancy / win_rate）
  7. Health — 策略健康监控（24h 信号/成交/收益）
  8. Timeline — 事件时间线视图

Observe Studio V2 扩展（Replay 优先）：
  9.  EventStore      — SQLite 事件持久化
  10. Session         — 交易会话管理
  11. TimelineService — 从 EventStore 读取时间线
  12. ReplayState     — 重放状态（持仓/订单/权益 随事件推进）
  13. ReplayController — 重放控制器（Play/Pause/Stop/Next/Prev/Seek）
  14. RCA             — 根因分析（交易链路定位）

Observe Studio V3 扩展（Root Cause Analysis）：
  15. TradeTrace        — 交易链路核心对象（入场/出场/滑点/PnL）
  16. RootCauseAnalyzer — 根因分析器（5 种原因类型）
  17. ExplainEngine     — 解释引擎（生成自然语言）
  18. AnalysisReporter  — 报告生成 + 异常检测

Observe Studio V4 扩展（Performance Attribution）：
  19. StrategyAttribution — 策略归因（收益/风险贡献）
  20. SymbolAttribution   — 品种归因 + Long/Short 归因
  21. TimeAttribution     — 时段归因 + Regime 归因
  22. RiskAttribution     — 风险归因 + Drawdown 归因
  23. FactorAttribution   — 因子归因（接口预留）
  24. MonthlyReview       — 月度复盘引擎
"""

from .metrics import MetricsCollector, MetricType
from .journal import TradeJournal, JournalEntry
from .replay import ReplayEngine, ReplayEvent
from .trade_analytics import TradeAnalytics, TradeAnalyticsReport
from .health import (
    StrategyHealthMonitor,
    StrategyHealth,
    HealthStatus,
    HealthConfig,
    get_health_monitor,
    set_health_monitor,
)
from .timeline import TimelineView, TimelineEntry, TraceSummary
from .event_store import (
    EventStore,
    StoredEvent,
    SessionInfo,
    get_event_store,
    set_event_store,
)
from .session import (
    TradingSession,
    SessionManager,
    get_session_manager,
)
from .timeline_service import (
    TimelineService,
    TimelineItem,
)
from .replay_state import (
    ReplayState,
    ReplayPosition,
    ReplayOrder,
)
from .replay_controller import (
    ReplayController,
    ReplaySnapshot,
    ReplayStatus,
    get_replay_controller,
)
from .rca import (
    RootCauseAnalysis,
    TradeChain,
)
from .analysis import (
    TradeLeg,
    TradeTrace,
    TraceBuilder,
    CauseType,
    CauseSeverity,
    RootCause,
    RootCauseAnalyzer,
    Explanation,
    ExplainEngine,
    TraceReport,
    Anomaly,
    AnomalyReport,
    AnalysisReporter,
)
from .attribution import (
    StrategyAttribution,
    StrategyAttributionReport,
    StrategyMetric,
    SymbolAttribution,
    SymbolAttributionReport,
    SymbolMetric,
    LongShortMetric,
    TimeAttribution,
    TimeAttributionReport,
    TimeSlotMetric,
    RegimeMetric,
    RiskAttribution,
    RiskAttributionReport,
    RiskContribution,
    DrawdownContribution,
    FactorAttribution,
    FactorAttributionReport,
    FactorContribution,
    MonthlyReview,
    MonthlyReport,
    TradeSummary,
)

__all__ = [
    # Metrics
    "MetricsCollector",
    "MetricType",
    # Journal
    "TradeJournal",
    "JournalEntry",
    # Replay (legacy)
    "ReplayEngine",
    "ReplayEvent",
    # Trade Analytics
    "TradeAnalytics",
    "TradeAnalyticsReport",
    # Health
    "StrategyHealthMonitor",
    "StrategyHealth",
    "HealthStatus",
    "HealthConfig",
    "get_health_monitor",
    "set_health_monitor",
    # Timeline (legacy)
    "TimelineView",
    "TimelineEntry",
    "TraceSummary",
    # Event Store
    "EventStore",
    "StoredEvent",
    "SessionInfo",
    "get_event_store",
    "set_event_store",
    # Session
    "TradingSession",
    "SessionManager",
    "get_session_manager",
    # Timeline Service
    "TimelineService",
    "TimelineItem",
    # Replay State
    "ReplayState",
    "ReplayPosition",
    "ReplayOrder",
    # Replay Controller
    "ReplayController",
    "ReplaySnapshot",
    "ReplayStatus",
    "get_replay_controller",
    # Root Cause Analysis
    "RootCauseAnalysis",
    "TradeChain",
    # Analysis V3
    "TradeLeg",
    "TradeTrace",
    "TraceBuilder",
    "CauseType",
    "CauseSeverity",
    "RootCause",
    "RootCauseAnalyzer",
    "Explanation",
    "ExplainEngine",
    "TraceReport",
    "Anomaly",
    "AnomalyReport",
    "AnalysisReporter",
    # Attribution V4
    "StrategyAttribution",
    "StrategyAttributionReport",
    "StrategyMetric",
    "SymbolAttribution",
    "SymbolAttributionReport",
    "SymbolMetric",
    "LongShortMetric",
    "TimeAttribution",
    "TimeAttributionReport",
    "TimeSlotMetric",
    "RegimeMetric",
    "RiskAttribution",
    "RiskAttributionReport",
    "RiskContribution",
    "DrawdownContribution",
    "FactorAttribution",
    "FactorAttributionReport",
    "FactorContribution",
    "MonthlyReview",
    "MonthlyReport",
    "TradeSummary",
]

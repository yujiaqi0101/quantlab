"""
QuantLab Observe — 可观测性中心

可观测性是个人量化最缺的能力。本包提供：

  Trade Analytics        交易分析（profit_factor / expectancy / avg_win / long_short_win_rate）
  Execution Analytics    执行分析（signal/order/fill latency）
  Event Timeline         事件时间线（基于 EventTracer 聚合）
  Strategy Health        策略健康监控（24h 信号/成交/收益）
  Drift Detection        数据漂移检测（PSI / KS / mean_std）

复用现有模块：
  - execution/journal.py     Strategy Journal
  - runtime/replay.py        Replay Engine
  - analytics/attribution.py Performance Attribution
  - monitoring/dashboard.py  Monitoring Dashboard
  - execution/notification.py Notification Hub
"""

from .trade_analytics import (
    TradeAnalytics,
    TradeAnalyticsReport,
)
from .execution_analytics import (
    ExecutionAnalytics,
    ExecutionAnalyticsReport,
    LatencyRecord,
)
from .timeline import (
    TimelineView,
    TimelineEntry,
    TraceSummary,
)
from .health import (
    StrategyHealthMonitor,
    StrategyHealth,
    HealthStatus,
    HealthConfig,
    get_health_monitor,
    set_health_monitor,
)
from .drift import (
    DriftDetector,
    DriftConfig,
    DriftResult,
)

__all__ = [
    # Trade Analytics
    "TradeAnalytics",
    "TradeAnalyticsReport",
    # Execution Analytics
    "ExecutionAnalytics",
    "ExecutionAnalyticsReport",
    "LatencyRecord",
    # Timeline
    "TimelineView",
    "TimelineEntry",
    "TraceSummary",
    # Health
    "StrategyHealthMonitor",
    "StrategyHealth",
    "HealthStatus",
    "HealthConfig",
    "get_health_monitor",
    "set_health_monitor",
    # Drift
    "DriftDetector",
    "DriftConfig",
    "DriftResult",
]

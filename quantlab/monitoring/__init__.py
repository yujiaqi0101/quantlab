"""
V3.2 Monitoring 包

观测性中心
  TradeLogger       统一日志（JSON Lines）
  MetricsCollector  实时指标
  EventTracer       事件链路追踪
  AlertManager      告警规则引擎
  Dashboard         matplotlib 可视化
  SystemContext     统一入口

V2.5 兼容：LiveLogger 已迁移到 monitoring.logger
"""

from .logger import (
    TradeLogger,
    LogRecord,
    new_trace_id,
)
from .metrics import (
    MetricsCollector,
)
from .tracer import (
    EventTracer,
    Span,
)
from .alert import (
    AlertManager,
    Alert,
    AlertRule,
    PnLThresholdRule,
    DrawdownBreachRule,
    ConsecutiveLossRule,
    FillFailureRule,
    ALERT_LEVEL_INFO,
    ALERT_LEVEL_WARN,
    ALERT_LEVEL_CRITICAL,
)
from .dashboard import (
    Dashboard,
)
from .system_context import (
    SystemContext,
)


__all__ = [
    "TradeLogger",
    "LogRecord",
    "new_trace_id",
    "MetricsCollector",
    "EventTracer",
    "Span",
    "AlertManager",
    "Alert",
    "AlertRule",
    "PnLThresholdRule",
    "DrawdownBreachRule",
    "ConsecutiveLossRule",
    "FillFailureRule",
    "ALERT_LEVEL_INFO",
    "ALERT_LEVEL_WARN",
    "ALERT_LEVEL_CRITICAL",
    "Dashboard",
    "SystemContext",
]

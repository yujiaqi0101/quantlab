# Execution Layer
# 把 TargetPortfolio 转成 Order
# 不修改 Portfolio
# Order 列表交给 BarEngine 处理
#
# 拆分子模块：
# - order            : Order 数据类
# - commission       : 佣金模型
# - slippage         : 滑点模型
# - matcher          : 撮合器（TargetWeight → Orders）
# - signal_executor  : Signal → TargetPortfolio → Order
# - market           : MarketDataService 统一行情服务
# - scheduler        : 策略定时调度
# - notification     : 通知中心（Telegram/Discord/Email）
# - journal          : 交易日志

from .order import (
    Order,
)

from .commission import (
    PercentageCommission,
)

from .slippage import (
    PercentageSlippage,
)

from .matcher import (
    TargetWeightExecution,
)

from .signal_executor import (
    Signal,
    SignalSide,
    SignalExecutor,
    execute_signals,
)

from .market import (
    Bar,
    Snapshot,
    MarketDataProvider,
    BacktestProvider,
    MarketDataService,
    get_market_data_service,
    set_market_data_service,
)

from .scheduler import (
    ScheduleRule,
    ScheduledJob,
    Scheduler,
    get_scheduler,
    set_scheduler,
)

from .notification import (
    Notification,
    NotificationLevel,
    NotificationChannel,
    LogChannel,
    TelegramChannel,
    DiscordChannel,
    EmailChannel,
    NotificationCenter,
    get_notifier,
    set_notifier,
)

from .journal import (
    JournalEntry,
    JournalCategory,
    TradingJournal,
    get_journal,
    set_journal,
)


__all__ = [
    # Order / Execution
    "Order",
    "PercentageCommission",
    "PercentageSlippage",
    "TargetWeightExecution",
    # Signal
    "Signal",
    "SignalSide",
    "SignalExecutor",
    "execute_signals",
    # Market Data
    "Bar",
    "Snapshot",
    "MarketDataProvider",
    "BacktestProvider",
    "MarketDataService",
    "get_market_data_service",
    "set_market_data_service",
    # Scheduler
    "ScheduleRule",
    "ScheduledJob",
    "Scheduler",
    "get_scheduler",
    "set_scheduler",
    # Notification
    "Notification",
    "NotificationLevel",
    "NotificationChannel",
    "LogChannel",
    "TelegramChannel",
    "DiscordChannel",
    "EmailChannel",
    "NotificationCenter",
    "get_notifier",
    "set_notifier",
    # Journal
    "JournalEntry",
    "JournalCategory",
    "TradingJournal",
    "get_journal",
    "set_journal",
]

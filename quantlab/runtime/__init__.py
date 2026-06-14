"""
V3.3 + V3.4 Runtime — 可恢复 + 多策略多账户交易系统内核

V3.3：
    StateSnapshot       状态快照
    CheckpointManager   定期保存
    RecoveryManager     启动恢复
    ConsistencyChecker  对账
    ReplayEngine        重放
    ShutdownManager     优雅停机
    TradeLock           线程安全
    EventLog            事件持久化

V3.4 多策略多账户矩阵：
    Account / AccountManager  账户模型
    StrategyRuntime           独立运行单元
    StrategyRegistry          策略注册器
    AllocationEngine / Rules  策略×账户分配
    OrderRouter               订单路由
    PortfolioSupervisor       总调度器
"""

from .state_store import (
    StateSnapshot,
)
from .checkpoint import (
    CheckpointManager,
)
from .recovery import (
    RecoveryManager,
)
from .consistency import (
    ConsistencyChecker,
    ConsistencyIssue,
)
from .replay import (
    ReplayEngine,
    ReplayResult,
)
from .shutdown import (
    ShutdownManager,
)
from .thread_safety import (
    TradeLock,
    critical,
)
from .event_durability import (
    EventLog,
)

# V3.4
from .account_manager import (
    Account,
    AccountManager,
)
from .allocation import (
    AllocationRule,
    FixedAllocation,
    DynamicAllocation,
    AllocationEngine,
)
from .router import (
    OrderRouter,
    RoutedOrder,
)
from .strategy_runtime import (
    StrategyRuntime,
    RuntimeStats,
)
from .supervisor import (
    StrategyRegistry,
    PortfolioSupervisor,
)


__all__ = [
    # V3.3
    "StateSnapshot",
    "CheckpointManager",
    "RecoveryManager",
    "ConsistencyChecker",
    "ConsistencyIssue",
    "ReplayEngine",
    "ReplayResult",
    "ShutdownManager",
    "TradeLock",
    "critical",
    "EventLog",
    # V3.4
    "Account",
    "AccountManager",
    "AllocationRule",
    "FixedAllocation",
    "DynamicAllocation",
    "AllocationEngine",
    "OrderRouter",
    "RoutedOrder",
    "StrategyRuntime",
    "RuntimeStats",
    "StrategyRegistry",
    "PortfolioSupervisor",
]

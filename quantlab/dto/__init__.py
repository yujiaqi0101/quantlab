"""
V4.0 Application Layer — DTO（Data Transfer Object）

职责：
  - 统一 API / CLI / Web 三端的数据格式
  - 与底层 dataclass 解耦（DTO 面向传输，不绑定实现）
  - 都用 @dataclass，可直接 .to_dict() / from_dict()

包结构：
  common       分页、通用响应包装
  task         任务模型（Task / TaskStatus / TaskType）
  strategy     策略元信息
  backtest     回测请求 / 响应 / 指标
  optimizer    优化请求 / 响应 / 方法
  experiment   实验摘要 / 详情
  portfolio    账户 / 持仓 / 概览
  runtime      实盘启停
  monitor      日志 / 告警 / 指标快照
"""

from .common import (
    PageRequest,
    PageResponse,
    ErrorResponse,
)
from .task import (
    Task,
    TaskStatus,
    TaskType,
    new_task,
)
from .strategy import (
    StrategyInfo,
    StrategyParam,
)
from .backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestMetrics,
)
from .optimizer import (
    OptimizerRequest,
    OptimizerResponse,
    OptimizerResultRow,
    OptimizerMethod,
)
from .experiment import (
    ExperimentSummary,
    ExperimentDetail,
)
from .portfolio import (
    AccountInfo,
    PositionInfo,
    PortfolioSummary,
)
from .runtime import (
    StartStrategyRequest,
    RuntimeStatus,
)
from .monitor import (
    LogEntry,
    AlertInfo,
    MetricsSnapshot,
)


__all__ = [
    "PageRequest",
    "PageResponse",
    "ErrorResponse",
    "Task",
    "TaskStatus",
    "TaskType",
    "new_task",
    "StrategyInfo",
    "StrategyParam",
    "BacktestRequest",
    "BacktestResponse",
    "BacktestMetrics",
    "OptimizerRequest",
    "OptimizerResponse",
    "OptimizerResultRow",
    "OptimizerMethod",
    "ExperimentSummary",
    "ExperimentDetail",
    "AccountInfo",
    "PositionInfo",
    "PortfolioSummary",
    "StartStrategyRequest",
    "RuntimeStatus",
    "LogEntry",
    "AlertInfo",
    "MetricsSnapshot",
]

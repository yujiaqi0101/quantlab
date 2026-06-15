"""
V4.0 Application Layer — Domain（领域模型）

Domain 层是整个系统的"中立语言"：
  - 不依赖 application / api / dto
  - 不依赖任何具体 engine / broker / storage
  - 上层（Service、API、DTO）全部依赖它

它回答一个问题：
  "这个系统里有哪几种核心对象？"
  Task
  Experiment
  StrategyDefinition
  RuntimeInstance
  Account
  PortfolioSnapshot
  BacktestJob
  OptimizerJob

**顺序**：Domain → DTO → Service → API

文件：
  task        异步任务（状态机 PENDING/RUNNING/SUCCESS/FAILED/CANCELLED）
  strategy    策略定义（前端用它自动生成表单）
  experiment  实验 vs 实验结果（两个独立对象）
  backtest    回测任务规格
  optimizer   优化任务规格 + 试验
  runtime     实盘运行实例
  account     账户
  portfolio   持仓快照
"""

from .task import (
    Task,
    TaskStatus,
    TaskType,
    new_task,
    now_iso,
)
from .strategy import (
    StrategyDefinition,
    ParamSchema,
    make_ma_cross_definition,
    make_rsi_definition,
)
from .experiment import (
    Experiment,
    ExperimentResult,
    ExperimentSummary,
    ExperimentDetail,
    summary_from,
)
from .backtest import (
    BacktestSpec,
    BacktestJob,
)
from .optimizer import (
    OptimizerSpec,
    OptimizerJob,
    OptimizerTrial,
    OptimizerMethod,
    BacktestSpecTemplate,
)
from .runtime import (
    RuntimeInstance,
    RuntimeState,
    StartStrategySpec,
)
from .account import (
    Account,
    Position,
)
from .portfolio import (
    PortfolioSnapshot,
    PortfolioSummary,
)


__all__ = [
    # task
    "Task",
    "TaskStatus",
    "TaskType",
    "new_task",
    "now_iso",
    # strategy
    "StrategyDefinition",
    "ParamSchema",
    "make_ma_cross_definition",
    "make_rsi_definition",
    # experiment
    "Experiment",
    "ExperimentResult",
    "ExperimentSummary",
    "ExperimentDetail",
    "summary_from",
    # backtest
    "BacktestSpec",
    "BacktestJob",
    # optimizer
    "OptimizerSpec",
    "OptimizerJob",
    "OptimizerTrial",
    "OptimizerMethod",
    "BacktestSpecTemplate",
    # runtime
    "RuntimeInstance",
    "RuntimeState",
    "StartStrategySpec",
    # account
    "Account",
    "Position",
    # portfolio
    "PortfolioSnapshot",
    "PortfolioSummary",
]

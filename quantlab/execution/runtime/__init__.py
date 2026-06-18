"""
Runtime Engine — 运行时引擎

T1 第七模块：系统主循环

  加载策略 → 订阅行情 → 产生信号 → 发送订单 → 更新持仓

统一入口：
    from quantlab.execution.runtime import Runtime, start

    runtime = start(strategy=my_strategy)
    runtime.stop()
"""

from .engine import ProductionRuntime, RuntimeConfig, RuntimeState
from .strategy_runner import StrategyRunner, StrategyConfig, RunnerState
from .scheduler import Scheduler, ScheduledTask
from .entry import Runtime, start, stop, get_runtime

__all__ = [
    # Engine
    "ProductionRuntime",
    "RuntimeConfig",
    "RuntimeState",
    # Strategy Runner
    "StrategyRunner",
    "StrategyConfig",
    "RunnerState",
    # Scheduler
    "Scheduler",
    "ScheduledTask",
    # 统一入口
    "Runtime",
    "start",
    "stop",
    "get_runtime",
]

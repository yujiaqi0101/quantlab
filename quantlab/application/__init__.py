"""
V4.0 Application Layer — Service 业务服务层

包结构：
  strategy_service      策略注册 / 列表 / 元信息
  backtest_service      异步回测（封装 BarEngine + Experiment）
  optimizer_service     参数优化（Grid / Random / Parallel / Bayesian）
  experiment_service    实验查询 / 详情 / leaderboard
  runtime_service       实盘启停 / 状态
  portfolio_service     多账户 / 持仓 / 暴露
  monitor_service       日志 / 告警 / 指标快照

为什么需要：
  - 前端不应直接调 Engine / Optimizer / WalkForward
  - Service 是统一入口，对应一条业务用例
  - 每个 Service 持有 TaskManager / Tracker / Supervisor 等基础设施
  - 业务逻辑写在这里，DTO 来回传，API/CLI/Web 三端共享
"""

from .backtest_service import BacktestService


__all__ = [
    "BacktestService",
]

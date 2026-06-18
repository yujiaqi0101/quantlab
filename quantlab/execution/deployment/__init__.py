"""
Deployment Manager — 部署管理器

T1 第八模块：Research → Deploy 闭环

前端 "Deploy Strategy" 按钮的后端逻辑

  1. 接收部署请求
  2. 启动 Runtime
  3. 启动 Scheduler
  4. 启动 Broker
  5. 加载策略
  6. 返回部署状态

用法：
    from quantlab.execution.deployment import DeploymentManager, DeployRequest

    manager = DeploymentManager()
    result = manager.deploy(DeployRequest(
        strategy_id="rsi",
        symbols=["BTCUSDT"],
        initial_capital=100000,
    ))
"""

from .manager import DeploymentManager, DeployRequest, DeployResult, DeployStatus

__all__ = [
    "DeploymentManager",
    "DeployRequest",
    "DeployResult",
    "DeployStatus",
]

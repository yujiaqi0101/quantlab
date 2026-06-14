"""
BaseExecution：Execution 层统一接口

V3.1 重构核心：
  之前 Execution 散在：
    - execution/matcher.py:TargetWeightExecution
    - engine/tick_engine.py:LiveEngine._on_tick
    - live/live_engine.py:LiveEngine._on_tick
  业务上看都是同一件事：TargetPortfolio → Order → Fill

新接口：
  submit(target_portfolio) -> List[Order]
      给一批目标权重，返回本轮下出的 Order
      Backtest 模式是同步，Paper/Live 模式也是同步调用 broker.submit_order
  drain_fills() -> List[Fill]
      拉取本轮新成交
      Backtest 模式：submit 内已同步成交，drain 返回空
      Paper/Live 模式：从 broker 拉新 Fill
  on_fill(callback)
      注册成交回报（LiveEngine 用）

为什么是 ABC 而不是 Protocol：
  - 子类都有 position_tolerance / commission / slippage 等共同参数
  - 工厂方法 ExecutionFactory.create(mode=...) 需要明确的 type
"""

from abc import ABC, abstractmethod
from typing import Callable, List, Optional

from ...core.fill import Fill
from ...core.order import Order
from ...portfolio_construction.target_portfolio import (
    TargetPortfolio,
)


class BaseExecution(ABC):
    """
    策略调用方只看到这一个接口
    内部可走 Backtest / Paper / Live 任意一种
    """

    name: str = "BASE"

    @abstractmethod
    def submit(
        self,
        target_portfolio: TargetPortfolio,
    ) -> List[Order]:
        """
        给一批目标权重，产出本轮 Order 列表
        返回 [] 表示本轮无调仓
        """
        ...

    def drain_fills(self) -> List[Fill]:
        """
        拉取本轮新成交
        V3.1 默认返回空（Backtest 模式 submit 内部已成交）
        """
        return []

    def on_fill(
        self,
        callback: Optional[Callable],
    ) -> None:
        """
        注册成交回报（仅 Paper/Live 有意义）
        """
        self._fill_callback = callback

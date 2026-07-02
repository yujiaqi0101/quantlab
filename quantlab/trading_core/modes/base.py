"""
交易模式抽象基类 (TradingMode)
=============================

定义三模式（Backtest/Paper/Live）的统一抽象：
    - create_broker()   创建该模式对应的 Broker
    - on_post_bar()     每根K线处理完成后的模式特定后处理
    - name              模式名称

唯一变化：数据来源（DataFeed）和 Broker 类型。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from quantlab.execution.broker.base import Broker

if TYPE_CHECKING:
    # 避免循环导入，仅用于类型提示
    from quantlab.trading_core.core import TradingCore
    from quantlab.trading_core.interfaces import Bar

__all__ = ["TradingMode"]


class TradingMode(ABC):
    """交易模式抽象基类。

    子类必须实现：
        - create_broker(initial_capital) -> Broker
        - on_post_bar(bar, core) -> None
        - name (property)
    """

    @abstractmethod
    def create_broker(self, initial_capital: float) -> Broker:
        """创建该模式对应的 Broker 实例。

        Args:
            initial_capital: 初始资金

        Returns:
            Broker 实例
        """
        ...

    @abstractmethod
    def on_post_bar(self, bar: "Bar", core: "TradingCore") -> None:
        """每根K线处理完成后的模式特定后处理。

        在 TradingCore.on_bar 完成策略调用和订单提交后调用。
        例如：PaperMode 可在此持久化状态，BacktestMode 通常为空。

        Args:
            bar: 当前K线
            core: TradingCore 实例
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """模式名称（如 'backtest' / 'paper' / 'live'）。"""
        ...

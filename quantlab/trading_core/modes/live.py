"""
LiveMode — 实盘模式
==================

实时行情 + 真实券商。

特点：
    - 数据来源：实时行情（券商API）
    - Broker：真实券商接口（当前占位为 PaperBroker，后续接入）
    - 真实资金、真实成交

注意：
    当前为骨架实现，create_broker 暂时返回 PaperBroker 占位。
    后续接入真实券商时，替换为对应的 Broker 实现。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from quantlab.execution.broker.base import Broker
from quantlab.execution.broker.paper import PaperBroker

from .base import TradingMode

if TYPE_CHECKING:
    from quantlab.trading_core.core import TradingCore
    from quantlab.trading_core.interfaces import Bar

__all__ = ["LiveMode"]


class LiveMode(TradingMode):
    """实盘模式：实时行情 + 真实券商（当前占位）。"""

    def __init__(
        self,
        fee_rate: float = 0.0003,
        slippage_rate: float = 0.0005,
    ) -> None:
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def create_broker(self, initial_capital: float) -> Broker:
        """创建 Broker（占位：暂用 PaperBroker，后续接真实券商）。

        TODO: 后续接入 BinanceBroker / IBBroker / QMTBroker 等。
        """
        # 占位实现：真实场景下此处应返回真实券商 Broker
        return PaperBroker(
            initial_capital=initial_capital,
            fee_rate=self.fee_rate,
            slippage_rate=self.slippage_rate,
        )

    def on_post_bar(self, bar: "Bar", core: "TradingCore") -> None:
        """实盘后处理（空实现，后续扩展持久化/报告）。"""
        return None

    @property
    def name(self) -> str:
        return "live"

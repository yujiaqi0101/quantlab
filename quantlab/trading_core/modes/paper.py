"""
PaperMode — 模拟交易模式
=======================

实时行情 + PaperBroker 模拟撮合。

特点：
    - 数据来源：实时行情（QMT/东财/WebSocket）
    - Broker：PaperBroker（模拟成交，支持部分成交/排队/滑点）
    - 实时运行、不可重复、有真实行情延迟
    - on_post_bar 预留持久化扩展点（当前空实现）

用法：
    mode = PaperMode()
    core = TradingCore(mode, initial_capital=1_000_000)
    # 由实时行情源逐个推送 bar
    core.on_bar(bar)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from quantlab.execution.broker.base import Broker
from quantlab.execution.broker.paper import PaperBroker

from .base import TradingMode

if TYPE_CHECKING:
    from quantlab.trading_core.core import TradingCore
    from quantlab.trading_core.interfaces import Bar

__all__ = ["PaperMode"]


class PaperMode(TradingMode):
    """模拟交易模式：实时行情 + PaperBroker 模拟撮合。"""

    def __init__(
        self,
        fee_rate: float = 0.0003,        # 0.03%
        slippage_rate: float = 0.001,    # 0.1%（实时滑点略大）
    ) -> None:
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def create_broker(self, initial_capital: float) -> Broker:
        """创建 PaperBroker（模拟撮合）。"""
        return PaperBroker(
            initial_capital=initial_capital,
            fee_rate=self.fee_rate,
            slippage_rate=self.slippage_rate,
        )

    def on_post_bar(self, bar: "Bar", core: "TradingCore") -> None:
        """模式特定后处理（预留持久化扩展点，当前空实现）。

        后续可在此处：
            - 持久化账户/持仓/订单状态到数据库
            - 生成报告
            - 触发通知
        """
        return None

    @property
    def name(self) -> str:
        return "paper"

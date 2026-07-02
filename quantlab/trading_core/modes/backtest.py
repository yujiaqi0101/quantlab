"""
BacktestMode — 回测模式
======================

历史数据驱动 + PaperBroker 即时撮合。

特点：
    - 数据来源：历史K线（从文件/数据库读取，由外部逐个推送）
    - Broker：PaperBroker（即时成交，支持滑点模型）
    - 可快进、可重复、无网络延迟
    - on_post_bar 为空（回测不需要持久化）

用法：
    mode = BacktestMode()
    core = TradingCore(mode, initial_capital=1_000_000)
    mode.run_history(core, bars)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from quantlab.execution.broker.base import Broker
from quantlab.execution.broker.paper import PaperBroker

from .base import TradingMode

if TYPE_CHECKING:
    from quantlab.trading_core.core import TradingCore
    from quantlab.trading_core.interfaces import Bar

__all__ = ["BacktestMode"]


class BacktestMode(TradingMode):
    """回测模式：历史数据驱动 + PaperBroker 即时撮合。"""

    def __init__(
        self,
        fee_rate: float = 0.0003,        # 0.03%
        slippage_rate: float = 0.0005,   # 0.05%
    ) -> None:
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

    def create_broker(self, initial_capital: float) -> Broker:
        """创建 PaperBroker（回测即时撮合）。"""
        return PaperBroker(
            initial_capital=initial_capital,
            fee_rate=self.fee_rate,
            slippage_rate=self.slippage_rate,
        )

    def on_post_bar(self, bar: "Bar", core: "TradingCore") -> None:
        """回测不需要后处理（无持久化）。"""
        return None

    @property
    def name(self) -> str:
        return "backtest"

    def run_history(self, core: "TradingCore", bars: List["Bar"]) -> None:
        """遍历历史K线，逐个驱动 TradingCore.on_bar。

        Args:
            core: TradingCore 实例
            bars: 历史K线列表（按时间升序）
        """
        for bar in bars:
            core.on_bar(bar)

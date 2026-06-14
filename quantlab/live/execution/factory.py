"""
ExecutionFactory：Paper / Backtest / Live 一键切换

V3.1 核心设计：
    execution = ExecutionFactory.create(
        mode="backtest",       # or "paper" / "live"
        portfolio=portfolio,
        broker=paper_broker,   # paper / live 模式必填
    )

策略代码完全不变，只换 mode。
"""

from typing import Optional

from ..broker.base import BrokerAdapter
from .base import BaseExecution
from .backtest_execution import BacktestExecution
from .paper_execution import PaperExecution
from .live_execution import LiveExecution


class ExecutionFactory:
    """
    工厂方法

    用法：
        # Backtest
        exec = ExecutionFactory.create(
            mode="backtest",
            portfolio=portfolio,
        )

        # Paper
        exec = ExecutionFactory.create(
            mode="paper",
            portfolio=portfolio,
            broker=paper_broker,
        )

        # Live
        exec = ExecutionFactory.create(
            mode="live",
            portfolio=portfolio,
            broker=ibkr_broker,
        )
    """

    MODES = ("backtest", "paper", "live")

    @staticmethod
    def create(
        mode: str,
        portfolio,
        broker: Optional[BrokerAdapter] = None,
        **kwargs,
    ) -> BaseExecution:
        mode = mode.lower()
        if mode not in ExecutionFactory.MODES:
            raise ValueError(
                f"mode must be one of {ExecutionFactory.MODES}, "
                f"got {mode!r}"
            )

        if mode == "backtest":
            return BacktestExecution(
                portfolio=portfolio,
                **kwargs,
            )
        if mode == "paper":
            if broker is None:
                raise ValueError(
                    "mode='paper' requires a broker (PaperBroker)"
                )
            return PaperExecution(
                portfolio=portfolio,
                broker=broker,
                **kwargs,
            )
        if mode == "live":
            if broker is None:
                raise ValueError(
                    "mode='live' requires a broker "
                    "(IBKRBroker / BinanceBroker)"
                )
            return LiveExecution(
                portfolio=portfolio,
                broker=broker,
                **kwargs,
            )

        # 不可能到这里
        raise ValueError(f"unreachable mode: {mode}")

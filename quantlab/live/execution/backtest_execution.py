"""
BacktestExecution：回测专用 Execution

V3.1：
  内部走 execution/matcher.py:TargetWeightExecution
  同步撮合：每根 bar 一次性撮合，返回 Order 列表
  Apply：引擎按 Order 直接 modify Portfolio + 生成 Fill
  同步 publish OrderEvent / FillEvent 到 EventBus
"""

from typing import List

from ...core.fill import Fill
from ...core.order import Order
from ...event.event_bus import event_bus
from ...event.event_types import FillEvent, OrderEvent
from ...execution.commission import PercentageCommission
from ...execution.matcher import TargetWeightExecution
from ...execution.slippage import PercentageSlippage
from ...portfolio_construction.target_portfolio import (
    TargetPortfolio,
)
from .base import BaseExecution


class BacktestExecution(BaseExecution):
    """
    Backtest 模式 Execution

    用法（Engine 内部）：
        exec = BacktestExecution(
            portfolio=portfolio,
            lot_size=1,
            commission=PercentageCommission(0.0003),
            slippage=PercentageSlippage(0.0002),
        )
        orders = exec.submit(target_portfolio)
        # Engine 拿 orders 直接撮合 → Fill → Portfolio
    """

    name = "BACKTEST"

    def __init__(
        self,
        portfolio,                    # Portfolio 实例
        lot_size: int = 1,
        position_tolerance: float = 0.02,
        commission: PercentageCommission = None,
        slippage: PercentageSlippage = None,
    ):
        self.portfolio = portfolio
        self.matcher = TargetWeightExecution(
            lot_size=lot_size,
            position_tolerance=position_tolerance,
        )
        self.commission = commission or PercentageCommission(0.0003)
        self.slippage = slippage or PercentageSlippage(0.0002)
        self._order_seq = 0

    def submit(
        self,
        target_portfolio: TargetPortfolio,
    ) -> List[Order]:
        # 1) 撮合：target → orders
        prices = {
            sym: self.portfolio.last_prices.get(sym, 0.0)
            for sym in self.portfolio.last_prices
        }
        if not prices:
            # 没价（首次）→ 拿不到价格 → 跳过
            return []

        raw_orders = self.matcher.generate_orders(
            portfolio=self.portfolio,
            target_portfolio=target_portfolio,
            prices=prices,
        )

        # 2) 填 id / price / status
        enriched: List[Order] = []
        for o in raw_orders:
            self._order_seq += 1
            # V3.1：构造新 Order（避免 slots=True 与 dataclasses.replace 冲突）
            o2 = Order(
                symbol=o.symbol,
                quantity=o.quantity,
                id=f"B{self._order_seq:06d}",
                side=o.side,
                price=prices.get(o.symbol),
                order_type="MARKET",
                status="NEW",
            )
            enriched.append(o2)

        # 3) publish OrderEvent
        for o in enriched:
            event_bus.publish(OrderEvent(
                type="ORDER",
                timestamp=target_portfolio.timestamp,
                symbol=o.symbol,
                quantity=o.quantity,
            ))

        return enriched

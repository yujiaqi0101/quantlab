"""
LiveExecution：真实交易所 Execution

V3.1：接口完整，依赖 IBKR / Binance broker 实现真实成交
       V3.1 阶段因为 broker 是 stub，LiveExecution 等价于 NotImplemented

设计上与 PaperExecution 一致：
  submit() → broker.submit_order()        fire-and-forget
  drain_fills() → broker 异步回报拉取      这里只能先 fall back 到 broker.trade_log

V3.1 实现：
  - submit 直接下到 broker.submit_order（broker 内部抛 NotImplementedError 是预期的）
  - drain_fills 沿用 Paper 模式，等真实 broker 完成后切换
"""

from typing import List

from ...core.fill import Fill
from ...core.order import Order
from ...event.event_bus import event_bus
from ...event.event_types import OrderEvent
from ...execution.matcher import TargetWeightExecution
from ...portfolio_construction.target_portfolio import (
    TargetPortfolio,
)
from ..broker.base import BrokerAdapter
from .base import BaseExecution


class LiveExecution(BaseExecution):
    """
    Live 模式 Execution

    与 PaperExecution 的唯一区别：
        broker 可能是 IBKR / Binance 等真实交易所
    """

    name = "LIVE"

    def __init__(
        self,
        portfolio,
        broker: BrokerAdapter,
        lot_size: int = 1,
        position_tolerance: float = 0.02,
    ):
        self.portfolio = portfolio
        self.broker = broker
        self.matcher = TargetWeightExecution(
            lot_size=lot_size,
            position_tolerance=position_tolerance,
        )
        self._order_seq = 0

    def submit(
        self,
        target_portfolio: TargetPortfolio,
    ) -> List[Order]:
        prices = {
            sym: self.portfolio.last_prices.get(sym, 0.0)
            for sym in self.portfolio.last_prices
        }
        if not prices:
            return []

        raw_orders = self.matcher.generate_orders(
            portfolio=self.portfolio,
            target_portfolio=target_portfolio,
            prices=prices,
        )

        enriched: List[Order] = []
        for o in raw_orders:
            self._order_seq += 1
            o2 = Order(
                symbol=o.symbol,
                quantity=o.quantity,
                id=f"L{self._order_seq:06d}",
                side=o.side,
                price=prices.get(o.symbol),
                order_type="MARKET",
                status="NEW",
            )
            enriched.append(o2)
            # 真实 broker 提交（V3.1 broker 内部抛 NotImplementedError）
            self.broker.submit_order(o2)

            event_bus.publish(OrderEvent(
                type="ORDER",
                timestamp=target_portfolio.timestamp,
                symbol=o2.symbol,
                quantity=o2.quantity,
            ))

        return enriched

    def drain_fills(self) -> List[Fill]:
        # V3.1 stub：等真实 broker 异步回报
        # 当前先尝试从 broker.trade_log 拉
        if hasattr(self.broker, "trade_log"):
            fills = list(self.broker.trade_log)
            self.broker.trade_log.clear()
            return fills
        return []

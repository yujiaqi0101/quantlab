"""
PaperExecution：Paper 模式 Execution

V3.1：
  1) submit(target) → matcher 产 Order 列表
  2) 每条 Order 转给 PaperBroker.submit_order
  3) PaperBroker 同步生成 Fill，立即回调
  4) 拉新 Fill（drain_fills）→ 更新 Portfolio
  5) 全部 publish 到 EventBus

与 BacktestExecution 的区别：
  Backtest   submit 内部已成交
  Paper      submit 只下到 broker，drain 拉新成交（这里 V3.1 简化为同步）

V3.1 简化：drain_fills 直接从 broker.trade_log 拉
            （未来 LiveExecution 要换成异步回调）
"""

from dataclasses import dataclass
from typing import List

from ...core.fill import Fill
from ...core.order import Order
from ...event.event_bus import event_bus
from ...event.event_types import FillEvent, OrderEvent
from ...execution.matcher import TargetWeightExecution
from ...portfolio_construction.target_portfolio import (
    TargetPortfolio,
)
from ..broker.paper_broker import PaperBroker
from .base import BaseExecution


class PaperExecution(BaseExecution):
    """
    Paper 模式 Execution

    用法：
        broker = PaperBroker(market_data=md, tick_size=0.01)
        broker.connect()
        exec = PaperExecution(portfolio=portfolio, broker=broker)
        orders = exec.submit(target)
        fills = exec.drain_fills()    # 同步从 broker 拉
    """

    name = "PAPER"

    def __init__(
        self,
        portfolio,
        broker: PaperBroker,
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
        self._last_fills: List[Fill] = []

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
                id=f"B{self._order_seq:06d}",
                side=o.side,
                price=prices.get(o.symbol),
                order_type="MARKET",
                status="NEW",
            )
            enriched.append(o2)
            # 直接下到 broker
            self.broker.submit_order(o2)

            event_bus.publish(OrderEvent(
                type="ORDER",
                timestamp=target_portfolio.timestamp,
                symbol=o2.symbol,
                quantity=o2.quantity,
            ))

        return enriched

    def drain_fills(self) -> List[Fill]:
        """
        从 PaperBroker.trade_log 拉新成交
        清空已处理的（与 LiveEngine 旧逻辑一致）
        """
        if not hasattr(self.broker, "trade_log"):
            return []

        fills = list(self.broker.trade_log)
        self.broker.trade_log.clear()
        return fills

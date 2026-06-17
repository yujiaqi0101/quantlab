"""
Rebalance Engine — 动态调仓引擎

根据 Capital Allocator 的分配结果
动态调整各策略的资金权重
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

from .allocator import CapitalAllocator, StrategyAllocation
from .portfolio import CapitalPortfolio

logger = logging.getLogger("quantlab.execution.capital.rebalance")


@dataclass
class RebalanceOrder:
    """调仓指令"""
    strategy_id: str
    symbol: str
    target_qty: float
    current_qty: float
    delta_qty: float
    reason: str = ""

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "target_qty": self.target_qty,
            "current_qty": self.current_qty,
            "delta_qty": self.delta_qty,
            "reason": self.reason,
        }


class RebalanceEngine:
    """
    动态调仓引擎

    用法：
        engine = RebalanceEngine(
            allocator=allocator,
            portfolio=portfolio,
        )
        orders = engine.compute_rebalance(prices={"BTCUSDT": 50000})
        for order in orders:
            if abs(order.delta_qty) > 0:
                execute(order)
    """

    def __init__(
        self,
        allocator: CapitalAllocator,
        portfolio: CapitalPortfolio,
    ) -> None:
        self.allocator = allocator
        self.portfolio = portfolio

    def compute_rebalance(
        self,
        target_weights: Dict[str, Dict[str, float]],
        prices: Dict[str, float],
    ) -> List[RebalanceOrder]:
        """
        计算调仓指令

        参数：
          target_weights: {strategy_id: {symbol: weight}}
          prices: {symbol: price}
        """
        orders: List[RebalanceOrder] = []
        allocations = self.allocator.get_all_allocations()

        for strategy_id, weights in target_weights.items():
            alloc = allocations.get(strategy_id)
            if not alloc or not alloc.active:
                continue

            strategy_capital = alloc.capital

            for symbol, weight in weights.items():
                price = prices.get(symbol, 0)
                if price <= 0:
                    continue

                target_qty = (strategy_capital * weight) / price
                current_qty = self.portfolio.positions.get(symbol, None)
                current_qty = current_qty.qty if current_qty else 0.0

                delta = target_qty - current_qty

                if abs(delta) > 0.0001:
                    orders.append(RebalanceOrder(
                        strategy_id=strategy_id,
                        symbol=symbol,
                        target_qty=target_qty,
                        current_qty=current_qty,
                        delta_qty=delta,
                        reason=f"rebalance: weight={weight:.4f}",
                    ))

        logger.info(
            f"Rebalance: {len(orders)} orders computed "
            f"across {len(target_weights)} strategies"
        )
        return orders

    def execute_rebalance(
        self,
        orders: List[RebalanceOrder],
        execute_fn=None,
    ) -> int:
        """执行调仓指令"""
        executed = 0
        for order in orders:
            if abs(order.delta_qty) < 0.0001:
                continue
            if execute_fn:
                try:
                    execute_fn(order)
                    executed += 1
                except Exception as e:
                    logger.error(f"Rebalance execute failed: {order.symbol}: {e}")
            else:
                executed += 1
        logger.info(f"Rebalance executed: {executed}/{len(orders)}")
        return executed

"""
Paper Broker 升级 — 真实行为模拟

升级内容：
  1. Slippage Model（已有，集成）
  2. Partial Fill（部分成交）
  3. Queue Position（排队成交）
  4. 市场冲击模型

Paper ≈ Live
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..core.fills.slippage_model import (
    SlippageModel,
    FixedSlippage,
    PercentageSlippage,
)
from ..core.oms.order import OMSOrder, OrderSide, OrderType, OrderState

logger = logging.getLogger("quantlab.execution.paper.upgraded_broker")


@dataclass
class PartialFillConfig:
    """部分成交配置"""
    enabled: bool = True
    min_fill_pct: float = 0.1          # 最小成交比例
    max_fill_pct: float = 0.9          # 单次最大成交比例
    fill_probability: float = 0.7      # 每次成交概率
    fill_interval_ms: int = 100         # 成交间隔


@dataclass
class QueuePositionConfig:
    """排队成交配置"""
    enabled: bool = True
    base_queue_size: int = 100          # 基础排队量
    queue_decay: float = 0.1            # 每tick队列减少比例


@dataclass
class PaperFillResult:
    """Paper 成交结果"""
    order_id: str
    symbol: str
    side: str
    fill_qty: float
    fill_price: float
    remaining_qty: float
    is_complete: bool
    timestamp: int
    queue_position: int = 0
    slippage: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "fill_qty": self.fill_qty,
            "fill_price": self.fill_price,
            "remaining_qty": self.remaining_qty,
            "is_complete": self.is_complete,
            "timestamp": self.timestamp,
            "queue_position": self.queue_position,
            "slippage": self.slippage,
        }


class UpgradedPaperBroker:
    """
    升级版 Paper Broker

    用法：
        broker = UpgradedPaperBroker(
            slippage_model=PercentageSlippage(rate=0.001),
            partial_fill_config=PartialFillConfig(),
            queue_config=QueuePositionConfig(),
        )
        result = broker.submit_order(order, market_price=50000, volume=1000000)
    """

    def __init__(
        self,
        slippage_model: SlippageModel = None,
        partial_fill_config: PartialFillConfig = None,
        queue_config: QueuePositionConfig = None,
        commission_rate: float = 0.0004,
    ) -> None:
        self.slippage_model = slippage_model or PercentageSlippage(rate=0.0005)
        self.partial_config = partial_fill_config or PartialFillConfig()
        self.queue_config = queue_config or QueuePositionConfig()
        self.commission_rate = commission_rate

        self._pending_orders: Dict[str, OMSOrder] = {}  # 等待部分成交
        self._queue_positions: Dict[str, int] = {}       # order_id → queue
        self._fill_history: List[PaperFillResult] = []

    def submit_order(
        self,
        order: OMSOrder,
        market_price: float,
        volume: float = 0,
        bid: float = 0,
        ask: float = 0,
    ) -> PaperFillResult:
        """提交订单"""
        if not bid:
            bid = market_price
        if not ask:
            ask = market_price

        # 计算滑点
        slippage = self.slippage_model.calculate(
            order=order,
            market_price=market_price,
            bid=bid,
            ask=ask,
            volume=volume,
        )

        # 基础成交价
        if order.side == OrderSide.BUY:
            base_price = ask + slippage
        else:
            base_price = bid - slippage

        # 限价单检查
        if order.order_type == OrderType.LIMIT and order.price:
            if order.side == OrderSide.BUY and base_price > order.price:
                base_price = order.price
            elif order.side == OrderSide.SELL and base_price < order.price:
                base_price = order.price

        # 排队位置
        queue_pos = 0
        if self.queue_config.enabled and order.order_type == OrderType.LIMIT:
            queue_pos = random.randint(0, self.queue_config.base_queue_size)
            self._queue_positions[order.id] = queue_pos

        # 部分成交
        if self.partial_config.enabled and order.quantity > 1:
            return self._partial_fill(order, base_price, slippage, queue_pos)
        else:
            # 全部成交
            result = PaperFillResult(
                order_id=order.id,
                symbol=order.symbol,
                side=order.side.value,
                fill_qty=order.quantity,
                fill_price=base_price,
                remaining_qty=0,
                is_complete=True,
                timestamp=int(time.time() * 1000),
                queue_position=queue_pos,
                slippage=slippage,
            )
            self._fill_history.append(result)
            return result

    def _partial_fill(
        self,
        order: OMSOrder,
        base_price: float,
        slippage: float,
        queue_pos: int,
    ) -> PaperFillResult:
        """部分成交模拟"""
        remaining = order.quantity - order.filled_qty

        # 如果有排队位置，先减少排队
        if queue_pos > 0:
            queue_pos = max(0, queue_pos - int(self.queue_config.base_queue_size * self.queue_config.queue_decay))
            self._queue_positions[order.id] = queue_pos
            if queue_pos > 0:
                # 还在排队，不成交
                return PaperFillResult(
                    order_id=order.id,
                    symbol=order.symbol,
                    side=order.side.value,
                    fill_qty=0,
                    fill_price=base_price,
                    remaining_qty=remaining,
                    is_complete=False,
                    timestamp=int(time.time() * 1000),
                    queue_position=queue_pos,
                    slippage=slippage,
                )

        # 计算本次成交量
        fill_pct = random.uniform(
            self.partial_config.min_fill_pct,
            self.partial_config.max_fill_pct,
        )
        fill_qty = remaining * fill_pct

        # 取整
        if fill_qty < 1:
            fill_qty = remaining if random.random() < self.partial_config.fill_probability else 0

        is_complete = (order.filled_qty + fill_qty) >= order.quantity

        result = PaperFillResult(
            order_id=order.id,
            symbol=order.symbol,
            side=order.side.value,
            fill_qty=fill_qty,
            fill_price=base_price,
            remaining_qty=remaining - fill_qty,
            is_complete=is_complete,
            timestamp=int(time.time() * 1000),
            queue_position=queue_pos,
            slippage=slippage,
        )
        self._fill_history.append(result)

        if not is_complete:
            self._pending_orders[order.id] = order

        return result

    def process_pending(
        self,
        market_price: float,
        bid: float = 0,
        ask: float = 0,
    ) -> List[PaperFillResult]:
        """处理待成交订单（模拟后续成交）"""
        results = []
        completed = []

        for order_id, order in self._pending_orders.items():
            if order.filled_qty >= order.quantity:
                completed.append(order_id)
                continue

            result = self.submit_order(
                order=order,
                market_price=market_price,
                bid=bid,
                ask=ask,
            )
            results.append(result)

            if result.is_complete:
                completed.append(order_id)

        for oid in completed:
            self._pending_orders.pop(oid, None)

        return results

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        if order_id in self._pending_orders:
            self._pending_orders.pop(order_id)
            self._queue_positions.pop(order_id, None)
            return True
        return False

    def get_pending_orders(self) -> List[str]:
        return list(self._pending_orders.keys())

    def get_fill_history(self, limit: int = 100) -> List[PaperFillResult]:
        return self._fill_history[-limit:]

    def get_commission(self, fill_qty: float, fill_price: float) -> float:
        """计算手续费"""
        return fill_qty * fill_price * self.commission_rate

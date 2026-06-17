"""
Matching Engine — 撮合引擎

基于订单簿的撮合逻辑：
  1. 市价单 → 吃深度
  2. 限价单 → 排队，被动成交
  3. 部分成交
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .orderbook.simulator import OrderBookSimulator, OrderBookSnapshot
from .orderbook.liquidity_model import LiquidityModel, LiquidityProfile

logger = logging.getLogger("quantlab.execution.fidelity.matcher")


@dataclass
class MatchResult:
    """撮合结果"""
    order_id: str
    symbol: str
    side: str
    fills: List[Dict] = field(default_factory=list)   # [{price, qty, timestamp}]
    avg_fill_price: float = 0.0
    total_filled: float = 0.0
    remaining: float = 0.0
    is_complete: bool = False
    queue_position: int = 0
    slippage_bps: float = 0.0
    impact_bps: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "fills": self.fills,
            "avg_fill_price": self.avg_fill_price,
            "total_filled": self.total_filled,
            "remaining": self.remaining,
            "is_complete": self.is_complete,
            "queue_position": self.queue_position,
            "slippage_bps": self.slippage_bps,
            "impact_bps": self.impact_bps,
        }


class MatchingEngine:
    """
    撮合引擎

    用法：
        engine = MatchingEngine(
            book_sim=OrderBookSimulator("BTCUSDT"),
            liquidity=LiquidityModel(),
        )
        result = engine.match(
            order_id="o1",
            symbol="BTCUSDT",
            side="BUY",
            qty=10,
            order_type="MARKET",
            mid_price=50000,
            volatility=0.02,
            volume=1000000,
        )
    """

    def __init__(
        self,
        book_sim: OrderBookSimulator = None,
        liquidity: LiquidityModel = None,
    ) -> None:
        self.book_sim = book_sim
        self.liquidity = liquidity or LiquidityModel()
        self._limit_queues: Dict[str, int] = {}  # order_id → queue_position

    def match(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: float,
        order_type: str = "MARKET",   # MARKET / LIMIT
        price: Optional[float] = None,
        mid_price: float = 0,
        volatility: float = 0.01,
        volume: float = 1000000,
    ) -> MatchResult:
        """撮合订单"""
        # 生成订单簿
        book = self.book_sim.generate(
            mid_price=mid_price,
            volatility=volatility,
            volume=volume,
        ) if self.book_sim else self._generate_simple_book(mid_price, volatility)

        if order_type == "MARKET":
            return self._match_market(order_id, symbol, side, qty, book)
        elif order_type == "LIMIT":
            return self._match_limit(order_id, symbol, side, qty, price, book)
        else:
            return MatchResult(order_id=order_id, symbol=symbol, side=side)

    def _match_market(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: float,
        book: OrderBookSnapshot,
    ) -> MatchResult:
        """市价单撮合"""
        fills_data = self.book_sim.sweep_market_order(book, side, qty) if self.book_sim else []

        if not fills_data:
            # 简单模式
            if side == "BUY":
                fill_price = book.best_ask.price if book.best_ask else book.mid_price
            else:
                fill_price = book.best_bid.price if book.best_bid else book.mid_price
            fills_data = [(fill_price, qty)]

        fills: List[Dict] = []
        total_filled = 0
        total_value = 0

        for fill_price, fill_qty in fills_data:
            actual_qty = min(fill_qty, qty - total_filled)
            if actual_qty <= 0:
                break
            fills.append({
                "price": fill_price,
                "qty": actual_qty,
                "timestamp": int(time.time() * 1000),
            })
            total_filled += actual_qty
            total_value += fill_price * actual_qty

        avg_price = total_value / total_filled if total_filled > 0 else 0
        remaining = qty - total_filled
        slippage_bps = abs(avg_price - book.mid_price) / book.mid_price * 10000 if book.mid_price > 0 else 0

        return MatchResult(
            order_id=order_id,
            symbol=symbol,
            side=side,
            fills=fills,
            avg_fill_price=avg_price,
            total_filled=total_filled,
            remaining=remaining,
            is_complete=remaining <= 0,
            slippage_bps=slippage_bps,
        )

    def _match_limit(
        self,
        order_id: str,
        symbol: str,
        side: str,
        qty: float,
        price: Optional[float],
        book: OrderBookSnapshot,
    ) -> MatchResult:
        """限价单撮合 — 排队 + 被动成交"""
        if price is None:
            price = book.mid_price

        # 检查是否立即成交（穿越价差）
        immediate_fill = False
        if side == "BUY" and book.best_ask and price >= book.best_ask.price:
            immediate_fill = True
        elif side == "SELL" and book.best_bid and price <= book.best_bid.price:
            immediate_fill = True

        if immediate_fill:
            return self._match_market(order_id, symbol, side, qty, book)

        # 排队
        queue_pos = random.randint(0, 100)
        self._limit_queues[order_id] = queue_pos

        # 部分概率成交（模拟排队等待）
        fill_probability = max(0, 0.5 - queue_pos / 200)
        if random.random() < fill_probability:
            fill_qty = qty * random.uniform(0.3, 0.8)
            fills = [{
                "price": price,
                "qty": fill_qty,
                "timestamp": int(time.time() * 1000),
            }]
            return MatchResult(
                order_id=order_id,
                symbol=symbol,
                side=side,
                fills=fills,
                avg_fill_price=price,
                total_filled=fill_qty,
                remaining=qty - fill_qty,
                is_complete=False,
                queue_position=queue_pos,
            )

        # 未成交
        return MatchResult(
            order_id=order_id,
            symbol=symbol,
            side=side,
            fills=[],
            avg_fill_price=0,
            total_filled=0,
            remaining=qty,
            is_complete=False,
            queue_position=queue_pos,
        )

    def _generate_simple_book(
        self,
        mid_price: float,
        volatility: float,
    ) -> OrderBookSnapshot:
        """简单订单簿（无 simulator 时）"""
        spread = mid_price * 0.0002 * (1 + volatility * 10)
        return OrderBookSnapshot(
            symbol="",
            bids=[],
            asks=[],
            timestamp=int(time.time() * 1000),
        )

    def get_queue_position(self, order_id: str) -> int:
        return self._limit_queues.get(order_id, -1)

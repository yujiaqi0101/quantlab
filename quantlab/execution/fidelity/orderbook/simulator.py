"""
Order Book Simulation — 订单簿模拟

模拟真实订单簿：
  1. bid / ask depth（多档深度）
  2. spread（价差）
  3. liquidity layers（流动性分层）

行为：
  - market order → 吃深度
  - limit order → 排队
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("quantlab.execution.fidelity.orderbook")


@dataclass
class PriceLevel:
    """价格档位"""
    price: float
    qty: float

    def to_dict(self) -> Dict:
        return {"price": self.price, "qty": self.qty}


@dataclass
class OrderBookSnapshot:
    """订单簿快照"""
    symbol: str
    bids: List[PriceLevel] = field(default_factory=list)   # 降序
    asks: List[PriceLevel] = field(default_factory=list)   # 升序
    timestamp: int = 0

    @property
    def best_bid(self) -> Optional[PriceLevel]:
        return self.bids[0] if self.bids else None

    @property
    def best_ask(self) -> Optional[PriceLevel]:
        return self.asks[0] if self.asks else None

    @property
    def mid_price(self) -> float:
        if self.best_bid and self.best_ask:
            return (self.best_bid.price + self.best_ask.price) / 2
        return 0.0

    @property
    def spread(self) -> float:
        if self.best_bid and self.best_ask:
            return self.best_ask.price - self.best_bid.price
        return 0.0

    @property
    def spread_bps(self) -> float:
        mid = self.mid_price
        if mid > 0:
            return self.spread / mid * 10000
        return 0.0

    def bid_depth(self, levels: int = 10) -> float:
        """前 N 档买盘总深度"""
        return sum(l.qty for l in self.bids[:levels])

    def ask_depth(self, levels: int = 10) -> float:
        return sum(l.qty for l in self.asks[:levels])

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "bids": [l.to_dict() for l in self.bids[:20]],
            "asks": [l.to_dict() for l in self.asks[:20]],
            "timestamp": self.timestamp,
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
        }


class OrderBookSimulator:
    """
    订单簿模拟器

    用法：
        sim = OrderBookSimulator(symbol="BTCUSDT")
        book = sim.generate(mid_price=50000, volatility=0.02)
        # 市价单吃深度
        fills = sim.sweep_market_order(book, side="BUY", qty=10)
    """

    def __init__(
        self,
        symbol: str,
        base_spread_bps: float = 2.0,
        depth_levels: int = 20,
        base_qty: float = 1.0,
        qty_decay: float = 0.85,
    ) -> None:
        self.symbol = symbol
        self.base_spread_bps = base_spread_bps
        self.depth_levels = depth_levels
        self.base_qty = base_qty
        self.qty_decay = qty_decay

    def generate(
        self,
        mid_price: float,
        volatility: float = 0.01,
        volume: float = 1000.0,
    ) -> OrderBookSnapshot:
        """生成订单簿快照"""
        # 价差随波动率扩大
        spread_bps = self.base_spread_bps * (1 + volatility * 50)
        spread = mid_price * spread_bps / 10000

        half_spread = spread / 2
        tick = mid_price * 0.0001  # 最小变动价位

        bids: List[PriceLevel] = []
        asks: List[PriceLevel] = []

        # 深度随成交量调整
        vol_factor = max(0.5, min(2.0, volume / 1000.0))

        for i in range(self.depth_levels):
            # 价格随档位加深
            bid_price = mid_price - half_spread - tick * i * (1 + random.uniform(-0.2, 0.2))
            ask_price = mid_price + half_spread + tick * i * (1 + random.uniform(-0.2, 0.2))

            # 深度随档位衰减
            qty = self.base_qty * (self.qty_decay ** i) * vol_factor * random.uniform(0.7, 1.3)

            bids.append(PriceLevel(price=bid_price, qty=qty))
            asks.append(PriceLevel(price=ask_price, qty=qty))

        import time
        return OrderBookSnapshot(
            symbol=self.symbol,
            bids=bids,
            asks=asks,
            timestamp=int(time.time() * 1000),
        )

    def sweep_market_order(
        self,
        book: OrderBookSnapshot,
        side: str,
        qty: float,
    ) -> List[Tuple[float, float]]:
        """
        市价单吃深度

        返回 [(fill_price, fill_qty), ...]
        """
        fills: List[Tuple[float, float]] = []
        remaining = qty

        levels = book.asks if side == "BUY" else book.bids

        for level in levels:
            if remaining <= 0:
                break
            fill_qty = min(remaining, level.qty)
            fills.append((level.price, fill_qty))
            remaining -= fill_qty

        if remaining > 0:
            # 深度不够，按最后一档价格成交
            if levels:
                last_price = levels[-1].price
                fills.append((last_price, remaining))
            logger.warning(
                f"OrderBook sweep: {side} {qty} exceeded depth, "
                f"{remaining} unfilled"
            )

        return fills

    def estimate_market_impact(
        self,
        book: OrderBookSnapshot,
        side: str,
        qty: float,
    ) -> Dict:
        """估算市价单冲击"""
        fills = self.sweep_market_order(book, side, qty)
        if not fills:
            return {"avg_price": 0, "impact_bps": 0, "filled_qty": 0}

        total_value = sum(p * q for p, q in fills)
        total_qty = sum(q for _, q in fills)
        avg_price = total_value / total_qty if total_qty > 0 else 0

        mid = book.mid_price
        impact_bps = abs(avg_price - mid) / mid * 10000 if mid > 0 else 0

        return {
            "avg_price": avg_price,
            "impact_bps": impact_bps,
            "filled_qty": total_qty,
            "mid_price": mid,
            "slippage": avg_price - mid if side == "BUY" else mid - avg_price,
        }

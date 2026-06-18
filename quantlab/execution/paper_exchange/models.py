"""
Paper Exchange Models — 模拟交易所数据模型
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExchangeQuote:
    """交易所报价"""
    symbol: str
    bid: float = 0.0
    ask: float = 0.0
    last: float = 0.0
    volume: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    @property
    def mid(self) -> float:
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "bid": self.bid,
            "ask": self.ask,
            "last": self.last,
            "mid": self.mid,
            "volume": self.volume,
            "timestamp": self.timestamp,
        }


@dataclass
class ExchangeFill:
    """交易所成交回报"""
    id: str = field(default_factory=lambda: f"XFILL-{uuid.uuid4().hex[:12]}")
    symbol: str = ""
    side: str = ""           # BUY / SELL
    qty: float = 0.0
    price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))
    order_type: str = "MARKET"
    client_order_id: str = ""
    broker_order_id: str = ""
    is_partial: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "price": self.price,
            "commission": self.commission,
            "slippage": self.slippage,
            "timestamp": self.timestamp,
            "order_type": self.order_type,
            "client_order_id": self.client_order_id,
            "broker_order_id": self.broker_order_id,
            "is_partial": self.is_partial,
        }

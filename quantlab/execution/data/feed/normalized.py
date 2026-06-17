"""
Normalized Market Data — 统一行情格式

不同交易所的行情格式不同，这里统一为标准格式
所有下游组件只依赖 NormalizedTick / NormalizedBar
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class NormalizedTick:
    """
    标准化 Tick 数据

    所有交易所的 tick 统一转成这个格式
    """
    symbol: str
    price: float
    volume: float
    timestamp: int           # exchange timestamp (ms)
    local_timestamp: int     # 本地接收时间 (ms)
    bid: float = 0.0
    ask: float = 0.0
    bid_volume: float = 0.0
    ask_volume: float = 0.0
    source: str = ""         # binance / ibkr / paper

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "local_timestamp": self.local_timestamp,
            "bid": self.bid,
            "ask": self.ask,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "source": self.source,
        }


@dataclass
class NormalizedBar:
    """标准化 K 线"""
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: int
    interval: str = "1m"
    source: str = ""

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timestamp": self.timestamp,
            "interval": self.interval,
            "source": self.source,
        }


@dataclass
class NormalizedDepth:
    """标准化盘口深度"""
    symbol: str
    bids: list  # [(price, volume), ...]
    asks: list
    timestamp: int
    source: str = ""


class MarketDataNormalizer:
    """
    行情数据标准化器

    把不同交易所的原始数据转成 NormalizedTick / NormalizedBar
    """

    @staticmethod
    def from_binance_trade(msg: Dict) -> NormalizedTick:
        """Binance trade stream → NormalizedTick"""
        return NormalizedTick(
            symbol=msg.get("s", ""),
            price=float(msg.get("p", 0)),
            volume=float(msg.get("q", 0)),
            timestamp=int(msg.get("T", 0)),
            local_timestamp=int(msg.get("E", 0)),
            source="binance",
        )

    @staticmethod
    def from_binance_ticker(msg: Dict) -> NormalizedTick:
        """Binance 24h ticker → NormalizedTick"""
        return NormalizedTick(
            symbol=msg.get("s", ""),
            price=float(msg.get("c", 0)),
            volume=float(msg.get("v", 0)),
            timestamp=int(msg.get("E", 0)),
            local_timestamp=int(msg.get("E", 0)),
            bid=float(msg.get("b", 0)),
            ask=float(msg.get("a", 0)),
            bid_volume=float(msg.get("B", 0)),
            ask_volume=float(msg.get("A", 0)),
            source="binance",
        )

    @staticmethod
    def from_binance_kline(msg: Dict) -> NormalizedBar:
        """Binance kline stream → NormalizedBar"""
        k = msg.get("k", {})
        return NormalizedBar(
            symbol=msg.get("s", ""),
            open=float(k.get("o", 0)),
            high=float(k.get("h", 0)),
            low=float(k.get("l", 0)),
            close=float(k.get("c", 0)),
            volume=float(k.get("v", 0)),
            timestamp=int(k.get("t", 0)),
            interval=k.get("i", "1m"),
            source="binance",
        )

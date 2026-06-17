"""
Market Snapshot — 行情快照

定期对行情做快照，用于：
  1. 系统恢复时重建行情状态
  2. 对账时对比本地 vs 交易所
  3. 回放时还原历史行情
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List

from ..feed.normalized import NormalizedTick


@dataclass
class MarketSnapshot:
    """
    行情快照 — 某一时刻所有标的的价格快照
    """
    timestamp: int                           # exchange time (ms)
    local_timestamp: int = 0                 # local capture time (ms)
    prices: Dict[str, float] = field(default_factory=dict)
    volumes: Dict[str, float] = field(default_factory=dict)
    bids: Dict[str, float] = field(default_factory=dict)
    asks: Dict[str, float] = field(default_factory=dict)
    source: str = ""

    @classmethod
    def from_ticks(
        cls,
        ticks: List[NormalizedTick],
        source: str = "",
    ) -> "MarketSnapshot":
        """从一批 tick 构建快照"""
        snap = cls(
            timestamp=max((t.timestamp for t in ticks), default=0),
            local_timestamp=int(time.time() * 1000),
            source=source,
        )
        for t in ticks:
            snap.prices[t.symbol] = t.price
            snap.volumes[t.symbol] = t.volume
            if t.bid:
                snap.bids[t.symbol] = t.bid
            if t.ask:
                snap.asks[t.symbol] = t.ask
        return snap

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "local_timestamp": self.local_timestamp,
            "prices": self.prices,
            "volumes": self.volumes,
            "bids": self.bids,
            "asks": self.asks,
            "source": self.source,
        }

    def get_price(self, symbol: str) -> float:
        return self.prices.get(symbol, 0.0)

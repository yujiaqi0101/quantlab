"""
Fill Engine — 成交引擎

负责：
  1. 接收交易所成交回报
  2. 部分成交处理
  3. 成交记录持久化
  4. 推送成交事件
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.core.fills")


@dataclass
class Fill:
    """成交记录"""
    id: str = field(default_factory=lambda: f"FILL-{uuid.uuid4().hex[:12]}")
    order_id: str = ""
    broker_order_id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: str = ""           # BUY / SELL
    fill_qty: int = 0
    fill_price: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0    # 实际滑点
    timestamp: int = 0       # exchange time (ms)
    local_timestamp: int = 0 # local receive time (ms)
    is_partial: bool = False
    source: str = ""         # binance / paper / ibkr

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "order_id": self.order_id,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "fill_qty": self.fill_qty,
            "fill_price": self.fill_price,
            "commission": self.commission,
            "slippage": self.slippage,
            "timestamp": self.timestamp,
            "local_timestamp": self.local_timestamp,
            "is_partial": self.is_partial,
            "source": self.source,
        }


class FillEngine:
    """
    成交引擎

    用法：
        engine = FillEngine()
        engine.on_fill(callback)
        fill = engine.process_fill(
            order_id="OMS-xxx",
            symbol="BTCUSDT",
            side="BUY",
            fill_qty=50,
            fill_price=50000,
        )
    """

    def __init__(self) -> None:
        self._fills: List[Fill] = []
        self._callbacks: List[Callable[[Fill], None]] = []
        self._fill_index: Dict[str, List[Fill]] = {}  # order_id → fills

    def process_fill(
        self,
        order_id: str,
        symbol: str,
        side: str,
        fill_qty: int,
        fill_price: float,
        broker_order_id: str = "",
        client_order_id: str = "",
        commission: float = 0.0,
        expected_price: float = 0.0,
        timestamp: int = 0,
        source: str = "",
    ) -> Fill:
        """处理一笔成交"""
        now = int(time.time() * 1000)
        slippage = 0.0
        if expected_price > 0:
            if side == "BUY":
                slippage = (fill_price - expected_price) / expected_price
            else:
                slippage = (expected_price - fill_price) / expected_price

        fill = Fill(
            order_id=order_id,
            broker_order_id=broker_order_id,
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            fill_qty=fill_qty,
            fill_price=fill_price,
            commission=commission,
            slippage=slippage,
            timestamp=timestamp or now,
            local_timestamp=now,
            source=source,
        )

        self._fills.append(fill)
        self._fill_index.setdefault(order_id, []).append(fill)

        # 推送回调
        for cb in self._callbacks:
            try:
                cb(fill)
            except Exception as e:
                logger.error(f"Fill callback error: {e}")

        logger.info(
            f"Fill: {fill.id} {side} {fill_qty} {symbol} "
            f"@ {fill_price} (slippage={slippage:.4%})"
        )
        return fill

    def on_fill(self, callback: Callable[[Fill], None]) -> None:
        self._callbacks.append(callback)

    def get_fills(self, order_id: str = "") -> List[Fill]:
        if order_id:
            return list(self._fill_index.get(order_id, []))
        return list(self._fills)

    def get_fills_by_symbol(self, symbol: str) -> List[Fill]:
        return [f for f in self._fills if f.symbol == symbol]

    def get_all_fills(self) -> List[Fill]:
        return list(self._fills)

    def total_commission(self) -> float:
        return sum(f.commission for f in self._fills)

    def total_slippage_cost(self) -> float:
        """总滑点成本（金额）"""
        return sum(
            abs(f.slippage) * f.fill_price * f.fill_qty
            for f in self._fills
        )

    def restore(self, fills: List[Fill]) -> None:
        """从持久化恢复"""
        self._fills = fills
        self._fill_index.clear()
        for f in fills:
            self._fill_index.setdefault(f.order_id, []).append(f)
        logger.info(f"FillEngine restored {len(fills)} fills")

"""
Paper Exchange — 模拟交易所核心

T1 第六模块：模拟成交 / 手续费 / 滑点 / 延迟

第一版：
  fee = 0.001 (0.1%)
  slippage = 0.0005 (0.05%)
  latency = 0 ms（可配置）

职责：
  1. 维护行情报价
  2. 接收订单 → 撮合 → 生成 Fill
  3. 模拟手续费、滑点、延迟
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from ..broker.base import OrderRequest
from .models import ExchangeFill, ExchangeQuote

logger = logging.getLogger("quantlab.execution.paper_exchange")


@dataclass
class ExchangeConfig:
    """交易所配置"""
    fee_rate: float = 0.001              # 0.1%
    slippage_rate: float = 0.0005        # 0.05%
    latency_ms: int = 0                  # 模拟延迟（毫秒）
    enable_partial_fill: bool = False    # 部分成交（第一版关闭）
    enable_random_slippage: bool = True  # 随机滑点波动
    random_slippage_range: float = 0.5   # 滑点波动范围（0-1）

    def to_dict(self) -> dict:
        return {
            "fee_rate": self.fee_rate,
            "slippage_rate": self.slippage_rate,
            "latency_ms": self.latency_ms,
            "enable_partial_fill": self.enable_partial_fill,
            "enable_random_slippage": self.enable_random_slippage,
        }


class PaperExchange:
    """
    模拟交易所

    用法：
        exchange = PaperExchange()
        exchange.update_quote("BTCUSDT", bid=49990, ask=50010, last=50000)
        fill = exchange.match_order(OrderRequest(
            symbol="BTCUSDT", side="BUY", qty=0.1, order_type="MARKET"
        ))
    """

    def __init__(self, config: ExchangeConfig = ExchangeConfig()) -> None:
        self.config = config
        self._quotes: Dict[str, ExchangeQuote] = {}
        self._fills: List[ExchangeFill] = []
        self._callbacks: List[Callable[[ExchangeFill], None]] = []
        self._order_counter: int = 0

    # ------------------------------------------------------------------
    # 行情
    # ------------------------------------------------------------------
    def update_quote(
        self,
        symbol: str,
        bid: float = 0,
        ask: float = 0,
        last: float = 0,
        volume: float = 0,
    ) -> ExchangeQuote:
        """更新行情报价"""
        if symbol not in self._quotes:
            self._quotes[symbol] = ExchangeQuote(symbol=symbol)

        q = self._quotes[symbol]
        if bid > 0:
            q.bid = bid
        if ask > 0:
            q.ask = ask
        if last > 0:
            q.last = last
        if volume > 0:
            q.volume = volume
        q.timestamp = int(time.time() * 1000)

        return q

    def update_price(self, symbol: str, price: float) -> None:
        """简单更新价格（bid/ask 自动计算）"""
        spread = price * self.config.slippage_rate
        self.update_quote(
            symbol=symbol,
            bid=price - spread / 2,
            ask=price + spread / 2,
            last=price,
        )

    def get_quote(self, symbol: str) -> Optional[ExchangeQuote]:
        return self._quotes.get(symbol)

    def get_price(self, symbol: str) -> float:
        q = self._quotes.get(symbol)
        return q.mid if q else 0.0

    def get_all_quotes(self) -> Dict[str, ExchangeQuote]:
        return dict(self._quotes)

    # ------------------------------------------------------------------
    # 撮合
    # ------------------------------------------------------------------
    def match_order(self, req: OrderRequest) -> Optional[ExchangeFill]:
        """撮合订单 → 生成成交"""
        q = self._quotes.get(req.symbol)
        if not q or q.last <= 0:
            logger.warning(f"PaperExchange: no quote for {req.symbol}")
            return None

        # 模拟延迟
        if self.config.latency_ms > 0:
            time.sleep(self.config.latency_ms / 1000.0)

        # 计算成交价
        fill_price = self._calculate_fill_price(req, q)

        # 手续费
        commission = fill_price * req.qty * self.config.fee_rate

        # 滑点
        slippage = 0.0
        if req.order_type == "MARKET":
            base = q.mid
            if req.side == "BUY":
                slippage = (fill_price - base) / base if base > 0 else 0
            else:
                slippage = (base - fill_price) / base if base > 0 else 0

        # 生成成交
        self._order_counter += 1
        broker_order_id = f"PEX-{self._order_counter:06d}"

        fill = ExchangeFill(
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            price=fill_price,
            commission=commission,
            slippage=slippage,
            order_type=req.order_type,
            client_order_id=req.client_order_id,
            broker_order_id=broker_order_id,
        )

        self._fills.append(fill)

        # 推送回调
        for cb in self._callbacks:
            try:
                cb(fill)
            except Exception as e:
                logger.error(f"PaperExchange callback error: {e}")

        logger.info(
            f"PaperExchange fill: {req.side} {req.qty} {req.symbol} "
            f"@ {fill_price:.4f} (fee={commission:.4f}, slip={slippage:.4%})"
        )

        return fill

    def _calculate_fill_price(self, req: OrderRequest, q: ExchangeQuote) -> float:
        """计算成交价"""
        if req.order_type == "LIMIT" and req.price:
            return req.price

        # MARKET 单：基于 ask/bid + 滑点
        base_price = q.ask if req.side == "BUY" else q.bid
        if base_price <= 0:
            base_price = q.last

        # 滑点
        slippage_rate = self.config.slippage_rate
        if self.config.enable_random_slippage:
            # 随机滑点波动
            factor = random.uniform(
                1 - self.config.random_slippage_range,
                1 + self.config.random_slippage_range,
            )
            slippage_rate *= factor

        if req.side == "BUY":
            return base_price * (1 + slippage_rate)
        else:
            return base_price * (1 - slippage_rate)

    # ------------------------------------------------------------------
    # 回调
    # ------------------------------------------------------------------
    def on_fill(self, callback: Callable[[ExchangeFill], None]) -> None:
        """注册成交回调"""
        self._callbacks.append(callback)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get_fills(self, symbol: str = "") -> List[ExchangeFill]:
        if symbol:
            return [f for f in self._fills if f.symbol == symbol]
        return list(self._fills)

    def total_commission(self) -> float:
        return sum(f.commission for f in self._fills)

    def total_volume(self) -> float:
        return sum(f.qty * f.price for f in self._fills)

    def n_fills(self) -> int:
        return len(self._fills)

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "config": self.config.to_dict(),
            "n_quotes": len(self._quotes),
            "n_fills": self.n_fills(),
            "total_commission": self.total_commission(),
            "total_volume": self.total_volume(),
            "quotes": {s: q.to_dict() for s, q in self._quotes.items()},
        }

    def reset(self) -> None:
        """清空所有状态"""
        self._quotes.clear()
        self._fills.clear()
        self._order_counter = 0

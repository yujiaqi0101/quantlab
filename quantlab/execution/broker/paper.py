"""
Paper Broker — 模拟 Broker

基于本地 PositionBook + PortfolioBook 维护账户状态
不依赖外部交易所

  fee = 0.001 (0.1%)
  slippage = 0.0005 (0.05%)
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from .base import (
    AccountInfo,
    Broker,
    BrokerType,
    OpenOrder,
    OrderRequest,
    OrderResponse,
    PositionInfo,
)

logger = logging.getLogger("quantlab.execution.broker.paper")


class PaperBroker(Broker):
    """
    Paper Broker — 模拟成交

    用法：
        broker = PaperBroker(initial_capital=100000)
        broker.update_market_prices({"BTCUSDT": 50000})
        resp = broker.submit_order(OrderRequest(
            symbol="BTCUSDT", side="BUY", qty=0.1, order_type="MARKET"
        ))
    """

    broker_type = BrokerType.PAPER

    def __init__(
        self,
        initial_capital: float = 100000.0,
        fee_rate: float = 0.001,           # 0.1%
        slippage_rate: float = 0.0005,     # 0.05%
        account_id: str = "",
    ) -> None:
        super().__init__(account_id=account_id)

        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.fee_rate = fee_rate
        self.slippage_rate = slippage_rate

        # 持仓（本地维护）
        self._positions: Dict[str, PositionInfo] = {}
        # 挂单
        self._open_orders: Dict[str, OpenOrder] = {}
        # 市场价格
        self._market_prices: Dict[str, float] = {}
        # 已实现 PnL
        self._realized_pnl: float = 0.0

    # ------------------------------------------------------------------
    # 账户
    # ------------------------------------------------------------------
    def get_account(self) -> AccountInfo:
        equity = self.cash + sum(
            p.qty * p.market_price for p in self._positions.values()
        )
        margin = sum(
            abs(p.qty * p.market_price)
            for p in self._positions.values()
        )
        return AccountInfo(
            broker=self.name,
            account_id=self.account_id,
            cash=self.cash,
            equity=equity,
            margin=margin,
            margin_ratio=margin / equity if equity > 0 else 0.0,
            initial_capital=self.initial_capital,
            updated_at=int(time.time() * 1000),
        )

    def get_positions(self) -> List[PositionInfo]:
        return [p for p in self._positions.values() if abs(p.qty) > 1e-10]

    # ------------------------------------------------------------------
    # 下单
    # ------------------------------------------------------------------
    def submit_order(self, req: OrderRequest) -> OrderResponse:
        """提交订单（Paper 立即成交）"""
        now = int(time.time() * 1000)

        # 获取市场价格
        market_price = self._market_prices.get(req.symbol, 0.0)
        if market_price <= 0:
            return OrderResponse(
                client_order_id=req.client_order_id,
                status="REJECTED",
                reject_reason=f"no market price for {req.symbol}",
                timestamp=now,
                broker=self.name,
            )

        # 计算成交价（含滑点）
        if req.order_type == "LIMIT" and req.price:
            base_price = req.price
        else:
            if req.side == "BUY":
                base_price = market_price * (1 + self.slippage_rate)
            else:
                base_price = market_price * (1 - self.slippage_rate)

        # 手续费
        commission = base_price * req.qty * self.fee_rate

        # 更新持仓和现金
        self._apply_fill(
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            price=base_price,
            commission=commission,
        )

        broker_order_id = f"PAPER-{uuid.uuid4().hex[:12]}"
        logger.info(
            f"PaperBroker fill: {req.side} {req.qty} {req.symbol} "
            f"@ {base_price:.4f} (fee={commission:.4f})"
        )

        return OrderResponse(
            broker_order_id=broker_order_id,
            client_order_id=req.client_order_id,
            status="FILLED",
            timestamp=now,
            broker=self.name,
        )

    def cancel_order(self, broker_order_id: str) -> bool:
        """撤单（Paper 立即成交，无挂单可撤）"""
        if broker_order_id in self._open_orders:
            self._open_orders.pop(broker_order_id)
            return True
        return False

    def get_open_orders(self, symbol: str = "") -> List[OpenOrder]:
        orders = list(self._open_orders.values())
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        return orders

    # ------------------------------------------------------------------
    # 市场价格
    # ------------------------------------------------------------------
    def get_market_price(self, symbol: str) -> float:
        return self._market_prices.get(symbol, 0.0)

    def update_market_prices(self, prices: Dict[str, float]) -> None:
        self._market_prices.update(prices)
        # 更新持仓的市场价格和未实现盈亏
        for symbol, price in prices.items():
            if symbol in self._positions:
                pos = self._positions[symbol]
                pos.market_price = price
                pos.unrealized_pnl = (price - pos.avg_price) * pos.qty
                pos.updated_at = int(time.time() * 1000)

    # ------------------------------------------------------------------
    # 内部：应用成交
    # ------------------------------------------------------------------
    def _apply_fill(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        commission: float,
    ) -> None:
        """应用成交到持仓和现金"""
        signed_qty = qty if side == "BUY" else -qty
        trade_value = price * qty

        # 现金变化
        self.cash -= trade_value if side == "BUY" else -trade_value
        self.cash -= commission

        # 持仓更新
        if symbol not in self._positions:
            self._positions[symbol] = PositionInfo(
                symbol=symbol,
                avg_price=price,
                market_price=price,
                updated_at=int(time.time() * 1000),
            )

        pos = self._positions[symbol]
        old_qty = pos.qty

        if old_qty == 0:
            # 新建仓
            pos.qty = signed_qty
            pos.avg_price = price
        elif (old_qty > 0) == (signed_qty > 0):
            # 加仓
            total_qty = old_qty + signed_qty
            pos.avg_price = (
                (pos.avg_price * old_qty + price * signed_qty) / total_qty
            )
            pos.qty = total_qty
        else:
            # 减仓或反手
            closing_qty = min(abs(signed_qty), abs(old_qty))
            if old_qty > 0:
                realized = (price - pos.avg_price) * closing_qty
            else:
                realized = (pos.avg_price - price) * closing_qty
            pos.realized_pnl += realized
            self._realized_pnl += realized

            new_qty = old_qty + signed_qty
            if abs(new_qty) < 1e-10:
                # 清仓
                pos.qty = 0
                pos.avg_price = 0
            elif (new_qty > 0) != (old_qty > 0):
                # 反手
                pos.qty = new_qty
                pos.avg_price = price
            else:
                # 部分减仓
                pos.qty = new_qty

        # 更新未实现盈亏
        pos.market_price = price
        pos.unrealized_pnl = (price - pos.avg_price) * pos.qty
        pos.side = "LONG" if pos.qty > 0 else ("SHORT" if pos.qty < 0 else "FLAT")
        pos.updated_at = int(time.time() * 1000)

    # ------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------
    def health_check(self) -> bool:
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            **super().to_dict(),
            "initial_capital": self.initial_capital,
            "cash": self.cash,
            "fee_rate": self.fee_rate,
            "slippage_rate": self.slippage_rate,
            "realized_pnl": self._realized_pnl,
            "n_positions": len(self.get_positions()),
            "n_open_orders": len(self._open_orders),
        }

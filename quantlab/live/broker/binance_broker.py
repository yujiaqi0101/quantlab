"""
BinanceBroker：Binance 现货真实接口

第一优先级实现。只做现货，不做合约/杠杆/期权。

依赖：
  pip install python-binance

接口：
  connect()                     登录
  get_account()                 现货账户余额
  get_positions()               现货持仓
  submit_order(order) -> str    下单（MARKET / LIMIT）
  cancel_order(order_id) -> bool 撤单
  on_fill(callback)             注册成交回调

下单流程：
  1) 策略生成 Order(symbol, quantity, price, order_type)
  2) BinanceBroker.submit_order()
     - quantity > 0 → BUY
     - quantity < 0 → SELL
     - order_type=MARKET → 市价单
     - order_type=LIMIT  → 限价单（需 price）
  3) 返回 Binance order_id
  4) 成交后通过 on_fill 回调推送 Fill

用法：
    from quantlab.live.broker.binance_broker import BinanceBroker

    broker = BinanceBroker(
        api_key="xxx",
        api_secret="xxx",
        testnet=True,    # 先用测试网
    )
    broker.connect()

    from quantlab.core.order import Order
    order = Order(symbol="BTCUSDT", quantity=1, order_type="MARKET")
    order_id = broker.submit_order(order)
"""

from __future__ import annotations

import logging
import math
import time
from typing import Callable, Dict, List, Optional

from ...core.order import (
    Order,
    ORDER_TYPE_LIMIT,
    ORDER_TYPE_MARKET,
    SIDE_BUY,
    SIDE_SELL,
)
from .base import AccountState, BrokerAdapter

logger = logging.getLogger("quantlab.live.broker.binance")


class BinanceBroker(BrokerAdapter):
    """
    Binance 现货适配器

    只做现货（spot），不做合约/杠杆/期权。
    """

    name = "BINANCE"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        market: str = "spot",   # 固定 "spot"
    ) -> None:
        if market != "spot":
            raise ValueError(
                "BinanceBroker V1 only supports spot. "
                "Futures / margin / options not supported."
            )

        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.market = market

        self._client = None
        self._connected = False
        self._fill_cb: Optional[Callable] = None

        # 本地维护的订单映射：binance_order_id → Order
        self._orders: Dict[str, Order] = {}
        # 本地缓存的持仓（避免频繁请求）
        self._positions_cache: Dict[str, float] = {}
        self._account_cache: Optional[AccountState] = None
        # 最近成交价缓存（用于估算 equity）
        self._last_prices: Dict[str, float] = {}

    # ------------------------------------------------------------------
    # 连接
    # ------------------------------------------------------------------

    def connect(self) -> None:
        """登录 Binance"""
        try:
            from binance.client import Client
        except ImportError as e:
            raise RuntimeError(
                "python-binance not installed. "
                "Run: pip install python-binance"
            ) from e

        self._client = Client(self.api_key, self.api_secret)

        if self.testnet:
            # 现货测试网
            self._client.API_URL = "https://testnet.binance.vision/api"

        # 验证连接
        try:
            self._client.ping()
            self._connected = True
            logger.info(
                f"BinanceBroker connected (testnet={self.testnet})"
            )
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Binance connect failed: {e}") from e

    def disconnect(self) -> None:
        """断开"""
        self._connected = False
        self._client = None
        logger.info("BinanceBroker disconnected")

    # ------------------------------------------------------------------
    # 账户 & 持仓
    # ------------------------------------------------------------------

    def get_account(self) -> AccountState:
        """获取现货账户余额"""
        if not self._connected:
            return AccountState()

        try:
            info = self._client.get_account()
            balances = info.get("balances", [])

            # 找 USDT 现金
            cash = 0.0
            positions_value = 0.0
            self._positions_cache.clear()

            for b in balances:
                asset = b["asset"]
                free = float(b["free"])
                locked = float(b["locked"])
                total = free + locked

                if asset == "USDT":
                    cash = free
                elif total > 0:
                    self._positions_cache[asset] = total
                    # 估算市值
                    if asset in self._last_prices:
                        positions_value += total * self._last_prices[asset]

            equity = cash + positions_value
            self._account_cache = AccountState(
                cash=cash,
                equity=equity,
                margin_used=0.0,           # 现货无保证金
                buying_power=cash,         # 现货 buying_power = 现金
            )
            return self._account_cache

        except Exception as e:
            logger.error(f"BinanceBroker.get_account failed: {e}")
            return self._account_cache or AccountState()

    def get_positions(self) -> Dict[str, float]:
        """
        获取现货持仓

        返回 Dict[asset, qty]，asset 不含 USDT
        """
        if not self._connected:
            return {}

        # 先刷新账户
        self.get_account()
        return dict(self._positions_cache)

    def update_last_price(self, symbol: str, price: float) -> None:
        """更新最新价（用于估算 equity）"""
        self._last_prices[symbol] = price

    # ------------------------------------------------------------------
    # 下单
    # ------------------------------------------------------------------

    def submit_order(self, order: Order) -> str:
        """
        提交订单到 Binance

        参数：
          order.quantity > 0 → BUY
          order.quantity < 0 → SELL
          order.order_type   MARKET / LIMIT
          order.price        LIMIT 单必填

        返回：
          Binance order_id（字符串）
        """
        if not self._connected:
            raise RuntimeError("BinanceBroker not connected")

        # 参数校验
        qty = abs(order.quantity)
        if qty <= 0:
            raise ValueError(f"invalid quantity: {order.quantity}")

        side = SIDE_BUY if order.quantity > 0 else SIDE_SELL
        symbol = order.symbol
        order_type = order.order_type.upper()

        # Binance 要求 quantity 精度对齐（不同 symbol 精度不同）
        # V1 简化：用 round 到 6 位小数，后续可查 symbol_info 精确处理
        qty_str = self._format_qty(symbol, qty)

        params: Dict = {
            "symbol": symbol,
            "side": side,
            "quantity": qty_str,
            "newClientOrderId": order.client_order_id,
        }

        if order_type == ORDER_TYPE_MARKET:
            params["type"] = "MARKET"
        elif order_type == ORDER_TYPE_LIMIT:
            if order.price is None or order.price <= 0:
                raise ValueError("LIMIT order requires price")
            params["type"] = "LIMIT"
            params["price"] = self._format_price(symbol, order.price)
            params["timeInForce"] = "GTC"
        else:
            raise ValueError(f"unsupported order_type: {order_type}")

        logger.info(
            f"BinanceBroker.submit_order: {side} {qty_str} {symbol} "
            f"@ {params.get('price', 'MARKET')} (type={order_type})"
        )

        try:
            resp = self._client.create_order(**params)
            binance_id = str(resp.get("orderId", ""))
            status = resp.get("status", "NEW")

            # 缓存订单
            self._orders[binance_id] = order
            order.id = binance_id

            # 同步状态
            if status == "FILLED":
                order.status = "FILLED"
                order.filled_qty = int(qty)
                self._emit_fill(order, resp)
            elif status == "PARTIALLY_FILLED":
                order.status = "PARTIAL"
                order.filled_qty = int(
                    float(resp.get("executedQty", 0))
                )
            elif status == "NEW":
                order.status = "NEW"
            elif status == "REJECTED":
                order.status = "REJECTED"
                order.reject_reason = resp.get("rejectReason", "")

            logger.info(
                f"BinanceBroker: order {binance_id} status={status}"
            )
            return binance_id

        except Exception as e:
            logger.error(f"BinanceBroker.submit_order failed: {e}")
            order.status = "REJECTED"
            order.reject_reason = str(e)
            raise

    def cancel_order(self, order_id: str) -> bool:
        """撤单"""
        if not self._connected:
            return False

        order = self._orders.get(order_id)
        symbol = order.symbol if order else None
        if symbol is None:
            logger.error(f"cancel_order: order {order_id} not found")
            return False

        try:
            self._client.cancel_order(
                symbol=symbol,
                orderId=order_id,
            )
            if order:
                order.status = "CANCELLED"
            logger.info(f"BinanceBroker: order {order_id} cancelled")
            return True
        except Exception as e:
            logger.error(f"BinanceBroker.cancel_order failed: {e}")
            return False

    # ------------------------------------------------------------------
    # 成交回调
    # ------------------------------------------------------------------

    def on_fill(self, callback: Optional[Callable]) -> None:
        """注册成交回调"""
        self._fill_cb = callback

    def _emit_fill(self, order: Order, resp: Dict) -> None:
        """触发成交回调"""
        if self._fill_cb is None:
            return

        from ...core.fill import Fill

        try:
            executed_qty = float(resp.get("executedQty", abs(order.quantity)))
            # 计算均价
            cum_quote = float(resp.get("cummulativeQuoteQty", 0))
            avg_price = (
                cum_quote / executed_qty
                if executed_qty > 0
                else order.price or 0.0
            )

            # Binance 现货手续费从成交资产里扣
            # V1 简化：用 resp.fills 估算
            commission = 0.0
            fills = resp.get("fills", [])
            if fills:
                commission = sum(float(f.get("commission", 0)) for f in fills)

            fill = Fill(
                symbol=order.symbol,
                quantity=int(order.quantity),
                price=avg_price,
                commission=commission,
            )
            self._fill_cb(fill)
        except Exception as e:
            logger.error(f"BinanceBroker._emit_fill error: {e}")

    # ------------------------------------------------------------------
    # 订单状态查询
    # ------------------------------------------------------------------

    def query_order(self, order_id: str) -> Optional[Dict]:
        """查询订单状态"""
        if not self._connected:
            return None

        order = self._orders.get(order_id)
        if order is None:
            return None

        try:
            return self._client.get_order(
                symbol=order.symbol,
                orderId=order_id,
            )
        except Exception as e:
            logger.error(f"BinanceBroker.query_order failed: {e}")
            return None

    def list_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """查询所有未成交订单"""
        if not self._connected:
            return []
        try:
            if symbol:
                return self._client.get_open_orders(symbol=symbol)
            return self._client.get_open_orders()
        except Exception as e:
            logger.error(f"BinanceBroker.list_open_orders failed: {e}")
            return []

    # ------------------------------------------------------------------
    # 行情（便捷方法）
    # ------------------------------------------------------------------

    def get_symbol_price(self, symbol: str) -> Optional[float]:
        """获取最新价"""
        if not self._connected:
            return self._last_prices.get(symbol)
        try:
            ticker = self._client.get_symbol_ticker(symbol=symbol)
            price = float(ticker["price"])
            self._last_prices[symbol] = price
            return price
        except Exception as e:
            logger.error(f"BinanceBroker.get_symbol_price failed: {e}")
            return self._last_prices.get(symbol)

    # ------------------------------------------------------------------
    # 精度处理
    # ------------------------------------------------------------------

    def _format_qty(self, symbol: str, qty: float) -> str:
        """
        格式化数量

        Binance 每个 symbol 有 stepSize（数量步长）
        V1 简化：round 到 6 位小数，去掉尾 0
        后续可查 symbol_info 精确处理
        """
        # 截断到 6 位小数
        step = 0.000001
        truncated = math.floor(qty / step) * step
        # 格式化去掉尾 0
        s = f"{truncated:.6f}".rstrip("0").rstrip(".")
        return s if s else "0"

    def _format_price(self, symbol: str, price: float) -> str:
        """格式化价格"""
        tick = 0.000001
        truncated = math.floor(price / tick) * tick
        s = f"{truncated:.6f}".rstrip("0").rstrip(".")
        return s if s else "0"

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    def __repr__(self) -> str:
        return (
            f"BinanceBroker(testnet={self.testnet}, "
            f"connected={self._connected})"
        )

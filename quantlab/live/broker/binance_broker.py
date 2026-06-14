"""
BinanceBroker：Binance Spot / Futures API 接口 stub

V3.1 仅给接口，不做真实连接。
真实环境需要：
  pip install binance-connector 或 python-binance
  在 Binance API 管理拿 API_KEY / SECRET
  实现 submit_order / on_fill / get_positions

V3.1 Stub 行为：
  - 同 IBKRBroker，submit_order 抛 NotImplementedError
"""

from typing import Callable, Dict, Optional

from ...core.order import Order
from .base import AccountState, BrokerAdapter


class BinanceBroker(BrokerAdapter):
    """
    Binance 交易所适配器（stub）

    待补：
      1) pip install binance-connector
      2) 在 submit_order / on_fill 实现真实 API
      3) 注意：Binance 限速（weight / order rate）
    """

    name = "BINANCE"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
        market: str = "spot",   # "spot" / "futures"
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.market = market
        self._client = None
        self._connected = False
        self._fill_cb: Optional[Callable] = None

    def connect(self) -> None:
        try:
            # 用户自行替换为 binance-connector / python-binance
            from binance.client import Client
            self._client = Client(self.api_key, self.api_secret)
            if self.testnet:
                self._client.API_URL = (
                    "https://testnet.binance.vision/api"
                )
            self._connected = True
        except ImportError:
            raise RuntimeError(
                "binance client lib not installed. "
                "Run: pip install python-binance"
            )

    def disconnect(self) -> None:
        self._connected = False

    def submit_order(self, order: Order) -> str:
        if not self._connected:
            raise RuntimeError("BinanceBroker not connected")
        raise NotImplementedError(
            "V3.1 stub: implement Binance submit_order "
            "via binance.client.Client.order_***"
        )

    def cancel_order(self, order_id: str) -> bool:
        if not self._connected:
            return False
        raise NotImplementedError("V3.1 stub: cancel_order not implemented")

    def get_positions(self) -> Dict[str, int]:
        if not self._connected:
            return {}
        raise NotImplementedError("V3.1 stub: get_positions not implemented")

    def get_account(self) -> AccountState:
        return AccountState()

    def on_fill(self, callback: Optional[Callable]) -> None:
        self._fill_cb = callback

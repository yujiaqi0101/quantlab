"""
IBKRBroker：IBKR TWS / IB Gateway 接口 stub

V3.1 仅给接口，不做真实连接。
真实环境需要：
  pip install ib_insync
  TWS / IB Gateway 开启 API socket
  修改 submit_order / on_fill 实现

V3.1 Stub 行为：
  - connect / disconnect：log + 状态切换
  - submit_order：抛 NotImplementedError，提示安装 ib_insync
  - get_positions / get_account：抛 NotImplementedError
"""

from typing import Callable, Dict, Optional

from ...core.order import Order
from .base import AccountState, BrokerAdapter


class IBKRBroker(BrokerAdapter):
    """
    IBKR TWS / IB Gateway 适配器（stub）

    待补：
      1) pip install ib_insync
      2) 在 submit_order / on_fill 实现真实 API 调用
      3) 注意：IBKR 要求 market data 订阅
    """

    name = "IBKR"

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,           # 7497 = TWS paper, 7496 = TWS live
        client_id: int = 1,
        account: str = "",
    ):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.account = account
        self._connected = False
        self._ib = None   # ib_insync.IB 实例
        self._fill_cb: Optional[Callable] = None

    def connect(self) -> None:
        # V3.1 stub
        try:
            from ib_insync import IB
            self._ib = IB()
            self._ib.connect(
                self.host, self.port, clientId=self.client_id
            )
            self._connected = True
        except ImportError:
            raise RuntimeError(
                "ib_insync not installed. "
                "Run: pip install ib_insync"
            )

    def disconnect(self) -> None:
        if self._ib is not None and self._connected:
            self._ib.disconnect()
        self._connected = False

    def submit_order(self, order: Order) -> str:
        if not self._connected:
            raise RuntimeError("IBKRBroker not connected")
        raise NotImplementedError(
            "V3.1 stub: see quantlab/live/broker/ibkr_broker.py "
            "to implement IBKR submit_order with ib_insync"
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

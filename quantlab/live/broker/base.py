"""
Broker 统一接口

V3.1：
  策略只调 BrokerAdapter 的方法
  换 broker（IBKR / Binance / Paper）不动策略代码

接口：
  connect()                            物理连接 / 登录
  disconnect()                         断开
  submit_order(order) -> str           下单，返回 broker 内部 order_id
  cancel_order(order_id) -> bool       撤单
  get_positions() -> Dict[symbol, qty] 持仓
  get_account() -> AccountState        资金
  on_fill(callback)                    注册成交回报回调

实现:
  PaperBroker   本地按行情模拟成交
  IBKRBroker    真实 IBKR TWS（stub）
  BinanceBroker 真实 Binance API（stub）
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, Optional


@dataclass
class AccountState:
    cash: float = 0.0
    equity: float = 0.0
    margin_used: float = 0.0
    buying_power: float = 0.0


class BrokerAdapter(ABC):
    """
    所有 broker 的统一接口
    策略只调 ABC 方法
    """

    name: str = "BASE"

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def submit_order(self, order) -> str: ...

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool: ...

    @abstractmethod
    def get_positions(self) -> Dict[str, int]: ...

    @abstractmethod
    def get_account(self) -> AccountState: ...

    # V3.1 兼容旧接口：on_fill 允许 None
    def on_fill(self, callback: Optional[Callable]) -> None:
        self._fill_callback = callback

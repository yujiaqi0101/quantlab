"""
Broker Abstraction — 统一 Broker 接口

T1 第一模块：所有交易所/模拟器统一接口

  PaperBroker()     — 模拟成交
  BinanceBroker()   — 币安实盘
  OKXBroker()       — OKX 实盘（未来）

用法：
    from quantlab.execution.broker import PaperBroker, BinanceBroker

    broker = PaperBroker()
    account = broker.get_account()
    positions = broker.get_positions()
    order_id = broker.submit_order(symbol="BTCUSDT", side="BUY", qty=0.1, price=50000)
    broker.cancel_order(order_id)
    open_orders = broker.get_open_orders()
"""

from .base import Broker, AccountInfo, PositionInfo, OrderRequest, OrderResponse, BrokerType
from .paper import PaperBroker
from .binance import BinanceBroker

__all__ = [
    "Broker",
    "AccountInfo",
    "PositionInfo",
    "OrderRequest",
    "OrderResponse",
    "BrokerType",
    "PaperBroker",
    "BinanceBroker",
]

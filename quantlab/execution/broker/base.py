"""
Broker Base — 统一 Broker 抽象基类

所有 Broker（Paper / Binance / OKX）必须实现此接口
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.broker")


class BrokerType(str, Enum):
    PAPER = "PAPER"
    BINANCE = "BINANCE"
    OKX = "OKX"


@dataclass
class AccountInfo:
    """账户信息"""
    broker: str = ""
    account_id: str = ""
    cash: float = 0.0
    equity: float = 0.0
    margin: float = 0.0
    margin_ratio: float = 0.0
    initial_capital: float = 0.0
    updated_at: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker": self.broker,
            "account_id": self.account_id,
            "cash": self.cash,
            "equity": self.equity,
            "margin": self.margin,
            "margin_ratio": self.margin_ratio,
            "initial_capital": self.initial_capital,
            "updated_at": self.updated_at or int(time.time() * 1000),
        }


@dataclass
class PositionInfo:
    """持仓信息（从 Broker 视角）"""
    symbol: str = ""
    qty: float = 0.0
    avg_price: float = 0.0
    market_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    side: str = ""  # LONG / SHORT / FLAT
    leverage: float = 1.0
    updated_at: int = 0

    @property
    def market_value(self) -> float:
        return self.qty * self.market_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_price": self.avg_price,
            "market_price": self.market_price,
            "market_value": self.market_value,
            "unrealized_pnl": self.unrealized_pnl,
            "realized_pnl": self.realized_pnl,
            "side": self.side,
            "leverage": self.leverage,
            "updated_at": self.updated_at or int(time.time() * 1000),
        }


@dataclass
class OrderRequest:
    """下单请求"""
    symbol: str
    side: str          # BUY / SELL
    qty: float
    order_type: str = "MARKET"   # MARKET / LIMIT / STOP
    price: Optional[float] = None
    stop_price: Optional[float] = None
    client_order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    strategy_id: str = ""
    signal_id: str = ""
    time_in_force: str = "GTC"   # GTC / IOC / FOK

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "order_type": self.order_type,
            "price": self.price,
            "stop_price": self.stop_price,
            "client_order_id": self.client_order_id,
            "strategy_id": self.strategy_id,
            "signal_id": self.signal_id,
            "time_in_force": self.time_in_force,
        }


@dataclass
class OrderResponse:
    """下单响应"""
    broker_order_id: str = ""
    client_order_id: str = ""
    status: str = "SUBMITTED"     # SUBMITTED / REJECTED / FILLED
    reject_reason: str = ""
    timestamp: int = 0
    broker: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "status": self.status,
            "reject_reason": self.reject_reason,
            "timestamp": self.timestamp or int(time.time() * 1000),
            "broker": self.broker,
        }


@dataclass
class OpenOrder:
    """挂单"""
    broker_order_id: str = ""
    client_order_id: str = ""
    symbol: str = ""
    side: str = ""
    qty: float = 0.0
    filled_qty: float = 0.0
    price: Optional[float] = None
    order_type: str = "MARKET"
    status: str = "SUBMITTED"
    timestamp: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "filled_qty": self.filled_qty,
            "price": self.price,
            "order_type": self.order_type,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class Broker(ABC):
    """
    统一 Broker 接口

    所有 Broker 必须实现：
        get_account()       — 账户信息
        get_positions()     — 持仓列表
        submit_order()      — 下单
        cancel_order()      — 撤单
        get_open_orders()   — 挂单
    """

    broker_type: BrokerType = BrokerType.PAPER

    def __init__(self, account_id: str = "") -> None:
        self.account_id = account_id or f"ACCT-{uuid.uuid4().hex[:8]}"

    @property
    def name(self) -> str:
        return self.broker_type.value

    @abstractmethod
    def get_account(self) -> AccountInfo:
        """获取账户信息"""
        ...

    @abstractmethod
    def get_positions(self) -> List[PositionInfo]:
        """获取持仓列表"""
        ...

    @abstractmethod
    def submit_order(self, req: OrderRequest) -> OrderResponse:
        """提交订单"""
        ...

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        """取消订单"""
        ...

    @abstractmethod
    def get_open_orders(self, symbol: str = "") -> List[OpenOrder]:
        """获取挂单"""
        ...

    # 可选方法（默认实现）
    def get_market_price(self, symbol: str) -> float:
        """获取市场价格（默认 0，由子类实现）"""
        return 0.0

    def update_market_prices(self, prices: Dict[str, float]) -> None:
        """更新市场价格（Paper Broker 用）"""
        pass

    def health_check(self) -> bool:
        """健康检查"""
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "broker_type": self.broker_type.value,
            "account_id": self.account_id,
            "healthy": self.health_check(),
        }

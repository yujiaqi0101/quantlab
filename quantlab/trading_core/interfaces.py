"""
统一策略接口与数据结构 (interfaces)
=================================

定义 Trading Core 的核心抽象：
    - Bar               单根K线/行情快照
    - OrderIntent       策略产出的订单意图（非OMS订单）
    - Position          持仓（策略视图）
    - TradingContext    策略运行上下文
    - EventStrategy     统一事件驱动策略接口

三模式（Backtest/Paper/Live）共享此接口。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

__all__ = [
    "Bar",
    "OrderIntent",
    "Position",
    "TradingContext",
    "EventStrategy",
]


@dataclass
class Bar:
    """单根K线/行情快照。

    Attributes:
        timestamp: 行情时间戳
        symbol: 标的代码
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
    """
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class OrderIntent:
    """策略产出的订单意图（非OMS订单）。

    策略通过 on_bar/on_exit 返回 OrderIntent 列表，
    由 TradingCore._submit_intent 转换为 OMSOrder 并提交 Broker。

    Attributes:
        symbol: 标的代码
        side: 买卖方向 ('buy' / 'sell')
        quantity: 数量（正数）
        order_type: 订单类型 ('market' / 'limit')
        price: 限价单价格（order_type='limit' 时必填）
        reason: 下单原因（用于审计/日志）
    """
    symbol: str
    side: str  # 'buy' / 'sell'
    quantity: float
    order_type: str = "market"  # 'market' / 'limit'
    price: Optional[float] = None
    reason: str = ""


@dataclass
class Position:
    """持仓（策略视图）。

    与 execution/position_book.Position 不同，这是给策略使用的简化视图，
    包含入场日期和方向等额外字段。

    Attributes:
        symbol: 标的代码
        quantity: 持仓数量（正数多头，负数空头）
        entry_price: 入场均价
        entry_date: 入场日期（字符串形式）
        current_price: 当前市价
        direction: 持仓方向 ('long' / 'short')
    """
    symbol: str
    quantity: float
    entry_price: float
    entry_date: str
    current_price: float
    direction: str = "long"

    @property
    def value(self) -> float:
        """持仓市值。"""
        return self.quantity * self.current_price

    @property
    def cost(self) -> float:
        """持仓成本。"""
        return self.quantity * self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        """未实现盈亏。"""
        return self.value - self.cost


@dataclass
class TradingContext:
    """策略运行上下文。

    每次 on_bar/on_exit 调用时由 TradingCore 构造，
    包含当前账户状态、持仓、历史K线缓冲等。

    Attributes:
        timestamp: 当前时间戳
        cash: 可用现金
        frozen_cash: 冻结现金（挂单占用）
        positions: 当前持仓 {symbol: Position}
        bar_data: 历史K线缓冲 {symbol: DataFrame}，按日期升序
        universe: 当前策略池
    """
    timestamp: datetime
    cash: float
    frozen_cash: float
    positions: Dict[str, Position]
    bar_data: Dict[str, pd.DataFrame]
    universe: List[str]

    @property
    def total_value(self) -> float:
        """总资产 = 现金 + 冻结现金 + 持仓市值。"""
        return (
            self.cash
            + self.frozen_cash
            + sum(p.value for p in self.positions.values())
        )


class EventStrategy(ABC):
    """统一事件驱动策略接口。Backtest/Paper/Live 三模式共用。

    子类必须实现：
        - on_bar(bar, ctx) -> List[OrderIntent]   每根K线到来时调用
        - on_exit(ctx) -> List[OrderIntent]       检查出场条件

    可选覆盖：
        - on_init()                                初始化钩子
    """

    name: str = "event_strategy"
    version: str = "1.0"

    @abstractmethod
    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        """每根K线/Tick到来时调用，返回订单意图列表。

        Args:
            bar: 当前K线
            ctx: 运行上下文（账户/持仓/历史数据）

        Returns:
            订单意图列表（空列表表示不下单）
        """
        ...

    @abstractmethod
    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        """检查持仓出场条件，返回出场订单意图。

        在 on_bar 之前调用，用于独立管理出场逻辑。

        Args:
            ctx: 运行上下文

        Returns:
            出场订单意图列表
        """
        ...

    def on_init(self) -> None:
        """策略初始化钩子（可选覆盖）。"""
        return None

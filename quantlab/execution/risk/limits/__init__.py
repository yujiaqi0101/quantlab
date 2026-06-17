"""
Risk Limits — 风险限额

所有订单必须经过 Risk Engine 检查
限额类型：
  1. PositionLimit — 单标的持仓上限
  2. ExposureLimit — 总敞口上限
  3. LossLimit — 日亏损上限
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional


class RiskLimit(ABC):
    """风险限额基类"""

    name: str = "BASE"

    @abstractmethod
    def check(
        self,
        order_qty: int,
        symbol: str,
        current_positions: Dict[str, float],
        current_equity: float,
        price: float = 0.0,
        daily_pnl: float = 0.0,
    ) -> tuple[bool, str]:
        """返回 (通过, 原因)"""
        ...


@dataclass
class PositionLimit(RiskLimit):
    """单标的持仓上限"""
    max_qty: int = 10000
    name: str = "POSITION_LIMIT"

    def check(self, order_qty, symbol, current_positions, current_equity, price=0.0, daily_pnl=0.0):
        current = current_positions.get(symbol, 0)
        new_qty = current + order_qty
        if abs(new_qty) > self.max_qty:
            return False, f"Position limit: {symbol} {new_qty} > {self.max_qty}"
        return True, ""


@dataclass
class ExposureLimit(RiskLimit):
    """总敞口上限（占净值比例）"""
    max_exposure: float = 1.0  # 100%
    name: str = "EXPOSURE_LIMIT"

    def check(self, order_qty, symbol, current_positions, current_equity, price=0.0, daily_pnl=0.0):
        if current_equity <= 0 or price <= 0:
            return True, ""

        current_exposure = sum(
            abs(qty) * price for qty in current_positions.values()
        ) / current_equity

        order_value = abs(order_qty) * price
        new_exposure = current_exposure + order_value / current_equity

        if new_exposure > self.max_exposure:
            return False, f"Exposure limit: {new_exposure:.2%} > {self.max_exposure:.2%}"
        return True, ""


@dataclass
class LossLimit(RiskLimit):
    """日亏损上限"""
    max_loss: float = -0.05  # -5%
    name: str = "LOSS_LIMIT"

    def check(self, order_qty, symbol, current_positions, current_equity, price=0.0, daily_pnl=0.0):
        if current_equity <= 0:
            return True, ""
        pnl_pct = daily_pnl / current_equity
        if pnl_pct <= self.max_loss:
            return False, f"Loss limit: daily PnL {pnl_pct:.2%} <= {self.max_loss:.2%}"
        return True, ""


@dataclass
class MaxOrderSize(RiskLimit):
    """单笔订单上限"""
    max_qty: int = 1000
    name: str = "MAX_ORDER_SIZE"

    def check(self, order_qty, symbol, current_positions, current_equity, price=0.0, daily_pnl=0.0):
        if abs(order_qty) > self.max_qty:
            return False, f"Order size: {abs(order_qty)} > {self.max_qty}"
        return True, ""


@dataclass
class ConsecutiveLossLimit(RiskLimit):
    """连续亏损次数上限"""
    max_consecutive: int = 5
    current_streak: int = 0
    name: str = "CONSECUTIVE_LOSS"

    def check(self, order_qty, symbol, current_positions, current_equity, price=0.0, daily_pnl=0.0):
        if self.current_streak >= self.max_consecutive:
            return False, f"Consecutive loss: {self.current_streak} >= {self.max_consecutive}"
        return True, ""

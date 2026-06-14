"""
Limits：风险限额数据类

V3.1：迁移自 risk/limits.py
"""

from dataclasses import dataclass


@dataclass
class MaxPositionLimit:
    """单 symbol 最大持仓（绝对量）"""
    symbol: str
    max_qty: int

    def check(self, current_qty: int, new_qty: int) -> bool:
        return abs(new_qty) <= self.max_qty


@dataclass
class MaxDailyLoss:
    """当日最大亏损限额（负数）"""
    max_loss: float
    current_pnl: float = 0.0

    def check(self) -> bool:
        return self.current_pnl >= self.max_loss

    def update(self, pnl_change: float) -> None:
        self.current_pnl += pnl_change


@dataclass
class MaxLeverage:
    """最大杠杆 = abs(gross_position_value) / equity"""
    max_leverage: float

    def check(
        self,
        equity: float,
        gross_position_value: float,
    ) -> bool:
        if equity <= 0:
            return False
        return (
            abs(gross_position_value) / equity
            <= self.max_leverage
        )


@dataclass
class MaxOrderSize:
    """单笔最大下单量"""
    max_qty: int

    def check(self, qty: int) -> bool:
        return abs(qty) <= self.max_qty

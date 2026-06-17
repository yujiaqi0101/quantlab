"""
Slippage Model — 滑点模型

提供多种滑点模型用于 Paper Broker 升级：
  1. FixedSlippage — 固定滑点
  2. PercentageSlippage — 百分比滑点
  3. VolumeSlippage — 基于成交量的滑点（市场冲击）
  4. QueueSlippage — 基于排队位置的滑点
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


class SlippageModel(ABC):
    """滑点模型基类"""

    @abstractmethod
    def apply(
        self,
        price: float,
        side: str,           # BUY / SELL
        quantity: int,
        volume: float = 0.0,  # 市场成交量
    ) -> float:
        """返回滑点后的实际成交价"""
        ...


class FixedSlippage(SlippageModel):
    """固定滑点（绝对值）"""

    def __init__(self, slippage: float = 0.01):
        self.slippage = slippage

    def apply(self, price: float, side: str, quantity: int, volume: float = 0.0) -> float:
        if side == "BUY":
            return price + self.slippage
        else:
            return price - self.slippage


class PercentageSlippage(SlippageModel):
    """百分比滑点"""

    def __init__(self, rate: float = 0.0002):
        self.rate = rate

    def apply(self, price: float, side: str, quantity: int, volume: float = 0.0) -> float:
        if side == "BUY":
            return price * (1 + self.rate)
        else:
            return price * (1 - self.rate)


class VolumeSlippage(SlippageModel):
    """
    基于成交量的滑点模型（市场冲击）

    slippage = base_rate * sqrt(order_qty / market_volume)
    """

    def __init__(self, base_rate: float = 0.001, max_rate: float = 0.01):
        self.base_rate = base_rate
        self.max_rate = max_rate

    def apply(self, price: float, side: str, quantity: int, volume: float = 0.0) -> float:
        import math
        if volume <= 0:
            volume = max(quantity * 10, 1000)

        participation = quantity / volume
        rate = min(
            self.base_rate * math.sqrt(participation),
            self.max_rate,
        )
        if side == "BUY":
            return price * (1 + rate)
        else:
            return price * (1 - rate)


class QueueSlippage(SlippageModel):
    """
    基于排队位置的滑点模型

    模拟限价单排队：排队越靠后，成交概率越低，滑点越大
    """

    def __init__(self, tick_size: float = 0.01):
        self.tick_size = tick_size

    def apply(self, price: float, side: str, quantity: int, volume: float = 0.0) -> float:
        # 简化：排队导致的滑点 = tick_size * log(1 + qty/100)
        import math
        queue_penalty = self.tick_size * math.log(1 + quantity / 100)
        if side == "BUY":
            return price + queue_penalty
        else:
            return price - queue_penalty

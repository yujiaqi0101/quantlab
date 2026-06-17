"""
Market Impact Model — 市场冲击模型

核心：impact = f(order_size, volume, volatility)

典型模型：
  1. SquareRoot Impact Model（平方根冲击模型）
     - Almgren-Chriss 简化版
     - impact ∝ σ × √(Q/V)

  2. Linear Impact Model
     - impact ∝ Q/V

  3. Power Impact Model
     - impact ∝ (Q/V)^δ

大单 → 推动价格
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("quantlab.execution.fidelity.impact")


@dataclass
class ImpactResult:
    """冲击结果"""
    impact_bps: float          # 冲击（bps）
    impact_price: float        # 冲击导致的价格变动
    impact_cost: float         # 冲击成本（USD）
    permanent_impact: float    # 永久冲击
    temporary_impact: float    # 临时冲击
    model: str = ""

    def to_dict(self) -> Dict:
        return {
            "impact_bps": self.impact_bps,
            "impact_price": self.impact_price,
            "impact_cost": self.impact_cost,
            "permanent_impact": self.permanent_impact,
            "temporary_impact": self.temporary_impact,
            "model": self.model,
        }


class ImpactModel(ABC):
    """冲击模型基类"""

    @abstractmethod
    def calculate(
        self,
        order_qty: float,
        mid_price: float,
        volume: float,
        volatility: float,
        side: str = "BUY",
    ) -> ImpactResult:
        ...


class SquareRootImpactModel(ImpactModel):
    """
    平方根冲击模型（Almgren-Chriss 简化版）

    impact = σ × η × √(Q / V)

    其中：
      σ = 波动率
      Q = 订单量
      V = 市场成交量
      η = 冲击系数

    大单推动价格，但非线性
    """

    def __init__(
        self,
        eta: float = 0.1,          # 冲击系数
        permanent_ratio: float = 0.3,  # 永久冲击占比
    ) -> None:
        self.eta = eta
        self.permanent_ratio = permanent_ratio

    def calculate(
        self,
        order_qty: float,
        mid_price: float,
        volume: float,
        volatility: float,
        side: str = "BUY",
    ) -> ImpactResult:
        if volume <= 0 or order_qty <= 0:
            return ImpactResult(
                impact_bps=0, impact_price=0, impact_cost=0,
                permanent_impact=0, temporary_impact=0,
                model="sqrt",
            )

        # 参与率
        participation = order_qty / volume

        # 平方根冲击
        impact_bps = volatility * self.eta * math.sqrt(participation) * 10000

        # 价格变动
        direction = 1 if side == "BUY" else -1
        impact_price = mid_price * impact_bps / 10000 * direction

        # 成本
        impact_cost = abs(impact_price) * order_qty

        # 永久 vs 临时
        permanent = impact_bps * self.permanent_ratio
        temporary = impact_bps * (1 - self.permanent_ratio)

        return ImpactResult(
            impact_bps=impact_bps,
            impact_price=impact_price,
            impact_cost=impact_cost,
            permanent_impact=permanent,
            temporary_impact=temporary,
            model="sqrt",
        )


class LinearImpactModel(ImpactModel):
    """线性冲击模型：impact ∝ Q/V"""

    def __init__(self, coefficient: float = 0.001) -> None:
        self.coefficient = coefficient

    def calculate(
        self,
        order_qty: float,
        mid_price: float,
        volume: float,
        volatility: float,
        side: str = "BUY",
    ) -> ImpactResult:
        if volume <= 0 or order_qty <= 0:
            return ImpactResult(
                impact_bps=0, impact_price=0, impact_cost=0,
                permanent_impact=0, temporary_impact=0,
                model="linear",
            )

        participation = order_qty / volume
        impact_bps = self.coefficient * participation * 10000

        direction = 1 if side == "BUY" else -1
        impact_price = mid_price * impact_bps / 10000 * direction
        impact_cost = abs(impact_price) * order_qty

        return ImpactResult(
            impact_bps=impact_bps,
            impact_price=impact_price,
            impact_cost=impact_cost,
            permanent_impact=impact_bps * 0.5,
            temporary_impact=impact_bps * 0.5,
            model="linear",
        )


class PowerImpactModel(ImpactModel):
    """幂律冲击模型：impact ∝ (Q/V)^δ"""

    def __init__(self, delta: float = 0.6, coefficient: float = 0.1) -> None:
        self.delta = delta
        self.coefficient = coefficient

    def calculate(
        self,
        order_qty: float,
        mid_price: float,
        volume: float,
        volatility: float,
        side: str = "BUY",
    ) -> ImpactResult:
        if volume <= 0 or order_qty <= 0:
            return ImpactResult(
                impact_bps=0, impact_price=0, impact_cost=0,
                permanent_impact=0, temporary_impact=0,
                model="power",
            )

        participation = order_qty / volume
        impact_bps = self.coefficient * (participation ** self.delta) * volatility * 10000

        direction = 1 if side == "BUY" else -1
        impact_price = mid_price * impact_bps / 10000 * direction
        impact_cost = abs(impact_price) * order_qty

        return ImpactResult(
            impact_bps=impact_bps,
            impact_price=impact_price,
            impact_cost=impact_cost,
            permanent_impact=impact_bps * 0.4,
            temporary_impact=impact_bps * 0.6,
            model="power",
        )


class MarketImpactEngine:
    """
    市场冲击引擎

    用法：
        engine = MarketImpactEngine(model=SquareRootImpactModel())
        result = engine.evaluate(
            order_qty=10,
            mid_price=50000,
            volume=1000000,
            volatility=0.02,
            side="BUY",
        )
    """

    def __init__(self, model: ImpactModel = None) -> None:
        self.model = model or SquareRootImpactModel()
        self._history: list = []

    def evaluate(
        self,
        order_qty: float,
        mid_price: float,
        volume: float,
        volatility: float,
        side: str = "BUY",
    ) -> ImpactResult:
        result = self.model.calculate(
            order_qty=order_qty,
            mid_price=mid_price,
            volume=volume,
            volatility=volatility,
            side=side,
        )
        self._history.append({
            "order_qty": order_qty,
            "mid_price": mid_price,
            "volume": volume,
            "volatility": volatility,
            "side": side,
            "result": result.to_dict(),
        })
        return result

    def suggest_split(
        self,
        total_qty: float,
        mid_price: float,
        volume: float,
        volatility: float,
        max_impact_bps: float = 5.0,
    ) -> list:
        """
        建议拆单方案

        在不超过 max_impact_bps 的前提下，计算每笔最大下单量
        """
        splits = []
        remaining = total_qty

        while remaining > 0:
            # 二分搜索最大单笔量
            lo, hi = 0, remaining
            best_qty = remaining

            for _ in range(20):
                mid = (lo + hi) / 2
                result = self.model.calculate(
                    order_qty=mid,
                    mid_price=mid_price,
                    volume=volume,
                    volatility=volatility,
                )
                if result.impact_bps <= max_impact_bps:
                    best_qty = mid
                    lo = mid
                else:
                    hi = mid

            qty = min(best_qty, remaining)
            splits.append(qty)
            remaining -= qty

            if qty <= 0:
                break

        return splits

    def get_history(self, limit: int = 100) -> list:
        return self._history[-limit:]

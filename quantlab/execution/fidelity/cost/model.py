"""
Execution Cost Model — 交易成本系统

成本组成：
  1. 手续费（fee）
  2. 滑点（slippage）
  3. 冲击成本（impact）
  4. 机会成本（opportunity）

统一模型：total_cost = fee + slippage + impact + opportunity

没有这个：所有 Sharpe 都是假的
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..impact.model import ImpactResult, MarketImpactEngine

logger = logging.getLogger("quantlab.execution.fidelity.cost")


@dataclass
class CostBreakdown:
    """成本拆解"""
    fee_cost: float = 0.0           # 手续费
    slippage_cost: float = 0.0      # 滑点成本
    impact_cost: float = 0.0        # 冲击成本
    opportunity_cost: float = 0.0   # 机会成本
    funding_cost: float = 0.0       # 资金费率

    @property
    def total_cost(self) -> float:
        return (
            self.fee_cost
            + self.slippage_cost
            + self.impact_cost
            + self.opportunity_cost
            + self.funding_cost
        )

    @property
    def total_cost_bps(self) -> float:
        """相对成本（需要 notional）"""
        return 0  # 由外部计算

    def to_dict(self) -> Dict:
        return {
            "fee_cost": self.fee_cost,
            "slippage_cost": self.slippage_cost,
            "impact_cost": self.impact_cost,
            "opportunity_cost": self.opportunity_cost,
            "funding_cost": self.funding_cost,
            "total_cost": self.total_cost,
        }


@dataclass
class TradeCostRecord:
    """交易成本记录"""
    symbol: str
    side: str
    qty: float
    price: float
    notional: float
    costs: CostBreakdown
    timestamp: int = 0

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "price": self.price,
            "notional": self.notional,
            "costs": self.costs.to_dict(),
            "total_cost_bps": self.costs.total_cost / self.notional * 10000 if self.notional > 0 else 0,
            "timestamp": self.timestamp,
        }


class ExecutionCostModel:
    """
    交易成本系统

    用法：
        model = ExecutionCostModel(
            fee_rate=0.0004,         # 0.04%
            impact_engine=MarketImpactEngine(),
        )
        record = model.calculate(
            symbol="BTCUSDT",
            side="BUY",
            qty=10,
            price=50000,
            slippage_bps=2.0,
            volume=1000000,
            volatility=0.02,
        )
    """

    def __init__(
        self,
        fee_rate: float = 0.0004,           # 手续费率
        taker_fee_rate: float = 0.0006,     # taker 手续费率
        maker_fee_rate: float = 0.0002,     # maker 手续费率
        impact_engine: Optional[MarketImpactEngine] = None,
    ) -> None:
        self.fee_rate = fee_rate
        self.taker_fee_rate = taker_fee_rate
        self.maker_fee_rate = maker_fee_rate
        self.impact_engine = impact_engine or MarketImpactEngine()
        self._history: List[TradeCostRecord] = []

    def calculate(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        slippage_bps: float = 0.0,
        volume: float = 0,
        volatility: float = 0.0,
        is_maker: bool = False,
        opportunity_cost: float = 0.0,
        funding_cost: float = 0.0,
    ) -> TradeCostRecord:
        """计算完整交易成本"""
        notional = qty * price

        # 1. 手续费
        fee_rate = self.maker_fee_rate if is_maker else self.taker_fee_rate
        fee_cost = notional * fee_rate

        # 2. 滑点
        slippage_cost = notional * slippage_bps / 10000

        # 3. 冲击成本
        impact_cost = 0.0
        if volume > 0 and volatility > 0:
            impact_result = self.impact_engine.evaluate(
                order_qty=qty,
                mid_price=price,
                volume=volume,
                volatility=volatility,
                side=side,
            )
            impact_cost = impact_result.impact_cost

        # 4. 机会成本（外部传入）
        # 5. 资金费率
        costs = CostBreakdown(
            fee_cost=fee_cost,
            slippage_cost=slippage_cost,
            impact_cost=impact_cost,
            opportunity_cost=opportunity_cost,
            funding_cost=funding_cost,
        )

        import time
        record = TradeCostRecord(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            notional=notional,
            costs=costs,
            timestamp=int(time.time() * 1000),
        )

        self._history.append(record)
        return record

    def get_total_costs(self) -> CostBreakdown:
        """累计所有成本"""
        total = CostBreakdown()
        for r in self._history:
            total.fee_cost += r.costs.fee_cost
            total.slippage_cost += r.costs.slippage_cost
            total.impact_cost += r.costs.impact_cost
            total.opportunity_cost += r.costs.opportunity_cost
            total.funding_cost += r.costs.funding_cost
        return total

    def get_avg_cost_bps(self) -> Dict:
        """平均成本（bps）"""
        if not self._history:
            return {"fee": 0, "slippage": 0, "impact": 0, "total": 0}

        total_notional = sum(r.notional for r in self._history)
        total = self.get_total_costs()

        return {
            "fee_bps": total.fee_cost / total_notional * 10000 if total_notional > 0 else 0,
            "slippage_bps": total.slippage_cost / total_notional * 10000 if total_notional > 0 else 0,
            "impact_bps": total.impact_cost / total_notional * 10000 if total_notional > 0 else 0,
            "opportunity_bps": total.opportunity_cost / total_notional * 10000 if total_notional > 0 else 0,
            "total_bps": total.total_cost / total_notional * 10000 if total_notional > 0 else 0,
            "trade_count": len(self._history),
        }

    def get_history(self, limit: int = 100) -> List[Dict]:
        return [r.to_dict() for r in self._history[-limit:]]

"""
Capital Allocator — 资金分配引擎

功能：
  1. 策略级资金分配（strategy_allocation）
  2. 风险预算（每个策略最大风险）
  3. 动态调仓（策略权重调整）
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.capital.allocator")


@dataclass
class StrategyAllocation:
    """单个策略的资金分配"""
    strategy_id: str
    capital: float              # 分配资金
    weight: float               # 权重 (0~1)
    max_risk: float = 0.0       # 最大风险预算 (e.g. 0.02 = 2%)
    max_leverage: float = 1.0   # 最大杠杆
    current_pnl: float = 0.0    # 当前盈亏
    active: bool = True

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "capital": self.capital,
            "weight": self.weight,
            "max_risk": self.max_risk,
            "max_leverage": self.max_leverage,
            "current_pnl": self.current_pnl,
            "active": self.active,
        }


class AllocationMethod(ABC):
    """分配方法基类"""

    @abstractmethod
    def allocate(
        self,
        total_capital: float,
        strategies: List[str],
        params: Dict = None,
    ) -> Dict[str, StrategyAllocation]:
        ...


class FixedAllocation(AllocationMethod):
    """固定权重分配"""

    def __init__(self, weights: Dict[str, float]):
        self.weights = weights

    def allocate(self, total_capital, strategies, params=None):
        result = {}
        for sid in strategies:
            w = self.weights.get(sid, 0.0)
            result[sid] = StrategyAllocation(
                strategy_id=sid,
                capital=total_capital * w,
                weight=w,
            )
        return result


class EqualAllocation(AllocationMethod):
    """等权分配"""

    def allocate(self, total_capital, strategies, params=None):
        n = len(strategies)
        if n == 0:
            return {}
        w = 1.0 / n
        return {
            sid: StrategyAllocation(
                strategy_id=sid,
                capital=total_capital * w,
                weight=w,
            )
            for sid in strategies
        }


class RiskParityAllocation(AllocationMethod):
    """风险平价分配 — 按风险贡献等权分配"""

    def __init__(self, risk_estimates: Dict[str, float]):
        """risk_estimates: {strategy_id: annual_volatility}"""
        self.risk_estimates = risk_estimates

    def allocate(self, total_capital, strategies, params=None):
        total_risk = sum(self.risk_estimates.get(s, 0.01) for s in strategies)
        if total_risk <= 0:
            return EqualAllocation().allocate(total_capital, strategies)

        result = {}
        for sid in strategies:
            vol = self.risk_estimates.get(sid, 0.01)
            w = (1.0 / vol) / sum(1.0 / self.risk_estimates.get(s, 0.01) for s in strategies)
            result[sid] = StrategyAllocation(
                strategy_id=sid,
                capital=total_capital * w,
                weight=w,
                max_risk=vol * w,
            )
        return result


class CapitalAllocator:
    """
    资金分配引擎

    用法：
        allocator = CapitalAllocator(
            total_capital=100000,
            method=EqualAllocation(),
        )
        allocator.set_strategies(["strat_1", "strat_2", "strat_3"])
        allocations = allocator.rebalance()
    """

    def __init__(
        self,
        total_capital: float,
        method: AllocationMethod = None,
    ) -> None:
        self.total_capital = total_capital
        self.method = method or EqualAllocation()
        self._strategies: List[str] = []
        self._allocations: Dict[str, StrategyAllocation] = {}
        self._pnl_history: Dict[str, List[float]] = {}

    def set_strategies(self, strategy_ids: List[str]) -> None:
        self._strategies = list(strategy_ids)
        self.rebalance()

    def set_method(self, method: AllocationMethod) -> None:
        self.method = method
        self.rebalance()

    def update_capital(self, total_capital: float) -> None:
        self.total_capital = total_capital
        self.rebalance()

    def update_pnl(self, strategy_id: str, pnl: float) -> None:
        """更新策略盈亏"""
        if strategy_id in self._allocations:
            self._allocations[strategy_id].current_pnl = pnl
        self._pnl_history.setdefault(strategy_id, []).append(pnl)

    def rebalance(self) -> Dict[str, StrategyAllocation]:
        """重新分配资金"""
        self._allocations = self.method.allocate(
            total_capital=self.total_capital,
            strategies=self._strategies,
        )
        logger.info(
            f"CapitalAllocator rebalanced: "
            f"{len(self._allocations)} strategies, "
            f"total={self.total_capital}"
        )
        return self._allocations

    def get_allocation(self, strategy_id: str) -> Optional[StrategyAllocation]:
        return self._allocations.get(strategy_id)

    def get_all_allocations(self) -> Dict[str, StrategyAllocation]:
        return dict(self._allocations)

    def activate_strategy(self, strategy_id: str) -> None:
        if strategy_id in self._allocations:
            self._allocations[strategy_id].active = True

    def deactivate_strategy(self, strategy_id: str) -> None:
        """停用策略（Kill Switch 用）"""
        if strategy_id in self._allocations:
            self._allocations[strategy_id].active = False
            logger.warning(f"Strategy deactivated: {strategy_id}")

    def total_allocated(self) -> float:
        return sum(
            a.capital for a in self._allocations.values() if a.active
        )

    def total_available(self) -> float:
        return self.total_capital - self.total_allocated()

    def to_dict(self) -> Dict:
        return {
            "total_capital": self.total_capital,
            "total_allocated": self.total_allocated(),
            "total_available": self.total_available(),
            "allocations": {
                k: v.to_dict() for k, v in self._allocations.items()
            },
        }

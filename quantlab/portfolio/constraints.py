"""
Portfolio Constraints — V4.6 组合约束

约束在 Allocator 输出后应用，确保组合满足风控要求：
  - MaxPositionConstraint: 单标的最大权重
  - MaxExposureConstraint: 总仓位上限
  - MinCashConstraint: 最小现金比例
  - MaxPositionsConstraint: 最大持仓数量

用法：
    constraints = [
        MaxPositionConstraint(max_weight=0.3),
        MaxExposureConstraint(max_gross=1.0),
        MinCashConstraint(min_cash=0.05),
    ]
    allocator = PortfolioAllocator(constraints=constraints)
"""

from __future__ import annotations

from typing import Dict, Tuple


class Constraint:
    """约束基类"""

    def apply(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        """
        应用约束

        返回: (调整后的 weights, 是否有调整)
        """
        return weights, False


class MaxPositionConstraint(Constraint):
    """
    单标的最大权重约束

    例: max_weight=0.2 → 任何标的不超过 20%
    超出部分按比例缩减
    """

    def __init__(self, max_weight: float = 0.2) -> None:
        self.max_weight = max_weight

    def apply(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        adjusted = False
        result = {}
        for sym, w in weights.items():
            if w > self.max_weight:
                result[sym] = self.max_weight
                adjusted = True
            else:
                result[sym] = w
        return result, adjusted


class MaxExposureConstraint(Constraint):
    """
    总仓位上限约束

    例: max_gross=1.0 → 总权重不超过 100%
    超出时按比例缩减
    """

    def __init__(self, max_gross: float = 1.0) -> None:
        self.max_gross = max_gross

    def apply(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        total = sum(weights.values())
        if total <= self.max_gross:
            return weights, False
        # 按比例缩减
        scale = self.max_gross / total
        return {s: w * scale for s, w in weights.items()}, True


class MinCashConstraint(Constraint):
    """
    最小现金比例约束

    例: min_cash=0.05 → 至少保留 5% 现金
    """

    def __init__(self, min_cash: float = 0.05) -> None:
        self.min_cash = min_cash

    def apply(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        total = sum(weights.values())
        max_exposure = 1.0 - self.min_cash
        if total <= max_exposure:
            return weights, False
        scale = max_exposure / total
        return {s: w * scale for s, w in weights.items()}, True


class MaxPositionsConstraint(Constraint):
    """
    最大持仓数量约束

    例: max_positions=5 → 最多持有 5 个标的
    超出时保留权重最大的 N 个
    """

    def __init__(self, max_positions: int = 5) -> None:
        self.max_positions = max_positions

    def apply(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        active = {s: w for s, w in weights.items() if w > 0}
        if len(active) <= self.max_positions:
            return weights, False
        # 保留权重最大的 N 个
        sorted_syms = sorted(active, key=lambda s: active[s], reverse=True)
        keep = set(sorted_syms[:self.max_positions])
        result = {s: w if s in keep else 0.0 for s, w in weights.items()}
        return result, True


class LongOnlyConstraint(Constraint):
    """
    多头约束：不允许做空

    所有负权重设为 0
    """

    def apply(self, weights: Dict[str, float]) -> Tuple[Dict[str, float], bool]:
        adjusted = False
        result = {}
        for s, w in weights.items():
            if w < 0:
                result[s] = 0.0
                adjusted = True
            else:
                result[s] = w
        return result, adjusted

"""
Portfolio Allocator — V4.6 信号→权重→目标仓位

PortfolioAllocator: Signal → Weight → TargetPosition

流程：
  1. 接收信号 Dict[symbol, signal_value]
  2. 用 WeightingModel 分配权重
  3. 用 Constraints 调整
  4. 输出 TargetPortfolio
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .models import TargetPortfolio
from .weighting import WeightingModel, EqualWeightModel

logger = logging.getLogger("quantlab.portfolio.allocator")


class PortfolioAllocator:
    """
    组合分配器

    Signal → WeightingModel → Constraints → TargetPortfolio

    用法：
        allocator = PortfolioAllocator(
            weighting=EqualWeightModel(),
            constraints=[MaxPositionConstraint(0.3), MaxExposureConstraint(1.0)],
        )
        target = allocator.allocate(signals, timestamp=ts)
    """

    def __init__(
        self,
        weighting: Optional[WeightingModel] = None,
        constraints: Optional[List] = None,
        source: str = "",
    ) -> None:
        self.weighting = weighting or EqualWeightModel()
        self.constraints = constraints or []
        self.source = source

    def allocate(
        self,
        signals: Dict[str, float],
        timestamp: Any = None,
    ) -> TargetPortfolio:
        """
        信号 → 目标组合

        1. WeightingModel 分配权重
        2. Constraints 调整
        3. 返回 TargetPortfolio
        """
        # Step 1: 权重分配
        weights = self.weighting.allocate(signals)

        if not weights:
            return TargetPortfolio(
                timestamp=timestamp,
                cash_weight=1.0,
                source=self.source,
            )

        # Step 2: 应用约束
        constraints_applied = []
        for constraint in self.constraints:
            name = type(constraint).__name__
            weights, applied = constraint.apply(weights)
            if applied:
                constraints_applied.append(name)

        # Step 3: 构建 TargetPortfolio
        total = sum(weights.values())
        cash_weight = max(0, 1.0 - total)

        return TargetPortfolio(
            timestamp=timestamp,
            positions=weights,
            cash_weight=cash_weight,
            source=self.source,
            constraints_applied=constraints_applied,
        )

    def allocate_series(
        self,
        signal_df: "pd.DataFrame",
    ) -> "pd.Series":
        """
        批量分配：对每根 bar 的信号行生成 TargetPortfolio

        输入: DataFrame(index=时间, columns=symbols, values=signal)
        输出: Series(index=时间, values=TargetPortfolio)
        """
        import pandas as pd
        results = {}
        for idx in signal_df.index:
            row = signal_df.loc[idx]
            signals = {sym: float(val) for sym, val in row.items()}
            results[idx] = self.allocate(signals, timestamp=idx)
        return pd.Series(results)

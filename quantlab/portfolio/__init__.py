"""
quantlab.portfolio — V4.6 Portfolio Construction Layer

四级架构：Factor → Signal → Portfolio Construction → Execution

Portfolio Construction 职责：
  Signal (离散 {-1, 0, 1}) → TargetPortfolio (权重) → Rebalance Orders

与旧 portfolio_construction/ 的关系：
  - 旧层只有 EqualWeight + TopN + TargetPortfolio
  - 新层增加了 WeightingModel 体系、Constraints、RebalanceEngine
  - 两者兼容，新代码推荐用 portfolio/
"""

from .models import TargetPosition, TargetPortfolio
from .weighting import (
    WeightingModel,
    EqualWeightModel,
    FixedWeightModel,
    SignalWeightModel,
    RiskParityModel,
    TopNWeightModel,
)
from .allocator import PortfolioAllocator
from .constraints import (
    Constraint,
    MaxPositionConstraint,
    MaxExposureConstraint,
    MinCashConstraint,
    MaxPositionsConstraint,
    LongOnlyConstraint,
)
from .rebalance import RebalanceEngine, RebalanceOrder, RebalanceResult


__all__ = [
    # models
    "TargetPosition",
    "TargetPortfolio",
    # weighting
    "WeightingModel",
    "EqualWeightModel",
    "FixedWeightModel",
    "SignalWeightModel",
    "RiskParityModel",
    "TopNWeightModel",
    # allocator
    "PortfolioAllocator",
    # constraints
    "Constraint",
    "MaxPositionConstraint",
    "MaxExposureConstraint",
    "MinCashConstraint",
    "MaxPositionsConstraint",
    "LongOnlyConstraint",
    # rebalance
    "RebalanceEngine",
    "RebalanceOrder",
    "RebalanceResult",
]

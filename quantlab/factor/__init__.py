"""
quantlab.factor — V4.6 Factor Platform

三级模型：Factor → Signal → Strategy

Factor:  per-symbol 时序因子值 (Factor.compute(df) → Series)
Signal:  因子 → 信号 (Signal.transform(factor_values) → Series ∈ {-1, 0, 1})
Strategy: 组合多个 Signal → 最终交易决策

与旧 quantlab.factors 的关系：
  - factors/ 是函数式接口: fn(ctx, symbol, **params) → Series
  - factor/ 是类式接口: Factor.compute(df) → Series
  - 两者共存，新代码推荐用 factor/
"""

from .base import Factor, CompositeFactor
from .registry import FactorRegistry
from .factor_engine import FactorEngine
from . import operators

# 内置因子类
from .technical import (
    MAFactor,
    RSIFactor,
    MomentumFactor,
    ATRFactor,
    BOLLUpperFactor,
    BOLLLowerFactor,
    VOLFactor,
)
from .cross_sectional import (
    CrossSectionalRankFactor,
    CrossSectionalZScoreFactor,
)
from .fundamental import (
    PEFactor,
    PBFactor,
    MarketCapFactor,
)


__all__ = [
    # base
    "Factor",
    "CompositeFactor",
    # core
    "FactorRegistry",
    "FactorEngine",
    # operators
    "operators",
    # technical
    "MAFactor",
    "RSIFactor",
    "MomentumFactor",
    "ATRFactor",
    "BOLLUpperFactor",
    "BOLLLowerFactor",
    "VOLFactor",
    # cross_sectional
    "CrossSectionalRankFactor",
    "CrossSectionalZScoreFactor",
    # fundamental
    "PEFactor",
    "PBFactor",
    "MarketCapFactor",
]

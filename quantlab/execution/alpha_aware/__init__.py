"""
Execution-Aware Alpha Layer — 执行感知 Alpha 层

完整系统闭环：
  Research Alpha
    ↓
  ML Validation
    ↓
  Auto Research
    ↓
  Execution Fidelity Layer
    ↓
  Execution-Aware Alpha Layer  ← 本模块
    ↓
  Paper Trading
    ↓
  Live Trading
    ↓
  Observe Studio

这一层的本质意义：
  如果没有这一层：你在优化"数学正确性"
  有了这一层：你在优化"市场存活率"
"""

from .realizability import (
    AlphaMetrics,
    ExecutionConstraints,
    RealizabilityReport,
    AlphaRealizabilityEngine,
)
from .turnover import (
    TurnoverAnalysis,
    TurnoverPressureModel,
)
from .liquidity_filter import (
    LiquidityMetrics,
    FilterResult,
    FilterVerdict,
    LiquidityAlphaFilter,
)
from .sensitivity import (
    SensitivityScenario,
    SensitivityReport,
    ExecutionSensitivityTest,
)
from .latency_fragility import (
    LatencyScenario,
    LatencyFragilityReport,
    LatencyFragilityTest,
)
from .impact_backtest import (
    BacktestTrade,
    ImpactBacktestResult,
    MarketImpactBacktest,
)
from .adj_sharpe import (
    SharpeDecomposition,
    AdjustedSharpeReport,
    ExecutionAdjustedSharpe,
)
from .survival import (
    SurvivalInput,
    SurvivalReport,
    AlphaSurvivalFilter,
)
from .features import (
    FeatureContext,
    AdjustedFeature,
    ExecutionAwareFeatureEngine,
)
from .tradeability import (
    TradeabilityScores,
    TradeabilityReport,
    TradeabilityScoreSystem,
)

__all__ = [
    # 模块 1：Alpha Realizability Engine
    "AlphaMetrics",
    "ExecutionConstraints",
    "RealizabilityReport",
    "AlphaRealizabilityEngine",
    # 模块 2：Turnover Pressure Model
    "TurnoverAnalysis",
    "TurnoverPressureModel",
    # 模块 3：Liquidity-Aware Alpha Filter
    "LiquidityMetrics",
    "FilterResult",
    "FilterVerdict",
    "LiquidityAlphaFilter",
    # 模块 4：Execution Sensitivity Test
    "SensitivityScenario",
    "SensitivityReport",
    "ExecutionSensitivityTest",
    # 模块 5：Latency Fragility Test
    "LatencyScenario",
    "LatencyFragilityReport",
    "LatencyFragilityTest",
    # 模块 6：Market Impact Backtest
    "BacktestTrade",
    "ImpactBacktestResult",
    "MarketImpactBacktest",
    # 模块 7：Execution-Adjusted Sharpe
    "SharpeDecomposition",
    "AdjustedSharpeReport",
    "ExecutionAdjustedSharpe",
    # 模块 8：Alpha Survival Filter
    "SurvivalInput",
    "SurvivalReport",
    "AlphaSurvivalFilter",
    # 模块 9：Execution-Aware Feature Engineering
    "FeatureContext",
    "AdjustedFeature",
    "ExecutionAwareFeatureEngine",
    # 模块 10：Tradeability Score System
    "TradeabilityScores",
    "TradeabilityReport",
    "TradeabilityScoreSystem",
]

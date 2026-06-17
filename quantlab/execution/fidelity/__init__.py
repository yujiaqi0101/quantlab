"""
Execution Fidelity Layer — 执行真实性层

目标：让纸上交易的行为 ≈ 真实交易行为

10 个模块：
  1. Fill Engine V2（成交引擎升级版）
  2. Market Impact Model（冲击模型）
  3. Order Book Simulation（订单簿模拟）
  4. Latency Model（延迟模型）
  5. Execution Cost Model（交易成本系统）
  6. Fill Reconciliation 2.0（成交对账升级）
  7. Event Replay Engine V2（生产级回放）
  8. Execution Shadow Mode（影子模式）
  9. Adaptive Execution Engine（自适应执行）
  10. Execution Truth Layer（执行真值层）

架构：
  Signal
    ↓
  Runtime
    ↓
  Risk
    ↓
  OMS
    ↓
  Fill Engine
    ↓
  Market Impact
    ↓
  Latency Model
    ↓
  Broker / Exchange
    ↓
  True PnL Layer
"""

from .orderbook.simulator import OrderBookSimulator, OrderBookSnapshot, PriceLevel
from .orderbook.liquidity_model import LiquidityModel, LiquidityProfile
from .impact.model import (
    ImpactModel,
    ImpactResult,
    SquareRootImpactModel,
    LinearImpactModel,
    PowerImpactModel,
    MarketImpactEngine,
)
from .latency.model import LatencyProfile, LatencyMeasurement, LatencySimulator
from .cost.model import ExecutionCostModel, CostBreakdown, TradeCostRecord
from .matcher import MatchingEngine, MatchResult
from .fill_engine import FillEngineV2, FillResult
from .reconciliation import (
    FillReconciliationV2,
    ReconciliationReport,
    FillDiff,
    PositionDiff,
)
from .replay import (
    DeterministicReplayEngine,
    ReplayEvent,
    ReplayConfig,
    ReplayState,
    ReplayCheckpoint,
)
from .shadow import ShadowModeEngine, ShadowComparison
from .adaptive import (
    AdaptiveExecutionEngine,
    ExecutionPlan,
    MarketState,
    MarketRegime,
    ExecutionStyle,
)
from .truth import ExecutionTruthLayer, TruePnLReport, PositionTruePnL

__all__ = [
    # Order Book
    "OrderBookSimulator",
    "OrderBookSnapshot",
    "PriceLevel",
    "LiquidityModel",
    "LiquidityProfile",
    # Impact
    "ImpactModel",
    "ImpactResult",
    "SquareRootImpactModel",
    "LinearImpactModel",
    "PowerImpactModel",
    "MarketImpactEngine",
    # Latency
    "LatencyProfile",
    "LatencyMeasurement",
    "LatencySimulator",
    # Cost
    "ExecutionCostModel",
    "CostBreakdown",
    "TradeCostRecord",
    # Matcher
    "MatchingEngine",
    "MatchResult",
    # Fill Engine
    "FillEngineV2",
    "FillResult",
    # Reconciliation
    "FillReconciliationV2",
    "ReconciliationReport",
    "FillDiff",
    "PositionDiff",
    # Replay
    "DeterministicReplayEngine",
    "ReplayEvent",
    "ReplayConfig",
    "ReplayState",
    "ReplayCheckpoint",
    # Shadow
    "ShadowModeEngine",
    "ShadowComparison",
    # Adaptive
    "AdaptiveExecutionEngine",
    "ExecutionPlan",
    "MarketState",
    "MarketRegime",
    "ExecutionStyle",
    # Truth
    "ExecutionTruthLayer",
    "TruePnLReport",
    "PositionTruePnL",
]

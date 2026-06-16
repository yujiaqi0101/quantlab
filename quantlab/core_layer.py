"""
QuantLab V2.0 — 五层架构

Layer 1: core      — 纯领域模型，零外部依赖
Layer 2: research  — 研究能力（实验/优化/分析）
Layer 3: services  — 统一业务入口（API 只调 services）
Layer 4: studio    — 前端接口（FastAPI + WebSocket）
Layer 5: infra     — 基础设施（存储/缓存/队列/事件）

依赖规则（只允许向下依赖）：
  studio  → services → research → core
  studio  → services → core
  studio  → infra
  services → infra
  research → infra
  core     → 无（零依赖）

用法：
    from quantlab.core import Factor, Signal, Strategy
    from quantlab.services import FactorService, StrategyService
    from quantlab.infra import EventBus, ArtifactStore
"""

# ============================================================
# Layer 1: core — 纯领域模型
# ============================================================

# --- Engine ---
from .core.base_engine import BaseBacktestEngine
from .core.backtest_result import BacktestResult

# --- Domain Objects ---
from .core.order import Order
from .core.trade import ClosedTrade, TradeBuilder
from .core.position import Position
from .core.portfolio import Portfolio
from .core.portfolio_snapshot import PortfolioSnapshot
from .core.tick import Tick
from .core.fill import Fill
from .core.tradebook import TradeBook

# --- Factor ---
from .factor.base import Factor
from .factor.registry import FactorRegistry
from .factor.factor_engine import FactorEngine

# --- Signal ---
from .signal.base import Signal, MultiFactorSignal
from .signal.signal_engine import SignalEngine
from .signal.threshold import ThresholdSignal
from .signal.crossover import CrossoverSignal, ZeroCrossoverSignal
from .signal.composite import AndSignal, OrSignal, NotSignal, MajoritySignal
from .signal.builder import SignalBuilder

# --- Strategy ---
from .strategy.base import BaseStrategy
from .strategy.registry import StrategyRegistry
from .strategy_builder import StrategySpec, StrategyCompiler, StrategyBuilder as StrategyBuilderFacade

# --- Portfolio Construction ---
from .portfolio.models import TargetPosition, TargetPortfolio
from .portfolio.allocator import PortfolioAllocator
from .portfolio.weighting import WeightingModel, EqualWeightModel

__core_all__ = [
    # Engine
    "BaseBacktestEngine", "BacktestResult",
    # Domain
    "Order", "ClosedTrade", "TradeBuilder", "Position", "Portfolio", "PortfolioSnapshot",
    "Tick", "Fill", "TradeBook",
    # Factor
    "Factor", "FactorRegistry", "FactorEngine",
    # Signal
    "Signal", "MultiFactorSignal", "SignalEngine",
    "ThresholdSignal", "CrossoverSignal", "ZeroCrossoverSignal",
    "AndSignal", "OrSignal", "NotSignal", "MajoritySignal", "SignalBuilder",
    # Strategy
    "BaseStrategy", "StrategyRegistry", "StrategySpec", "StrategyCompiler", "StrategyBuilderFacade",
    # Portfolio
    "TargetPosition", "TargetPortfolio", "PortfolioAllocator", "WeightingModel", "EqualWeightModel",
]

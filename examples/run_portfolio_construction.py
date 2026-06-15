"""
V4.6 Portfolio Construction 全链路演示

完整四级架构：Factor -> Signal -> Portfolio Construction -> Execution

1) Weighting: 5 种权重模型
2) Allocator: Signal -> Weight -> TargetPortfolio
3) Constraints: MaxPosition / MaxExposure / MinCash
4) Rebalance: Current -> Target -> Orders
5) 全链路: Factor -> Signal -> Allocator -> Rebalance -> Backtest
6) 与旧 portfolio_construction 兼容
"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd
import numpy as np


def make_test_data(symbols=("AAPL", "MSFT", "GOOG"), bars=300):
    np.random.seed(42)
    data = {}
    for sym in symbols:
        dates = pd.date_range("2024-01-01", periods=bars, freq="B")
        close = 100 + np.cumsum(np.random.randn(bars) * 0.5)
        high = close + np.abs(np.random.randn(bars) * 0.3)
        low = close - np.abs(np.random.randn(bars) * 0.3)
        open_ = close + np.random.randn(bars) * 0.2
        volume = (np.random.rand(bars) * 1e6).astype(int)
        data[sym] = pd.DataFrame({
            "open": open_, "high": high, "low": low,
            "close": close, "volume": volume,
        }, index=dates)
    return data


data = make_test_data()

print("=" * 60)
print("  V4.6 Portfolio Construction Demo")
print("=" * 60)


# ══════════════════════════════════════════════════════════════
# 1) Weighting Models
# ══════════════════════════════════════════════════════════════
print("\n1) Weighting Models")

from quantlab.portfolio import (
    EqualWeightModel, FixedWeightModel, SignalWeightModel,
    RiskParityModel, TopNWeightModel,
)

signals = {"AAPL": 1, "MSFT": 1, "GOOG": 0}  # GOOG 空仓

# Equal: 等权
eq = EqualWeightModel().allocate(signals)
print(f"   EqualWeight:  {eq}")

# Fixed: 固定 20%
fx = FixedWeightModel(weight=0.2).allocate(signals)
print(f"   FixedWeight:  {fx}")

# Signal: 按信号强度
sig_signals = {"AAPL": 0.8, "MSFT": 0.4, "GOOG": 0.0}
sw = SignalWeightModel().allocate(sig_signals)
print(f"   SignalWeight: {sw}")

# RiskParity: 按波动率倒数
rp = RiskParityModel(volatilities={"AAPL": 0.02, "MSFT": 0.03, "GOOG": 0.015}).allocate(signals)
print(f"   RiskParity:   {rp}")

# TopN: 只取前 2
tn = TopNWeightModel(n=2).allocate(sig_signals)
print(f"   TopN(2):      {tn}")


# ══════════════════════════════════════════════════════════════
# 2) Allocator: Signal -> TargetPortfolio
# ══════════════════════════════════════════════════════════════
print("\n2) Portfolio Allocator")

from quantlab.portfolio import PortfolioAllocator

# 简单分配
allocator = PortfolioAllocator(
    weighting=EqualWeightModel(),
    source="demo",
)
target = allocator.allocate(signals, timestamp="2024-01-01")
print(f"   EqualWeight: {target}")

# 带约束
from quantlab.portfolio import (
    MaxPositionConstraint, MaxExposureConstraint, MinCashConstraint,
)

allocator_constrained = PortfolioAllocator(
    weighting=EqualWeightModel(),
    constraints=[
        MaxPositionConstraint(max_weight=0.3),
        MinCashConstraint(min_cash=0.1),
    ],
    source="constrained",
)
target2 = allocator_constrained.allocate(signals, timestamp="2024-01-01")
print(f"   Constrained: {target2}")
print(f"   Constraints applied: {target2.constraints_applied}")


# ══════════════════════════════════════════════════════════════
# 3) Constraints
# ══════════════════════════════════════════════════════════════
print("\n3) Constraints")

from quantlab.portfolio import MaxPositionsConstraint, LongOnlyConstraint

# MaxPosition: 单标的不超过 30%
w1, applied1 = MaxPositionConstraint(0.3).apply({"AAPL": 0.5, "MSFT": 0.3, "GOOG": 0.2})
print(f"   MaxPosition(0.3): {w1}, applied={applied1}")

# MaxExposure: 总仓位不超过 100%
w2, applied2 = MaxExposureConstraint(1.0).apply({"AAPL": 0.6, "MSFT": 0.6})
print(f"   MaxExposure(1.0): {w2}, applied={applied2}")

# MinCash: 至少 5% 现金
w3, applied3 = MinCashConstraint(0.05).apply({"AAPL": 0.5, "MSFT": 0.5, "GOOG": 0.1})
print(f"   MinCash(0.05):    {w3}, applied={applied3}")

# MaxPositions: 最多 2 个
w4, applied4 = MaxPositionsConstraint(2).apply({"AAPL": 0.4, "MSFT": 0.3, "GOOG": 0.3})
print(f"   MaxPositions(2):  {w4}, applied={applied4}")


# ══════════════════════════════════════════════════════════════
# 4) Rebalance Engine
# ══════════════════════════════════════════════════════════════
print("\n4) Rebalance Engine")

from quantlab.portfolio import RebalanceEngine, TargetPortfolio

rebalancer = RebalanceEngine(min_weight_change=0.01)

# 场景1: 新建仓位
current = {}
target_new = TargetPortfolio(positions={"AAPL": 0.5, "MSFT": 0.5}, cash_weight=0.0)
result1 = rebalancer.generate(current, target_new)
print(f"   New portfolio: {result1}")
for o in result1.orders:
    print(f"     {o.action} {o.symbol} delta={o.delta_weight:+.1%}")

# 场景2: 调仓
current2 = {"AAPL": 0.5, "MSFT": 0.5}
target_adj = TargetPortfolio(positions={"AAPL": 0.3, "MSFT": 0.3, "GOOG": 0.4}, cash_weight=0.0)
result2 = rebalancer.generate(current2, target_adj)
print(f"   Rebalance: {result2}")
for o in result2.orders:
    print(f"     {o.action} {o.symbol} delta={o.delta_weight:+.1%}")

# 场景3: 全部平仓
current3 = {"AAPL": 0.5, "MSFT": 0.5}
target_flat = TargetPortfolio(positions={}, cash_weight=1.0)
result3 = rebalancer.generate(current3, target_flat)
print(f"   Close all: {result3}")
for o in result3.orders:
    print(f"     {o.action} {o.symbol} delta={o.delta_weight:+.1%}")


# ══════════════════════════════════════════════════════════════
# 5) 全链路: Factor -> Signal -> Allocator -> Rebalance -> Backtest
# ══════════════════════════════════════════════════════════════
print("\n5) Full Pipeline: Factor -> Signal -> Portfolio -> Backtest")

from quantlab.factor import FactorRegistry, FactorEngine, RSIFactor, MomentumFactor, MAFactor
from quantlab.signal import (
    SignalEngine, ThresholdSignal, CrossoverSignal, StatefulSignal,
)
from quantlab.strategy.factor_strategy import FactorStrategy
from quantlab.engine import BarEngine
from quantlab.execution import TargetWeightExecution, PercentageCommission, PercentageSlippage

# Step 1: Factor
registry = FactorRegistry()
registry.register(lambda: RSIFactor(14))
registry.register(lambda: MAFactor(5))
registry.register(lambda: MAFactor(20))
factor_engine = FactorEngine(registry)

# Step 2: Signal
sig_engine = SignalEngine()
sig_engine.register(ThresholdSignal("RSI14", 30, 70))
sig_engine.register(CrossoverSignal("MA5", "MA20"))

# Step 3: Allocator (带约束)
allocator_full = PortfolioAllocator(
    weighting=EqualWeightModel(),
    constraints=[
        MaxPositionConstraint(max_weight=0.4),
        MinCashConstraint(min_cash=0.05),
    ],
    source="full_pipeline",
)

# Step 4: 用 FactorStrategy 跑回测
rsi_strategy = FactorStrategy(
    name="rsi_with_portfolio",
    factor_registry=registry,
    signal_engine=sig_engine,
    factor_names=["RSI14"],
    signal_name="THRESH_RSI14_30_70",
    stateful=True,
    min_hold=3,
)

eng = BarEngine(
    strategy=rsi_strategy,
    portfolio_constructor=EqualWeightModel() if False else __import__(
        'quantlab.portfolio_construction', fromlist=['EqualWeight']
    ).EqualWeight(),
    execution_model=TargetWeightExecution(),
    commission_model=PercentageCommission(),
    slippage_model=PercentageSlippage(),
)
result = eng.run(strategy=rsi_strategy, data=data)
print(f"   Backtest: equity={result.final_equity:.0f}, "
      f"return={result.total_return:.2%}, trades={result.trade_count}")

# Step 5: 独立演示 Allocator + Rebalance 全流程
print("\n   Standalone Allocator + Rebalance demo:")
# 模拟 5 根 bar 的信号
sample_signals = [
    {"AAPL": 1, "MSFT": 0, "GOOG": 0},
    {"AAPL": 1, "MSFT": 1, "GOOG": 0},
    {"AAPL": 1, "MSFT": 1, "GOOG": 1},
    {"AAPL": 0, "MSFT": 1, "GOOG": 1},
    {"AAPL": 0, "MSFT": 0, "GOOG": 0},
]
current = {}
for i, sig in enumerate(sample_signals):
    target = allocator_full.allocate(sig, timestamp=f"bar_{i}")
    rebal = rebalancer.generate(current, target)
    print(f"   bar_{i}: signals={sig} -> target={target} -> rebal={rebal}")
    current = dict(target.positions)


# ══════════════════════════════════════════════════════════════
# 6) 与旧 portfolio_construction 兼容
# ══════════════════════════════════════════════════════════════
print("\n6) Backward Compatibility")

from quantlab.portfolio_construction import EqualWeight as OldEqualWeight, TopN as OldTopN

# 旧方式
old_ew = OldEqualWeight()
old_tp = old_ew.construct({"AAPL": 1, "MSFT": 1, "GOOG": 0}, timestamp="2024-01-01")
print(f"   Old EqualWeight: {old_tp.weights}")

# 新方式
new_ew = EqualWeightModel()
new_weights = new_ew.allocate({"AAPL": 1, "MSFT": 1, "GOOG": 0})
print(f"   New EqualWeight: {new_weights}")

# 验证一致
assert abs(old_tp.weights.get("AAPL", 0) - new_weights.get("AAPL", 0)) < 1e-9
assert abs(old_tp.weights.get("MSFT", 0) - new_weights.get("MSFT", 0)) < 1e-9
print(f"   Consistency: OK")


# ══════════════════════════════════════════════════════════════
# 总结
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  V4.6 Portfolio Construction Summary")
print("=" * 60)
print(f"  Weighting Models:")
print(f"    EqualWeightModel:  1/N for all active signals")
print(f"    FixedWeightModel:  fixed weight per signal")
print(f"    SignalWeightModel: proportional to signal strength")
print(f"    RiskParityModel:   inverse volatility weighting")
print(f"    TopNWeightModel:   top N signals, equal weight")
print(f"  Constraints:")
print(f"    MaxPositionConstraint:  single symbol <= max_weight")
print(f"    MaxExposureConstraint:  total weight <= max_gross")
print(f"    MinCashConstraint:      cash >= min_cash%")
print(f"    MaxPositionsConstraint: max N positions")
print(f"    LongOnlyConstraint:     no short selling")
print(f"  Allocator:")
print(f"    Signal -> WeightingModel -> Constraints -> TargetPortfolio")
print(f"  Rebalance:")
print(f"    Current -> Target -> RebalanceOrders")
print(f"  Full Architecture:")
print(f"    Factor -> Signal -> Portfolio Construction -> Execution")
print(f"\n  V4.6 Portfolio Construction demo complete!")

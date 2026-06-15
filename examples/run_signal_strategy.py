"""
V4.6 Signal + Strategy 全链路演示

演示 Factor -> Signal -> Strategy -> Execution 完整流程

1) Factor: 计算因子值
2) Signal: 阈值/交叉/组合信号
3) Composite: AND/OR 多信号组合
4) Filters: Hold/Cooldown/Stateful 后处理
5) FactorStrategy: 因子策略跑回测
6) MultiFactorStrategy: 多因子横截面策略
7) 与旧 MACrossStrategy 对比
"""

import os
os.environ.setdefault("MPLBACKEND", "Agg")

import pandas as pd
import numpy as np


# ── 生成测试数据 ──────────────────────────────────────────────
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
print("  V4.6 Signal + Strategy Full Pipeline Demo")
print("=" * 60)


# ══════════════════════════════════════════════════════════════
# 1) Factor -> Signal: 单因子信号
# ══════════════════════════════════════════════════════════════
print("\n1) Factor -> Signal (single factor)")

from quantlab.factor import FactorRegistry, FactorEngine, RSIFactor, MomentumFactor, MAFactor
from quantlab.signal import (
    SignalEngine, ThresholdSignal, CrossoverSignal, ZeroCrossoverSignal,
)

# 注册因子
registry = FactorRegistry()
registry.register(lambda: RSIFactor(14))
registry.register(lambda: MomentumFactor(20))
registry.register(lambda: MAFactor(5))
registry.register(lambda: MAFactor(20))

engine = FactorEngine(registry)

# 注册信号
sig_engine = SignalEngine()
sig_engine.register(ThresholdSignal("RSI14", 30, 70))
sig_engine.register(CrossoverSignal("MA5", "MA20"))
sig_engine.register(ZeroCrossoverSignal("MOM20"))

# 计算 AAPL 的因子和信号
factor_values_aapl = engine.compute_batch(["RSI14", "MOM20", "MA5", "MA20"], data["AAPL"])

rsi_sig = sig_engine.transform_single(factor_values_aapl, "THRESH_RSI14_30_70")
cross_sig = sig_engine.transform_single(factor_values_aapl, "CROSS_MA5_MA20")
mom_sig = sig_engine.transform_single(factor_values_aapl, "ZERO_CROSS_MOM20")

print(f"   RSI threshold: 1={int((rsi_sig==1).sum())}, -1={int((rsi_sig==-1).sum())}, 0={int((rsi_sig==0).sum())}")
print(f"   MA crossover:  1={int((cross_sig==1).sum())}, -1={int((cross_sig==-1).sum())}, 0={int((cross_sig==0).sum())}")
print(f"   MOM zero cross: 1={int((mom_sig==1).sum())}, -1={int((mom_sig==-1).sum())}, 0={int((mom_sig==0).sum())}")


# ══════════════════════════════════════════════════════════════
# 2) Composite: AND/OR 多信号组合
# ══════════════════════════════════════════════════════════════
print("\n2) Composite Signals (AND / OR / Majority)")

from quantlab.signal import AndSignal, OrSignal, MajoritySignal, NotSignal

# AND: RSI 和 MOM 都看多才做多
and_sig = AndSignal(
    ThresholdSignal("RSI14", 30, 70),
    ZeroCrossoverSignal("MOM20"),
    name="RSI_AND_MOM",
)
and_result = and_sig.transform_multi_signal([rsi_sig, mom_sig])
print(f"   AND(RSI, MOM): 1={int((and_result==1).sum())}, -1={int((and_result==-1).sum())}, 0={int((and_result==0).sum())}")

# OR: 任一看多就做多
or_sig = OrSignal(
    ThresholdSignal("RSI14", 30, 70),
    ZeroCrossoverSignal("MOM20"),
    name="RSI_OR_MOM",
)
or_result = or_sig.transform_multi_signal([rsi_sig, mom_sig])
print(f"   OR(RSI, MOM):  1={int((or_result==1).sum())}, -1={int((or_result==-1).sum())}, 0={int((or_result==0).sum())}")

# Majority: 三信号投票
maj_sig = MajoritySignal(
    ThresholdSignal("RSI14", 30, 70),
    CrossoverSignal("MA5", "MA20"),
    ZeroCrossoverSignal("MOM20"),
    name="MAJ_3",
)
maj_result = maj_sig.transform_multi_signal([rsi_sig, cross_sig, mom_sig])
print(f"   MAJ(RSI,CROSS,MOM): 1={int((maj_result==1).sum())}, -1={int((maj_result==-1).sum())}, 0={int((maj_result==0).sum())}")

# NOT: 取反
not_sig = NotSignal(ThresholdSignal("RSI14", 30, 70))
not_result = not_sig.transform(rsi_sig)
print(f"   NOT(RSI): 1={int((not_result==1).sum())}, -1={int((not_result==-1).sum())}")


# ══════════════════════════════════════════════════════════════
# 3) Filters: Hold/Cooldown/Stateful
# ══════════════════════════════════════════════════════════════
print("\n3) Signal Filters")

from quantlab.signal import HoldFilter, CooldownFilter, StatefulSignal

# Stateful: 脉冲 -> 状态
stateful_cross = StatefulSignal().apply(cross_sig)
print(f"   Raw crossover:    1={int((cross_sig==1).sum())}, -1={int((cross_sig==-1).sum())}, 0={int((cross_sig==0).sum())}")
print(f"   Stateful cross:   1={int((stateful_cross==1).sum())}, -1={int((stateful_cross==-1).sum())}, 0={int((stateful_cross==0).sum())}")

# Hold: 至少持有 5 根 bar
hold_rsi = HoldFilter(min_hold=5).apply(rsi_sig)
print(f"   Hold(5) RSI:      1={int((hold_rsi==1).sum())}, -1={int((hold_rsi==-1).sum())}, 0={int((hold_rsi==0).sum())}")

# Cooldown: 平仓后冷却 10 根 bar
cool_rsi = CooldownFilter(cooldown_bars=10).apply(rsi_sig)
print(f"   Cooldown(10) RSI: 1={int((cool_rsi==1).sum())}, -1={int((cool_rsi==-1).sum())}, 0={int((cool_rsi==0).sum())}")


# ══════════════════════════════════════════════════════════════
# 4) FactorStrategy: RSI 阈值策略跑回测
# ══════════════════════════════════════════════════════════════
print("\n4) FactorStrategy: RSI Threshold Backtest")

from quantlab.strategy.factor_strategy import FactorStrategy
from quantlab.engine import BarEngine
from quantlab.portfolio_construction import EqualWeight
from quantlab.execution import TargetWeightExecution, PercentageCommission, PercentageSlippage

# 构建因子策略
rsi_strategy = FactorStrategy(
    name="rsi_threshold",
    factor_registry=registry,
    signal_engine=sig_engine,
    factor_names=["RSI14"],
    signal_name="THRESH_RSI14_30_70",
    stateful=True,       # 脉冲 -> 状态
    min_hold=5,          # 至少持有 5 bar
)

eng = BarEngine(
    strategy=rsi_strategy,
    portfolio_constructor=EqualWeight(),
    execution_model=TargetWeightExecution(),
    commission_model=PercentageCommission(),
    slippage_model=PercentageSlippage(),
)
result = eng.run(strategy=rsi_strategy, data=data)
print(f"   RSI Threshold: equity={result.final_equity:.0f}, "
      f"return={result.total_return:.2%}, trades={result.trade_count}")


# ══════════════════════════════════════════════════════════════
# 5) FactorStrategy: MA 交叉策略跑回测
# ══════════════════════════════════════════════════════════════
print("\n5) FactorStrategy: MA Crossover Backtest")

ma_strategy = FactorStrategy(
    name="ma_crossover",
    factor_registry=registry,
    signal_engine=sig_engine,
    factor_names=["MA5", "MA20"],
    signal_name="CROSS_MA5_MA20",
    stateful=True,       # 交叉信号必须转状态
    cooldown=5,          # 平仓后冷却 5 bar
)

eng2 = BarEngine(
    strategy=ma_strategy,
    portfolio_constructor=EqualWeight(),
    execution_model=TargetWeightExecution(),
    commission_model=PercentageCommission(),
    slippage_model=PercentageSlippage(),
)
result2 = eng2.run(strategy=ma_strategy, data=data)
print(f"   MA Crossover: equity={result2.final_equity:.0f}, "
      f"return={result2.total_return:.2%}, trades={result2.trade_count}")


# ══════════════════════════════════════════════════════════════
# 6) MultiFactorStrategy: 多因子横截面策略
# ══════════════════════════════════════════════════════════════
print("\n6) MultiFactorStrategy: Cross-Sectional Rank")

from quantlab.strategy.factor_strategy import MultiFactorStrategy

mf_strategy = MultiFactorStrategy(
    factor_registry=registry,
    factor_weights={"RSI14": -0.5, "MOM20": 0.5},  # RSI 越小越好，MOM 越大越好
    top_n=2,
)

eng3 = BarEngine(
    strategy=mf_strategy,
    portfolio_constructor=EqualWeight(),
    execution_model=TargetWeightExecution(),
    commission_model=PercentageCommission(),
    slippage_model=PercentageSlippage(),
)
result3 = eng3.run(strategy=mf_strategy, data=data)
print(f"   MultiFactor: equity={result3.final_equity:.0f}, "
      f"return={result3.total_return:.2%}, trades={result3.trade_count}")


# ══════════════════════════════════════════════════════════════
# 7) 与旧 MACrossStrategy 对比
# ══════════════════════════════════════════════════════════════
print("\n7) Compare: FactorStrategy vs Old MACrossStrategy")

from quantlab.signals import MACrossStrategy

old_strategy = MACrossStrategy(fast=5, slow=20)
eng4 = BarEngine(
    strategy=old_strategy,
    portfolio_constructor=EqualWeight(),
    execution_model=TargetWeightExecution(),
    commission_model=PercentageCommission(),
    slippage_model=PercentageSlippage(),
)
result4 = eng4.run(strategy=old_strategy, data=data)
print(f"   Old MACrossStrategy: equity={result4.final_equity:.0f}, "
      f"return={result4.total_return:.2%}, trades={result4.trade_count}")
print(f"   New FactorStrategy:  equity={result2.final_equity:.0f}, "
      f"return={result2.total_return:.2%}, trades={result2.trade_count}")


# ══════════════════════════════════════════════════════════════
# 总结
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  V4.6 Signal + Strategy Summary")
print("=" * 60)
print(f"  Signal Types:")
print(f"    ThresholdSignal:  RSI < 30 -> 1, RSI > 70 -> -1")
print(f"    CrossoverSignal:  MA5 crosses MA20")
print(f"    ZeroCrossover:    MOM crosses 0")
print(f"  Composite:")
print(f"    AndSignal:        both agree -> trigger")
print(f"    OrSignal:         either agree -> trigger")
print(f"    MajoritySignal:   majority vote")
print(f"    NotSignal:        invert")
print(f"  Filters:")
print(f"    HoldFilter:       min hold N bars")
print(f"    CooldownFilter:   cooldown N bars after close")
print(f"    StatefulSignal:   pulse -> persistent state")
print(f"  Strategies:")
print(f"    FactorStrategy:   Factor -> Signal -> Target")
print(f"    MultiFactorStrategy: multi-factor cross-sectional rank")
print(f"  Backtest Results:")
print(f"    RSI Threshold:    equity={result.final_equity:.0f}, return={result.total_return:.2%}")
print(f"    MA Crossover:     equity={result2.final_equity:.0f}, return={result2.total_return:.2%}")
print(f"    MultiFactor:      equity={result3.final_equity:.0f}, return={result3.total_return:.2%}")
print(f"    Old MACross:      equity={result4.final_equity:.0f}, return={result4.total_return:.2%}")
print(f"\n  Full Pipeline: Factor -> Signal -> Filter -> Strategy -> Execution")
print(f"\n  V4.6 Signal + Strategy demo complete!")

"""
V4.6 Factor Platform Demo

演示三级模型：Factor -> Signal -> Strategy

1) Factor: 注册 + 计算（单 symbol / 多 symbol / 批量）
2) Operators: 横截面 rank/zscore + 时序算子
3) Signal: 阈值信号 + 交叉信号
4) Factor -> Signal -> Strategy 全链路
5) 与旧 factors/ 兼容
6) 与 Research IDE 集成
"""

import os
import sys
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
print("  V4.6 Factor Platform Demo")
print("=" * 60)


# ══════════════════════════════════════════════════════════════
# 1) Factor: 注册 + 计算
# ══════════════════════════════════════════════════════════════
print("\n1) Factor Registry + Compute")

from quantlab.factor import (
    FactorRegistry, FactorEngine,
    MAFactor, RSIFactor, MomentumFactor, ATRFactor,
    BOLLUpperFactor, BOLLLowerFactor, VOLFactor,
)

registry = FactorRegistry()

# 注册因子
registry.register(lambda: MAFactor(5))
registry.register(lambda: MAFactor(20))
registry.register(lambda: RSIFactor(14))
registry.register(lambda: MomentumFactor(20))
registry.register(lambda: ATRFactor(14))
registry.register(lambda: BOLLUpperFactor(20))
registry.register(lambda: BOLLLowerFactor(20))

print(f"   registered: {registry.list()}")
print(f"   categories: {registry.categories()}")
print(f"   stats: {registry.stats()}")

# 单 symbol 计算
engine = FactorEngine(registry)
rsi_aapl = engine.compute("RSI14", data["AAPL"])
print(f"\n   RSI14(AAPL): min={rsi_aapl.min():.1f}, max={rsi_aapl.max():.1f}, "
      f"last={rsi_aapl.iloc[-1]:.1f}")

mom_aapl = engine.compute("MOM20", data["AAPL"])
print(f"   MOM20(AAPL): min={mom_aapl.min():.4f}, max={mom_aapl.max():.4f}, "
      f"last={mom_aapl.iloc[-1]:.4f}")

# 多 symbol 计算
rsi_all = engine.compute_all("RSI14", data)
print(f"\n   RSI14(all): shape={rsi_all.shape}")
print(f"   last values: {rsi_all.iloc[-1].to_dict()}")

# 批量计算
batch = engine.compute_batch(["MA5", "MA20", "RSI14", "MOM20"], data["AAPL"])
print(f"\n   batch(AAPL): {list(batch.keys())}")
for name, series in batch.items():
    print(f"     {name}: last={series.iloc[-1]:.4f}" if not pd.isna(series.iloc[-1])
          else f"     {name}: last=NaN")

# 多 symbol 批量
batch_all = engine.compute_all_batch(["MA5", "MA20", "RSI14"], data)
print(f"\n   batch_all: {list(batch_all.keys())}")
for name, df in batch_all.items():
    print(f"     {name}: shape={df.shape}")


# ══════════════════════════════════════════════════════════════
# 2) Operators: 横截面 + 时序
# ══════════════════════════════════════════════════════════════
print("\n2) Operators")

from quantlab.factor.operators import rank, zscore, quantile, ts_delta, ts_zscore

# 横截面 rank
rsi_ranked = rank(rsi_all)
print(f"   rank(RSI14): last={rsi_ranked.iloc[-1].to_dict()}")

# 横截面 zscore
rsi_zscored = zscore(rsi_all)
print(f"   zscore(RSI14): last={rsi_zscored.iloc[-1].to_dict()}")

# 横截面分位数
rsi_q = quantile(rsi_all, q=5)
print(f"   quantile(RSI14, q=5): last={rsi_q.iloc[-1].to_dict()}")

# 时序算子
mom_delta = ts_delta(mom_aapl, 5)
print(f"   ts_delta(MOM20, 5): last={mom_delta.iloc[-1]:.4f}")

mom_zs = ts_zscore(mom_aapl, 20)
print(f"   ts_zscore(MOM20, 20): last={mom_zs.iloc[-1]:.4f}")


# ══════════════════════════════════════════════════════════════
# 3) Signal: 阈值 + 交叉
# ══════════════════════════════════════════════════════════════
print("\n3) Signal")

from quantlab.signal import (
    SignalEngine, ThresholdSignal, CrossoverSignal, ZeroCrossoverSignal,
)

sig_engine = SignalEngine()

# 阈值信号: RSI < 30 -> 1, RSI > 70 -> -1
sig_engine.register(ThresholdSignal("RSI14", 30, 70))

# 交叉信号: MA5 上穿 MA20 -> 1, 下穿 -> -1
sig_engine.register(CrossoverSignal("MA5", "MA20"))

# 零轴交叉: MOM20 上穿 0 -> 1, 下穿 -> -1
sig_engine.register(ZeroCrossoverSignal("MOM20"))

print(f"   registered signals: {sig_engine.list()}")

# 单 symbol 信号转换
factor_values_aapl = batch  # 从之前的 batch 计算
rsi_signal = sig_engine.transform_single(factor_values_aapl, "THRESH_RSI14_30_70")
print(f"\n   RSI threshold signal (AAPL): "
      f"1={int((rsi_signal == 1).sum())}, "
      f"-1={int((rsi_signal == -1).sum())}, "
      f"0={int((rsi_signal == 0).sum())}")

cross_signal = sig_engine.transform_single(factor_values_aapl, "CROSS_MA5_MA20")
print(f"   MA crossover signal (AAPL): "
      f"1={int((cross_signal == 1).sum())}, "
      f"-1={int((cross_signal == -1).sum())}, "
      f"0={int((cross_signal == 0).sum())}")

zero_signal = sig_engine.transform_single(factor_values_aapl, "ZERO_CROSS_MOM20")
print(f"   MOM zero cross signal (AAPL): "
      f"1={int((zero_signal == 1).sum())}, "
      f"-1={int((zero_signal == -1).sum())}, "
      f"0={int((zero_signal == 0).sum())}")

# 多 symbol 信号
factor_values_by_sym = {}
for sym, df in data.items():
    factor_values_by_sym[sym] = engine.compute_batch(
        ["MA5", "MA20", "RSI14", "MOM20"], df
    )

rsi_signal_all = sig_engine.transform_all(factor_values_by_sym, "THRESH_RSI14_30_70")
print(f"\n   RSI signal (all symbols): shape={rsi_signal_all.shape}")
for sym in rsi_signal_all.columns:
    s = rsi_signal_all[sym]
    print(f"     {sym}: 1={int((s == 1).sum())}, -1={int((s == -1).sum())}")


# ══════════════════════════════════════════════════════════════
# 4) Factor -> Signal -> Strategy 全链路
# ══════════════════════════════════════════════════════════════
print("\n4) Factor -> Signal -> Strategy Full Pipeline")

# Step 1: 计算因子
all_factors = engine.compute_all_batch(["MA5", "MA20", "RSI14", "MOM20", "ATR14"], data)
print(f"   Step1 factors: {list(all_factors.keys())}")

# Step 2: 横截面 rank（在 Strategy 层做，不在 Factor 层）
from quantlab.factor.operators import rank as cs_rank
ranked_rsi = cs_rank(all_factors["RSI14"])
ranked_mom = cs_rank(all_factors["MOM20"])
print(f"   Step2 cross-sectional rank: RSI shape={ranked_rsi.shape}, MOM shape={ranked_mom.shape}")

# Step 3: 生成信号（用 rank 后的因子）
# 简单多因子: rank_rsi + rank_mom 的加权组合
alpha = ranked_rsi * 0.5 + ranked_mom * 0.5
# 信号: alpha > 中位数 -> 1, alpha < 中位数 -> -1
median = alpha.median(axis=1)
signal_df = pd.DataFrame(0, index=alpha.index, columns=alpha.columns)
for col in alpha.columns:
    signal_df.loc[alpha[col] > median, col] = 1
    signal_df.loc[alpha[col] < median, col] = -1

print(f"   Step3 signal: shape={signal_df.shape}")
for sym in signal_df.columns:
    s = signal_df[sym]
    print(f"     {sym}: 1={int((s == 1).sum())}, -1={int((s == -1).sum())}, 0={int((s == 0).sum())}")

# Step 4: 用信号跑回测（接入旧引擎）
from quantlab.signals import MACrossStrategy
from quantlab.engine import BarEngine
from quantlab.portfolio_construction import EqualWeight
from quantlab.execution import TargetWeightExecution, PercentageCommission, PercentageSlippage

strategy = MACrossStrategy(fast=5, slow=20)
eng = BarEngine(
    strategy=strategy,
    portfolio_constructor=EqualWeight(),
    execution_model=TargetWeightExecution(),
    commission_model=PercentageCommission(),
    slippage_model=PercentageSlippage(),
)
result = eng.run(strategy=strategy, data=data)
print(f"\n   Step4 backtest: equity={result.final_equity:.0f}, "
      f"return={result.total_return:.2%}, "
      f"trades={result.trade_count}")


# ══════════════════════════════════════════════════════════════
# 5) 与旧 factors/ 兼容
# ══════════════════════════════════════════════════════════════
print("\n5) Backward Compatibility (old factors/)")

# 旧方式: fn(ctx, symbol, **params)
from quantlab.data import StrategyContext, factor_cache
factor_cache.clear()
ctx = StrategyContext(data, factor_cache)
from quantlab.factors.ma import ma
from quantlab.factors.rsi import rsi

ma5_old = ma(ctx, "AAPL", 5)
rsi14_old = rsi(ctx, "AAPL", 14)
print(f"   old ma(AAPL, 5): last={ma5_old.iloc[-1]:.2f}")
print(f"   old rsi(AAPL, 14): last={rsi14_old.iloc[-1]:.1f}")

# 新方式: Factor.compute(df)
ma5_new = engine.compute("MA5", data["AAPL"])
rsi14_new = engine.compute("RSI14", data["AAPL"])
print(f"   new MA5(AAPL): last={ma5_new.iloc[-1]:.2f}")
print(f"   new RSI14(AAPL): last={rsi14_new.iloc[-1]:.1f}")

# 验证一致性
ma_diff = (ma5_old - ma5_new).abs().max()
rsi_diff = (rsi14_old - rsi14_new).abs().max()
print(f"   consistency: MA diff={ma_diff:.6f}, RSI diff={rsi_diff:.6f}")


# ══════════════════════════════════════════════════════════════
# 6) 与 Research IDE 集成
# ══════════════════════════════════════════════════════════════
print("\n6) Research IDE Integration")

from quantlab.research import ResearchSession, FeatureStore

session = ResearchSession(name="factor_platform_demo")
session._data = data
session._current_dataset = "test_3sym"

# 用新 Factor Platform 计算并保存到 FeatureStore
rsi_all = engine.compute_all("RSI14", data)
session.save_feature("rsi14_platform", rsi_all, formula="RSIFactor(14)")

mom_all = engine.compute_all("MOM20", data)
session.save_feature("mom20_platform", mom_all, formula="MomentumFactor(20)")

# 横截面 rank 后保存
ranked = cs_rank(rsi_all)
session.save_feature("rsi14_cs_rank", ranked, formula="rank(RSI14)")

print(f"   features saved: {[f.name for f in session.feature_store.list_features()]}")
print(f"   session stats: {session.stats()}")


# ══════════════════════════════════════════════════════════════
# 总结
# ══════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("  V4.6 Factor Platform Summary")
print("=" * 60)
print(f"  Factor Registry:  {registry.stats()}")
print(f"  Signal Engine:    {len(sig_engine.list())} signals")
print(f"  Operators:        cross-sectional(rank/zscore/quantile/demean)")
print(f"                    time-series(delta/pct_change/mean/std/rank/zscore)")
print(f"                    arithmetic(add/sub/mul/div/abs/log/sign)")
print(f"  Compatibility:    old factors/ -> new factor/ (MA diff={ma_diff:.6f})")
print(f"  Integration:      Research IDE + FeatureStore OK")
print(f"\n  Three-Level Model:")
print(f"    Factor  -> per-symbol continuous values")
print(f"    Signal  -> discrete {-1, 0, 1} decisions")
print(f"    Strategy -> composes signals + execution")
print(f"\n  V4.6 Factor Platform demo complete!")

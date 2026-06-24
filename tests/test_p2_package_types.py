"""
P2 单元测试：Signal/Position/Risk/Execution/Observe Package 系统
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import numpy as np

from quantlab.asset_package.base import PackageType
from quantlab.asset_package.types import (
    # Signal
    ThresholdSignal, ProbabilitySignal, TrendSignal, RankingSignal,
    SignalSide, Signal,
    # Position
    FixedSizing, ConfidenceSizing, VolatilitySizing, KellySizing,
    # Risk
    MaxPositionRisk, StopLossRisk, TakeProfitRisk, MaxDrawdownRisk,
    # Execution
    PaperExecution, BinanceExecution, ReplayExecution, BacktestExecution,
    # Observe
    StandardObserve, HFObserveProfile,
)
from quantlab.asset_package.storage import PackageStorage
from quantlab.asset_package.registry import PackageRegistry, register_package_class


def test_threshold_signal():
    """测试 ThresholdSignal 生成 + 序列化"""
    print("\n=== Test: ThresholdSignal ===")
    sig = ThresholdSignal(name="ThresholdSignal", version="1.0", long_threshold=0.02)

    preds = pd.Series({"BTC": 0.05, "ETH": 0.0, "SOL": -0.05})
    signals = sig.generate(preds, metadata={"timestamp": "2026-06-24"})

    assert len(signals) == 3
    btc = next(s for s in signals if s.symbol == "BTC")
    eth = next(s for s in signals if s.symbol == "ETH")
    sol = next(s for s in signals if s.symbol == "SOL")
    assert btc.side == SignalSide.BUY
    assert eth.side == SignalSide.HOLD
    assert sol.side == SignalSide.SELL
    print(f"  ✓ generate(): BTC={btc.side.value}, ETH={eth.side.value}, SOL={sol.side.value}")

    # 序列化
    m = sig.to_manifest()
    assert m["config"]["long_threshold"] == 0.02
    sig2 = ThresholdSignal.from_manifest(m)
    assert sig2.long_threshold == 0.02
    print(f"  ✓ serialize/deserialize: long_threshold={sig2.long_threshold}")
    print("  PASSED")


def test_probability_signal():
    """测试 ProbabilitySignal"""
    print("\n=== Test: ProbabilitySignal ===")
    sig = ProbabilitySignal(name="ProbSignal", version="1.0", buy_threshold=0.72)

    preds = pd.Series({"BTC": 0.85, "ETH": 0.5, "SOL": 0.2})
    signals = sig.generate(preds)

    btc = next(s for s in signals if s.symbol == "BTC")
    eth = next(s for s in signals if s.symbol == "ETH")
    sol = next(s for s in signals if s.symbol == "SOL")
    assert btc.side == SignalSide.BUY
    assert eth.side == SignalSide.HOLD
    assert sol.side == SignalSide.SELL
    print(f"  ✓ generate(): BTC={btc.side.value}(prob={btc.prediction}), SOL={sol.side.value}")
    print("  PASSED")


def test_ranking_signal():
    """测试 RankingSignal"""
    print("\n=== Test: RankingSignal ===")
    sig = RankingSignal(name="RankSignal", version="1.0", top_pct=0.3, bottom_pct=0.3)

    preds = pd.Series({"A": 0.1, "B": 0.05, "C": 0.0, "D": -0.05, "E": -0.1})
    signals = sig.generate(preds)

    buy_symbols = [s.symbol for s in signals if s.side == SignalSide.BUY]
    sell_symbols = [s.symbol for s in signals if s.side == SignalSide.SELL]
    assert "A" in buy_symbols
    assert "E" in sell_symbols
    print(f"  ✓ generate(): BUY={buy_symbols}, SELL={sell_symbols}")
    print("  PASSED")


def test_fixed_sizing():
    """测试 FixedSizing"""
    print("\n=== Test: FixedSizing ===")
    sizer = FixedSizing(name="FixedSizing", version="1.0", base_size=0.2)

    signals = [
        Signal(symbol="BTC", side=SignalSide.BUY, score=0.5),
        Signal(symbol="ETH", side=SignalSide.SELL, score=0.5),
        Signal(symbol="SOL", side=SignalSide.HOLD, score=0.0),
    ]
    positions = sizer.size(signals, capital=100000)

    assert positions["BTC"] == 0.2
    assert positions["ETH"] == -0.2
    assert positions["SOL"] == 0.0
    print(f"  ✓ size(): BTC={positions['BTC']}, ETH={positions['ETH']}, SOL={positions['SOL']}")
    print("  PASSED")


def test_confidence_sizing():
    """测试 ConfidenceSizing"""
    print("\n=== Test: ConfidenceSizing ===")
    sizer = ConfidenceSizing(name="ConfSizing", version="1.0", confidence_scale=1.0, max_size=0.5)

    signals = [
        Signal(symbol="BTC", side=SignalSide.BUY, score=0.8),
        Signal(symbol="ETH", side=SignalSide.BUY, score=0.3),
    ]
    positions = sizer.size(signals, capital=100000)

    assert positions["BTC"] == 0.5  # capped at max_size
    assert positions["ETH"] == 0.3
    print(f"  ✓ size(): BTC={positions['BTC']} (capped), ETH={positions['ETH']}")
    print("  PASSED")


def test_volatility_sizing():
    """测试 VolatilitySizing"""
    print("\n=== Test: VolatilitySizing ===")
    sizer = VolatilitySizing(name="VolSizing", version="1.0", target_volatility=0.15)

    signals = [Signal(symbol="BTC", side=SignalSide.BUY, score=0.5)]
    # 构造 30 天价格数据
    np.random.seed(42)
    prices = pd.DataFrame({"BTC": 100 * np.exp(np.cumsum(np.random.randn(30) * 0.02))})
    positions = sizer.size(signals, capital=100000, market_data=prices)

    assert positions["BTC"] > 0
    assert positions["BTC"] <= 1.0
    print(f"  ✓ size(): BTC={positions['BTC']:.4f}")
    print("  PASSED")


def test_kelly_sizing():
    """测试 KellySizing"""
    print("\n=== Test: KellySizing ===")
    sizer = KellySizing(name="KellySizing", version="1.0", win_rate=0.6, win_loss_ratio=2.0)

    signals = [Signal(symbol="BTC", side=SignalSide.BUY, score=0.5)]
    positions = sizer.size(signals, capital=100000)

    # Kelly = (0.6*2 - 0.4) / 2 = 0.4, half = 0.2
    assert abs(positions["BTC"] - 0.2) < 0.01
    print(f"  ✓ size(): BTC={positions['BTC']:.4f} (expected ~0.2)")
    print("  PASSED")


def test_max_position_risk():
    """测试 MaxPositionRisk"""
    print("\n=== Test: MaxPositionRisk ===")
    risk = MaxPositionRisk(name="MaxPosRisk", version="1.0", max_position=0.3, max_portfolio=0.5)

    positions = {"BTC": 0.5, "ETH": 0.5, "SOL": 0.5}  # 总 1.5 > 0.5
    adjusted = risk.apply(positions)

    # 单品种应被限制到 0.3
    assert all(abs(v) <= 0.3 + 1e-9 for v in adjusted.values())
    # 总仓位应被缩放到 0.5
    gross = sum(abs(v) for v in adjusted.values())
    assert abs(gross - 0.5) < 0.01
    print(f"  ✓ apply(): gross={gross:.4f} (capped at 0.5)")
    print("  PASSED")


def test_stop_loss_risk():
    """测试 StopLossRisk"""
    print("\n=== Test: StopLossRisk ===")
    risk = StopLossRisk(name="StopLoss", version="1.0", stop_loss_pct=0.08)

    positions = {"BTC": 0.2, "ETH": 0.2}
    state = {"unrealized_pnl": {"BTC": -0.10, "ETH": 0.05}}  # BTC 亏 10%
    adjusted = risk.apply(positions, state)

    assert adjusted["BTC"] == 0.0
    assert adjusted["ETH"] == 0.2
    print(f"  ✓ apply(): BTC={adjusted['BTC']} (stopped), ETH={adjusted['ETH']}")
    print("  PASSED")


def test_max_drawdown_risk():
    """测试 MaxDrawdownRisk"""
    print("\n=== Test: MaxDrawdownRisk ===")
    risk = MaxDrawdownRisk(name="MaxDD", version="1.0", max_drawdown=0.20, drawdown_cutoff=0.5)

    positions = {"BTC": 0.2, "ETH": 0.2}
    state = {"current_drawdown": 0.25}  # 回撤 25%
    adjusted = risk.apply(positions, state)

    assert adjusted["BTC"] == 0.1  # 0.2 * 0.5
    assert adjusted["ETH"] == 0.1
    print(f"  ✓ apply(): BTC={adjusted['BTC']} (scaled by cutoff)")
    print("  PASSED")


def test_execution_profiles():
    """测试 ExecutionProfile 序列化"""
    print("\n=== Test: ExecutionProfiles ===")
    for cls, name, expected_broker in [
        (PaperExecution, "PaperExec", "paper"),
        (BinanceExecution, "BinanceExec", "binance"),
        (ReplayExecution, "ReplayExec", "replay"),
        (BacktestExecution, "BacktestExec", "backtest"),
    ]:
        exec_profile = cls(name=name, version="1.0")
        assert exec_profile.get_broker_type() == expected_broker
        m = exec_profile.to_manifest()
        assert m["type"] == "EXECUTION"
        # 反序列化
        exec2 = cls.from_manifest(m)
        assert exec2.get_broker_type() == expected_broker
        print(f"  ✓ {cls.__name__}: broker={expected_broker}")
    print("  PASSED")


def test_observe_profiles():
    """测试 ObserveProfile"""
    print("\n=== Test: ObserveProfiles ===")
    std = StandardObserve(name="StandardObserve", version="1.0")
    hf = HFObserveProfile(name="HFObserve", version="1.0")

    std_metrics = std.get_metrics()
    hf_metrics = hf.get_metrics()
    assert "daily_return" in std_metrics
    assert "latency" in hf_metrics
    print(f"  ✓ StandardObserve metrics: {std_metrics[:3]}...")
    print(f"  ✓ HFObserveProfile metrics: {hf_metrics[:3]}...")
    print("  PASSED")


def test_package_registry_integration():
    """测试 PackageRegistry 集成"""
    print("\n=== Test: PackageRegistry 集成 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlpkg_p2_")
    try:
        store = PackageStorage(root=tmpdir)
        registry = PackageRegistry(storage=store)

        # 注册所有类型
        register_package_class(PackageType.SIGNAL, ThresholdSignal)
        register_package_class(PackageType.POSITION, FixedSizing)
        register_package_class(PackageType.RISK, MaxPositionRisk)
        register_package_class(PackageType.EXECUTION, PaperExecution)
        register_package_class(PackageType.OBSERVE, StandardObserve)

        # 创建并注册
        sig = ThresholdSignal(name="ThresholdSignal", version="1.0", long_threshold=0.03)
        pos = FixedSizing(name="FixedSizing", version="1.0", base_size=0.15)
        risk = MaxPositionRisk(name="MaxPosRisk", version="1.0", max_position=0.25)
        exe = PaperExecution(name="PaperExec", version="1.0")
        obs = StandardObserve(name="StdObserve", version="1.0")

        for pkg in [sig, pos, risk, exe, obs]:
            registry.register(pkg)

        # 查询
        sigs = registry.list(PackageType.SIGNAL)
        poses = registry.list(PackageType.POSITION)
        risks = registry.list(PackageType.RISK)
        exes = registry.list(PackageType.EXECUTION)
        obss = registry.list(PackageType.OBSERVE)

        assert len(sigs) == 1
        assert len(poses) == 1
        assert len(risks) == 1
        assert len(exes) == 1
        assert len(obss) == 1
        print(f"  ✓ 注册并查询: S={len(sigs)} P={len(poses)} R={len(risks)} E={len(exes)} O={len(obss)}")

        # ref 查询
        loaded = registry.get_by_ref(PackageType.SIGNAL, "ref://ThresholdSignal@1.0")
        assert loaded is not None
        assert loaded.long_threshold == 0.03
        print(f"  ✓ get_by_ref: long_threshold={loaded.long_threshold}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    print("=" * 60)
    print("P2 单元测试：Signal/Position/Risk/Execution/Observe Package")
    print("=" * 60)

    test_threshold_signal()
    test_probability_signal()
    test_ranking_signal()
    test_fixed_sizing()
    test_confidence_sizing()
    test_volatility_sizing()
    test_kelly_sizing()
    test_max_position_risk()
    test_stop_loss_risk()
    test_max_drawdown_risk()
    test_execution_profiles()
    test_observe_profiles()
    test_package_registry_integration()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
P6 单元测试：Strategy Runtime 解释器
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantlab.asset_package.base import PackageType
from quantlab.asset_package.types import (
    ThresholdSignal, FixedSizing, MaxPositionRisk,
    PaperExecution, StandardObserve, StrategyPackage,
)
from quantlab.asset_package.storage import PackageStorage
from quantlab.asset_package.registry import PackageRegistry, register_package_class
from quantlab.strategy_studio.composer import StrategyComposer, ComposeRequest
from quantlab.strategy_studio.runtime import StrategyRuntime, Bar, RunResult


def setup_test_registry(tmpdir: str) -> PackageRegistry:
    """创建测试用 Registry"""
    store = PackageStorage(root=tmpdir)
    registry = PackageRegistry(storage=store)

    register_package_class(PackageType.SIGNAL, ThresholdSignal)
    register_package_class(PackageType.POSITION, FixedSizing)
    register_package_class(PackageType.RISK, MaxPositionRisk)
    register_package_class(PackageType.EXECUTION, PaperExecution)
    register_package_class(PackageType.OBSERVE, StandardObserve)
    register_package_class(PackageType.STRATEGY, StrategyPackage)

    registry.register(ThresholdSignal(name="ThresholdSignal", version="1.0", long_threshold=0.02))
    registry.register(FixedSizing(name="FixedSizing", version="1.0", base_size=0.2))
    registry.register(MaxPositionRisk(name="MaxPosRisk", version="1.0", max_position=0.3))
    registry.register(PaperExecution(name="PaperExec", version="1.0"))
    registry.register(StandardObserve(name="StdObserve", version="1.0"))

    # Model 占位
    import yaml
    model_manifest = {
        "id": "Momentum_LGBM@1.2.0",
        "name": "Momentum_LGBM",
        "version": "1.2.0",
        "type": "MODEL",
        "description": "Test model placeholder",
        "status": "ACTIVE",
        "created_at": "2026-06-24T00:00:00",
        "created_by": "system",
        "tags": [],
        "hash": "placeholder",
        "config": {},
    }
    model_dir = os.path.join(tmpdir, "model", "Momentum_LGBM@1.2.0")
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(os.path.join(model_dir, "artifacts"), exist_ok=True)
    with open(os.path.join(model_dir, "manifest.yaml"), "w") as f:
        yaml.safe_dump(model_manifest, f)

    return registry


def make_test_bars(n: int = 10) -> list:
    """生成测试 K 线数据"""
    bars = []
    base_price = 100.0
    for i in range(n):
        # 简单的随机走势
        change = (i % 3 - 1) * 0.5
        close = base_price + i * 0.1 + change
        bars.append(Bar(
            timestamp=f"2026-01-{i+1:02d}",
            open=close - 0.2,
            high=close + 0.3,
            low=close - 0.3,
            close=close,
            volume=1000.0 + i * 10,
            symbol="BTC",
        ))
    return bars


def test_runtime_basic():
    """测试 Runtime 基本运行"""
    print("\n=== Test: Runtime 基本运行 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlruntime_")
    try:
        registry = setup_test_registry(tmpdir)

        # 装配策略
        composer = StrategyComposer(registry=registry)
        result = composer.compose(ComposeRequest(
            name="TestStrategy",
            version="1.0",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
            auto_validate=False,
        ))
        assert result.success

        # 运行
        strategy = registry.get(PackageType.STRATEGY, "TestStrategy", "1.0")
        runtime = StrategyRuntime(strategy, registry=registry)
        bars = make_test_bars(10)

        run_result = runtime.run(bars, initial_capital=100000)

        assert run_result.bars_processed == 10
        assert run_result.errors == []
        assert len(run_result.bar_results) == 10
        print(f"  ✓ run() 处理 {run_result.bars_processed} bars")
        print(f"  ✓ final_portfolio_value={run_result.final_portfolio_value:.2f}")
        print(f"  ✓ total_return={run_result.total_return:.4f}")
        print(f"  ✓ metrics: {run_result.metrics}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_runtime_missing_dependency():
    """测试缺失依赖时 Runtime 报错"""
    print("\n=== Test: Runtime 缺失依赖 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlruntime_")
    try:
        registry = setup_test_registry(tmpdir)

        # 创建一个引用不存在组件的策略
        strategy = StrategyPackage(
            name="BadStrategy",
            version="1.0",
            model_ref="ref://NonExistent@1.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
        )

        runtime = StrategyRuntime(strategy, registry=registry)
        bars = make_test_bars(5)

        run_result = runtime.run(bars)

        assert not run_result.errors == []
        assert any("NonExistent" in e for e in run_result.errors)
        print(f"  ✓ run() 正确报错: {run_result.errors}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_runtime_bar_result():
    """测试单 bar 结果结构"""
    print("\n=== Test: BarResult 结构 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlruntime_")
    try:
        registry = setup_test_registry(tmpdir)

        composer = StrategyComposer(registry=registry)
        result = composer.compose(ComposeRequest(
            name="TestStrategy",
            version="1.0",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
            auto_validate=False,
        ))
        assert result.success

        strategy = registry.get(PackageType.STRATEGY, "TestStrategy", "1.0")
        runtime = StrategyRuntime(strategy, registry=registry)
        bars = make_test_bars(3)

        run_result = runtime.run(bars, initial_capital=100000)

        # 检查第一个 bar 的结果
        first_bar = run_result.bar_results[0]
        assert first_bar.timestamp == "2026-01-01"
        assert "BTC" in first_bar.predictions
        assert len(first_bar.signals) > 0
        print(f"  ✓ BarResult timestamp={first_bar.timestamp}")
        print(f"  ✓ predictions={first_bar.predictions}")
        print(f"  ✓ signals count={len(first_bar.signals)}")
        print(f"  ✓ target_positions={first_bar.target_positions}")
        print(f"  ✓ orders count={len(first_bar.orders)}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_runtime_metrics():
    """测试策略指标计算"""
    print("\n=== Test: 指标计算 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlruntime_")
    try:
        registry = setup_test_registry(tmpdir)

        composer = StrategyComposer(registry=registry)
        result = composer.compose(ComposeRequest(
            name="TestStrategy",
            version="1.0",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
            auto_validate=False,
        ))
        assert result.success

        strategy = registry.get(PackageType.STRATEGY, "TestStrategy", "1.0")
        runtime = StrategyRuntime(strategy, registry=registry)
        bars = make_test_bars(20)

        run_result = runtime.run(bars, initial_capital=100000)

        metrics = run_result.metrics
        assert "final_value" in metrics
        assert "total_return" in metrics
        assert "max_drawdown" in metrics
        assert "total_orders" in metrics
        assert "bars" in metrics
        print(f"  ✓ metrics keys: {list(metrics.keys())}")
        print(f"  ✓ final_value={metrics['final_value']:.2f}")
        print(f"  ✓ total_return={metrics['total_return']:.4f}")
        print(f"  ✓ max_drawdown={metrics['max_drawdown']:.4f}")
        print(f"  ✓ total_orders={metrics['total_orders']}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    print("=" * 60)
    print("P6 单元测试：Strategy Runtime 解释器")
    print("=" * 60)

    test_runtime_basic()
    test_runtime_missing_dependency()
    test_runtime_bar_result()
    test_runtime_metrics()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

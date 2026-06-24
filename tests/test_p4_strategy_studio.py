"""
P4 单元测试：Strategy Studio 后端
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
from quantlab.strategy_studio.resolver import DependencyResolver
from quantlab.strategy_studio.validator import StrategyValidator


def setup_test_registry(tmpdir: str) -> PackageRegistry:
    """创建测试用 Registry，预注册所有 Package 类型"""
    store = PackageStorage(root=tmpdir)
    registry = PackageRegistry(storage=store)

    # 注册类型
    register_package_class(PackageType.SIGNAL, ThresholdSignal)
    register_package_class(PackageType.POSITION, FixedSizing)
    register_package_class(PackageType.RISK, MaxPositionRisk)
    register_package_class(PackageType.EXECUTION, PaperExecution)
    register_package_class(PackageType.OBSERVE, StandardObserve)
    register_package_class(PackageType.STRATEGY, StrategyPackage)

    # 预注册组件 Package
    signal = ThresholdSignal(name="ThresholdSignal", version="1.0", long_threshold=0.02)
    position = FixedSizing(name="FixedSizing", version="1.0", base_size=0.2)
    risk = MaxPositionRisk(name="MaxPosRisk", version="1.0", max_position=0.3)
    execution = PaperExecution(name="PaperExec", version="1.0")
    observe = StandardObserve(name="StdObserve", version="1.0")

    # Model 用占位：直接用 storage 创建一个 MODEL 类型的 manifest
    # （P4 不实际加载 Model，只验证 ref 存在）
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

    registry.register(signal)
    registry.register(position)
    registry.register(risk)
    registry.register(execution)
    registry.register(observe)

    return registry


def test_compose_success():
    """测试成功装配策略"""
    print("\n=== Test: 成功装配策略 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlstudio_")
    try:
        registry = setup_test_registry(tmpdir)
        composer = StrategyComposer(registry=registry)

        request = ComposeRequest(
            name="Momentum_LGBM_v2",
            family="Momentum",
            version="2.0",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
        )

        result = composer.compose(request)
        assert result.success, f"Compose failed: {result.errors}"
        assert result.strategy_id == "Momentum_LGBM_v2@2.0"
        assert result.validation.passed
        print(f"  ✓ compose() success, strategy_id={result.strategy_id}")
        print(f"  ✓ 依赖验证通过: {result.validation.passed}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_compose_missing_dependency():
    """测试缺失依赖时装配失败"""
    print("\n=== Test: 缺失依赖 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlstudio_")
    try:
        registry = setup_test_registry(tmpdir)
        composer = StrategyComposer(registry=registry)

        request = ComposeRequest(
            name="BadStrategy",
            version="1.0",
            model_ref="ref://NonExistent@1.0",  # 不存在
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
        )

        result = composer.compose(request)
        assert not result.success
        assert any("NonExistent" in e for e in result.errors)
        print(f"  ✓ compose() 正确拒绝缺失依赖: {result.errors}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_compose_missing_field():
    """测试缺失必填字段"""
    print("\n=== Test: 缺失必填字段 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlstudio_")
    try:
        registry = setup_test_registry(tmpdir)
        composer = StrategyComposer(registry=registry)

        request = ComposeRequest(
            name="",  # 缺 name
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
        )

        result = composer.compose(request)
        assert not result.success
        assert any("name" in e.lower() for e in result.errors)
        print(f"  ✓ compose() 正确拒绝缺失字段: {result.errors}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_dependency_resolver():
    """测试依赖解析器"""
    print("\n=== Test: DependencyResolver ===")
    tmpdir = tempfile.mkdtemp(prefix="qlstudio_")
    try:
        registry = setup_test_registry(tmpdir)
        resolver = DependencyResolver(registry=registry)

        strategy = StrategyPackage(
            name="Test",
            version="1.0",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ThresholdSignal@1.0",
            position_ref="ref://FixedSizing@1.0",
            risk_ref="ref://MaxPosRisk@1.0",
            execution_ref="ref://PaperExec@1.0",
            observe_ref="ref://StdObserve@1.0",
        )

        graph = resolver.resolve(strategy)
        assert len(graph.all_nodes) == 6
        assert graph.is_complete
        assert len(graph.missing_refs) == 0
        print(f"  ✓ resolve() 返回 {len(graph.all_nodes)} 个节点")
        print(f"  ✓ is_complete={graph.is_complete}")

        # 验证
        result = resolver.validate(graph)
        assert result.passed
        print(f"  ✓ validate() passed={result.passed}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_validator_smoke_test():
    """测试策略验证器（smoke test）"""
    print("\n=== Test: StrategyValidator ===")
    tmpdir = tempfile.mkdtemp(prefix="qlstudio_")
    try:
        registry = setup_test_registry(tmpdir)

        # 先装配策略
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

        # 验证
        validator = StrategyValidator(registry=registry)
        strategy = registry.get(PackageType.STRATEGY, "TestStrategy", "1.0")
        report = validator.validate(strategy, smoke_test_bars=100)

        assert report.passed, f"Validation failed: {report.errors}"
        assert report.smoke_test is not None
        assert report.smoke_test["passed"]
        print(f"  ✓ validate() passed={report.passed}")
        print(f"  ✓ smoke_test checks: {len(report.smoke_test['checks'])}")
        for check in report.smoke_test["checks"]:
            print(f"    - {check['name']}: {'✓' if check['passed'] else '✗'} {check['detail']}")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    print("=" * 60)
    print("P4 单元测试：Strategy Studio 后端")
    print("=" * 60)

    test_compose_success()
    test_compose_missing_dependency()
    test_compose_missing_field()
    test_dependency_resolver()
    test_validator_smoke_test()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

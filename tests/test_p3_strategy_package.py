"""
P3 单元测试：.qlstrategy 包格式 + StrategyPackage
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantlab.asset_package.base import PackageType, Ref, parse_ref
from quantlab.asset_package.types import StrategyPackage, StrategyStatus, ValidationState
from quantlab.asset_package.storage import PackageStorage
from quantlab.asset_package.registry import PackageRegistry, register_package_class


def test_strategy_package_serialize():
    """测试 StrategyPackage 序列化"""
    print("\n=== Test: StrategyPackage 序列化 ===")
    strategy = StrategyPackage(
        name="Momentum_LGBM_v2",
        version="2.0",
        description="动量+LGBM策略v2",
        family="Momentum",
        model_ref="ref://Momentum_LGBM@1.2.0",
        signal_ref="ref://ProbabilitySignal@1.0",
        position_ref="ref://VolatilitySizing@2.0",
        risk_ref="ref://CryptoBasicRisk@1.1",
        execution_ref="ref://PaperExecution@1.0",
        observe_ref="ref://StandardObserve@1.0",
    )

    # 序列化
    manifest = strategy.to_manifest()
    assert manifest["id"] == "Momentum_LGBM_v2@2.0"
    assert manifest["type"] == "STRATEGY"
    assert manifest["config"]["family"] == "Momentum"
    assert manifest["config"]["model"] == "ref://Momentum_LGBM@1.2.0"
    assert manifest["config"]["signal"] == "ref://ProbabilitySignal@1.0"
    print(f"  ✓ to_manifest() id={manifest['id']}")
    print(f"  ✓ model_ref={manifest['config']['model']}")
    print(f"  ✓ signal_ref={manifest['config']['signal']}")

    # yaml
    yaml_str = strategy.to_manifest_yaml()
    assert "Momentum_LGBM@1.2.0" in yaml_str
    assert "ProbabilitySignal@1.0" in yaml_str
    print(f"  ✓ to_manifest_yaml() 包含所有 ref")

    # 反序列化
    strategy2 = StrategyPackage.from_manifest(manifest)
    assert strategy2.name == "Momentum_LGBM_v2"
    assert strategy2.family == "Momentum"
    assert strategy2.model_ref == "ref://Momentum_LGBM@1.2.0"
    assert strategy2.signal_ref == "ref://ProbabilitySignal@1.0"
    assert strategy2.strategy_status == StrategyStatus.CANDIDATE
    assert strategy2.validation == ValidationState.PENDING
    print(f"  ✓ from_manifest() 正确恢复所有 ref")
    print("  PASSED")


def test_strategy_ref_parsing():
    """测试 ref 解析"""
    print("\n=== Test: ref 解析 ===")
    strategy = StrategyPackage(
        name="Test",
        version="1.0",
        model_ref="ref://ModelA@1.0",
        signal_ref="ref://SignalB@2.0",
        position_ref="ref://PositionC@1.5",
        risk_ref="ref://RiskD@1.0",
        execution_ref="ref://PaperExecution@1.0",
        observe_ref="ref://StandardObserve@1.0",
    )

    refs = strategy.get_all_refs()
    assert len(refs) == 6
    assert refs["model"] == "ref://ModelA@1.0"

    ref_objs = strategy.get_ref_objects()
    assert ref_objs["model"].name == "ModelA"
    assert ref_objs["model"].version == "1.0"
    assert ref_objs["signal"].name == "SignalB"
    print(f"  ✓ get_all_refs() 返回 {len(refs)} 个 ref")
    print(f"  ✓ get_ref_objects() model={ref_objs['model'].id}")
    print("  PASSED")


def test_strategy_storage():
    """测试 StrategyPackage 存储"""
    print("\n=== Test: StrategyPackage 存储 ===")
    tmpdir = tempfile.mkdtemp(prefix="qlstrategy_")
    try:
        store = PackageStorage(root=tmpdir)
        registry = PackageRegistry(storage=store)
        register_package_class(PackageType.STRATEGY, StrategyPackage)

        strategy = StrategyPackage(
            name="Momentum_LGBM_v2",
            version="2.0",
            family="Momentum",
            model_ref="ref://Momentum_LGBM@1.2.0",
            signal_ref="ref://ProbabilitySignal@1.0",
            position_ref="ref://VolatilitySizing@2.0",
            risk_ref="ref://CryptoBasicRisk@1.1",
            execution_ref="ref://PaperExecution@1.0",
            observe_ref="ref://StandardObserve@1.0",
        )

        # 注册
        pkg_id = registry.register(strategy)
        assert pkg_id == "Momentum_LGBM_v2@2.0"
        print(f"  ✓ register() → {pkg_id}")

        # 查询
        loaded = registry.get(PackageType.STRATEGY, "Momentum_LGBM_v2", "2.0")
        assert loaded is not None
        assert loaded.family == "Momentum"
        assert loaded.model_ref == "ref://Momentum_LGBM@1.2.0"
        print(f"  ✓ get() family={loaded.family}, model_ref={loaded.model_ref}")

        # ref 查询
        loaded_ref = registry.get_by_ref(PackageType.STRATEGY, "ref://Momentum_LGBM_v2@2.0")
        assert loaded_ref is not None
        print(f"  ✓ get_by_ref() 正确")

        # 列表
        all_strategies = registry.list(PackageType.STRATEGY)
        assert len(all_strategies) == 1
        print(f"  ✓ list() 返回 {len(all_strategies)} 个策略")
        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_manifest_yaml_format():
    """测试 manifest.yaml 格式符合设计"""
    print("\n=== Test: manifest.yaml 格式 ===")
    strategy = StrategyPackage(
        name="Momentum_LGBM_v2",
        version="2.0",
        family="Momentum",
        model_ref="ref://Momentum_LGBM@1.2.0",
        signal_ref="ref://ProbabilitySignal@1.0",
        position_ref="ref://VolatilitySizing@2.0",
        risk_ref="ref://CryptoBasicRisk@1.1",
        execution_ref="ref://PaperExecution@1.0",
        observe_ref="ref://StandardObserve@1.0",
    )

    yaml_str = strategy.to_manifest_yaml()
    print(f"\n  --- manifest.yaml ---\n{yaml_str}  --- end ---")

    # 验证关键字段
    assert "id: Momentum_LGBM_v2@2.0" in yaml_str
    assert "type: STRATEGY" in yaml_str
    assert "family: Momentum" in yaml_str
    assert "ref://Momentum_LGBM@1.2.0" in yaml_str
    assert "ref://ProbabilitySignal@1.0" in yaml_str
    assert "ref://VolatilitySizing@2.0" in yaml_str
    assert "ref://PaperExecution@1.0" in yaml_str
    print(f"  ✓ manifest.yaml 包含所有必要字段")
    print("  PASSED")


def main():
    print("=" * 60)
    print("P3 单元测试：.qlstrategy 包格式 + StrategyPackage")
    print("=" * 60)

    test_strategy_package_serialize()
    test_strategy_ref_parsing()
    test_strategy_storage()
    test_manifest_yaml_format()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

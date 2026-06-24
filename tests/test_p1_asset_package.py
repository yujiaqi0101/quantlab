"""
P1 单元测试：Asset Package 标准化

测试内容：
  1. Ref 解析
  2. Package 基类序列化/反序列化
  3. PackageStorage 保存/加载/查询
  4. PackageRegistry 注册/获取
"""

import os
import sys
import tempfile
import shutil

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantlab.asset_package.base import (
    AssetPackage,
    PackageType,
    PackageStatus,
    Ref,
    parse_ref,
)
from quantlab.asset_package.storage import PackageStorage
from quantlab.asset_package.registry import PackageRegistry, register_package_class


# ==================================================================
# 测试用具体 Package 实现
# ==================================================================

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class TestSignalPackage(AssetPackage):
    """测试用的 SignalPackage"""
    package_type: PackageType = PackageType.SIGNAL
    long_threshold: float = 0.02
    short_threshold: float = -0.02
    use_short: bool = True

    def to_config(self) -> Dict[str, Any]:
        return {
            "long_threshold": self.long_threshold,
            "short_threshold": self.short_threshold,
            "use_short": self.use_short,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            **self.to_config(),
        })

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.long_threshold = config.get("long_threshold", 0.02)
        self.short_threshold = config.get("short_threshold", -0.02)
        self.use_short = config.get("use_short", True)


# ==================================================================
# 测试
# ==================================================================

def test_ref_parse():
    """测试 1：ref 解析"""
    print("\n=== Test 1: ref 解析 ===")

    # 标准格式
    ref = parse_ref("ref://Momentum_LGBM@1.2.0")
    assert ref.name == "Momentum_LGBM"
    assert ref.version == "1.2.0"
    assert str(ref) == "ref://Momentum_LGBM@1.2.0"
    assert ref.id == "Momentum_LGBM@1.2.0"
    print(f"  ✓ parse_ref('ref://Momentum_LGBM@1.2.0') = {ref}")

    # 无 ref:// 前缀
    ref2 = parse_ref("ThresholdSignal@1.0")
    assert ref2.name == "ThresholdSignal"
    assert ref2.version == "1.0"
    print(f"  ✓ parse_ref('ThresholdSignal@1.0') = {ref2}")

    # Ref.from_string
    ref3 = Ref.from_string("ref://X@2.0")
    assert ref3.name == "X"
    assert ref3.version == "2.0"
    print(f"  ✓ Ref.from_string('ref://X@2.0') = {ref3}")

    # 错误格式
    try:
        parse_ref("invalid_no_at")
        assert False, "Should have raised"
    except ValueError as e:
        print(f"  ✓ 正确拒绝无效格式: {e}")

    print("  PASSED")


def test_package_serialize():
    """测试 2：Package 序列化/反序列化"""
    print("\n=== Test 2: Package 序列化/反序列化 ===")

    pkg = TestSignalPackage(
        name="ThresholdSignal",
        version="1.0",
        description="阈值信号",
        long_threshold=0.03,
        short_threshold=-0.03,
        use_short=False,
    )

    # 序列化
    manifest = pkg.to_manifest()
    assert manifest["id"] == "ThresholdSignal@1.0"
    assert manifest["name"] == "ThresholdSignal"
    assert manifest["version"] == "1.0"
    assert manifest["type"] == "SIGNAL"
    assert manifest["config"]["long_threshold"] == 0.03
    assert manifest["config"]["use_short"] is False
    assert manifest["hash"] != ""
    print(f"  ✓ to_manifest() id={manifest['id']}, hash={manifest['hash'][:8]}...")

    # yaml 序列化
    yaml_str = pkg.to_manifest_yaml()
    assert "ThresholdSignal" in yaml_str
    assert "long_threshold: 0.03" in yaml_str
    print(f"  ✓ to_manifest_yaml() 包含正确字段")

    # 反序列化
    pkg2 = TestSignalPackage.from_manifest(manifest)
    assert pkg2.name == "ThresholdSignal"
    assert pkg2.version == "1.0"
    assert pkg2.long_threshold == 0.03
    assert pkg2.use_short is False
    assert pkg2.hash == pkg.hash
    print(f"  ✓ from_manifest() 正确恢复 long_threshold={pkg2.long_threshold}")

    print("  PASSED")


def test_storage():
    """测试 3：PackageStorage 保存/加载/查询"""
    print("\n=== Test 3: PackageStorage ===")

    tmpdir = tempfile.mkdtemp(prefix="qlpkg_test_")
    try:
        store = PackageStorage(root=tmpdir)

        pkg = TestSignalPackage(
            name="ThresholdSignal",
            version="1.0",
            description="阈值信号",
            long_threshold=0.02,
        )

        # 保存
        path = store.save(pkg)
        assert os.path.exists(path)
        assert "manifest.yaml" in path
        print(f"  ✓ save() → {path}")

        # exists
        assert store.exists(PackageType.SIGNAL, "ThresholdSignal", "1.0")
        assert not store.exists(PackageType.SIGNAL, "ThresholdSignal", "2.0")
        print(f"  ✓ exists() 正确")

        # load
        manifest = store.load(PackageType.SIGNAL, "ThresholdSignal", "1.0")
        assert manifest["name"] == "ThresholdSignal"
        assert manifest["config"]["long_threshold"] == 0.02
        print(f"  ✓ load() 正确")

        # save_artifact / load_artifact
        store.save_artifact(PackageType.SIGNAL, "ThresholdSignal", "1.0",
                            "test.json", b'{"key": "value"}')
        data = store.load_artifact(PackageType.SIGNAL, "ThresholdSignal", "1.0", "test.json")
        assert data == b'{"key": "value"}'
        print(f"  ✓ save/load_artifact() 正确")

        # list
        pkg2 = TestSignalPackage(name="ThresholdSignal", version="2.0", description="v2")
        store.save(pkg2)
        all_pkgs = store.list(PackageType.SIGNAL)
        assert len(all_pkgs) == 2
        print(f"  ✓ list() 返回 {len(all_pkgs)} 个 package")

        # list_versions
        versions = store.list_versions(PackageType.SIGNAL, "ThresholdSignal")
        assert "1.0" in versions
        assert "2.0" in versions
        print(f"  ✓ list_versions() = {versions}")

        # load_by_ref
        manifest_ref = store.load_by_ref(PackageType.SIGNAL, "ref://ThresholdSignal@1.0")
        assert manifest_ref["name"] == "ThresholdSignal"
        print(f"  ✓ load_by_ref('ref://ThresholdSignal@1.0') 正确")

        # delete
        assert store.delete(PackageType.SIGNAL, "ThresholdSignal", "2.0")
        assert not store.exists(PackageType.SIGNAL, "ThresholdSignal", "2.0")
        print(f"  ✓ delete() 正确")

        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_registry():
    """测试 4：PackageRegistry 注册/获取"""
    print("\n=== Test 4: PackageRegistry ===")

    tmpdir = tempfile.mkdtemp(prefix="qlpkg_reg_")
    try:
        store = PackageStorage(root=tmpdir)
        registry = PackageRegistry(storage=store)

        # 注册类型
        register_package_class(PackageType.SIGNAL, TestSignalPackage)

        pkg = TestSignalPackage(
            name="ThresholdSignal",
            version="1.0",
            description="阈值信号",
            long_threshold=0.02,
        )

        # register
        pkg_id = registry.register(pkg)
        assert pkg_id == "ThresholdSignal@1.0"
        print(f"  ✓ register() → {pkg_id}")

        # get
        loaded = registry.get(PackageType.SIGNAL, "ThresholdSignal", "1.0")
        assert loaded is not None
        assert loaded.name == "ThresholdSignal"
        assert isinstance(loaded, TestSignalPackage)
        assert loaded.long_threshold == 0.02
        print(f"  ✓ get() 返回 {type(loaded).__name__}, long_threshold={loaded.long_threshold}")

        # get_by_ref
        loaded_ref = registry.get_by_ref(PackageType.SIGNAL, "ref://ThresholdSignal@1.0")
        assert loaded_ref is not None
        assert loaded_ref.name == "ThresholdSignal"
        print(f"  ✓ get_by_ref() 正确")

        # list
        all_pkgs = registry.list(PackageType.SIGNAL)
        assert len(all_pkgs) == 1
        print(f"  ✓ list() 返回 {len(all_pkgs)} 个 package")

        # exists
        assert registry.exists(PackageType.SIGNAL, "ThresholdSignal", "1.0")
        print(f"  ✓ exists() 正确")

        print("  PASSED")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    print("=" * 60)
    print("P1 单元测试：Asset Package 标准化")
    print("=" * 60)

    test_ref_parse()
    test_package_serialize()
    test_storage()
    test_registry()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()

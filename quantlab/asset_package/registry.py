"""
PackageRegistry — Package 注册中心

职责：
  1. 注册 / 查询 / 版本管理 Package
  2. 将 manifest 字典反序列化为具体 Package 类
  3. 提供 ref 解析（ref://name@version → Package 实例）

与现有 AssetRegistry（asset/registry.py）的关系：
  - AssetRegistry 管理 QuantAsset（索引层）
  - PackageRegistry 管理 AssetPackage（配置层）
  - 两者通过 adapter 桥接（P4 实现）
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Type

from .base import AssetPackage, PackageType, Ref, parse_ref
from .storage import PackageStorage, get_package_storage

logger = logging.getLogger("quantlab.asset_package.registry")


# ==================================================================
# 类型注册表：PackageType → 具体类
# ==================================================================

_PACKAGE_CLASSES: Dict[PackageType, Type[AssetPackage]] = {}


def register_package_class(pkg_type: PackageType, cls: Type[AssetPackage]) -> None:
    """注册 Package 类型对应的类（供子模块调用）"""
    _PACKAGE_CLASSES[pkg_type] = cls
    logger.debug(f"Registered package class: {pkg_type.value} → {cls.__name__}")


def get_package_class(pkg_type: PackageType) -> Optional[Type[AssetPackage]]:
    """获取 Package 类型对应的类"""
    return _PACKAGE_CLASSES.get(pkg_type)


# ==================================================================
# PackageRegistry
# ==================================================================

class PackageRegistry:
    """
    Package 注册中心

    用法：
        reg = get_package_registry()
        reg.register(package)                          # 注册
        pkg = reg.get(PackageType.SIGNAL, "X", "1.0")  # 获取
        pkgs = reg.list(PackageType.SIGNAL)            # 列表
        pkg = reg.get_by_ref(PackageType.SIGNAL, "ref://X@1.0")  # ref 获取
    """

    def __init__(self, storage: Optional[PackageStorage] = None) -> None:
        self.storage = storage or get_package_storage()

    # ------------------------------------------------------------------
    # 注册 / 获取
    # ------------------------------------------------------------------

    def register(self, package: AssetPackage) -> str:
        """注册 Package（保存到 storage）"""
        self.storage.save(package)
        logger.info(f"Registered package: {package.id} ({package.package_type.value})")
        return package.id

    def get(self, pkg_type: PackageType, name: str, version: str) -> Optional[AssetPackage]:
        """获取 Package（返回反序列化后的实例）"""
        manifest = self.storage.load(pkg_type, name, version)
        return self._deserialize(manifest)

    def get_by_ref(self, pkg_type: PackageType, ref_str: str) -> Optional[AssetPackage]:
        """通过 ref 字符串获取 Package"""
        ref = parse_ref(ref_str)
        return self.get(pkg_type, ref.name, ref.version)

    def list(self, pkg_type: PackageType) -> List[AssetPackage]:
        """列出某类型的所有 Package"""
        manifests = self.storage.list(pkg_type)
        return [self._deserialize(m) for m in manifests]

    def list_by_name(self, pkg_type: PackageType, name: str) -> List[AssetPackage]:
        """列出某 Package 的所有版本"""
        versions = self.storage.list_versions(pkg_type, name)
        results = []
        for v in versions:
            pkg = self.get(pkg_type, name, v)
            if pkg:
                results.append(pkg)
        return results

    def exists(self, pkg_type: PackageType, name: str, version: str) -> bool:
        """检查 Package 是否存在"""
        return self.storage.exists(pkg_type, name, version)

    def delete(self, pkg_type: PackageType, name: str, version: str) -> bool:
        """删除 Package"""
        return self.storage.delete(pkg_type, name, version)

    # ------------------------------------------------------------------
    # 反序列化
    # ------------------------------------------------------------------

    def _deserialize(self, manifest: Dict[str, Any]) -> Optional[AssetPackage]:
        """将 manifest 字典反序列化为具体 Package 实例"""
        pkg_type_str = manifest.get("type", "")
        try:
            pkg_type = PackageType(pkg_type_str)
        except ValueError:
            logger.warning(f"Unknown package type: {pkg_type_str}")
            return None

        cls = get_package_class(pkg_type)
        if cls is None:
            logger.warning(f"No class registered for package type: {pkg_type.value}")
            return None

        try:
            return cls.from_manifest(manifest)
        except Exception as e:
            logger.error(f"Failed to deserialize package: {e}")
            return None


# ==================================================================
# 单例
# ==================================================================

_registry: Optional[PackageRegistry] = None


def get_package_registry() -> PackageRegistry:
    global _registry
    if _registry is None:
        _registry = PackageRegistry()
    return _registry

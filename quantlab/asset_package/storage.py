"""
PackageStorage — Package 文件系统存储

目录结构：
  storage/asset_packages/<type>/<name>@<version>/
    manifest.yaml    # 元数据 + ref 引用
    artifacts/        # 实际文件（可选）

与现有 AssetStorage（asset/storage.py）的关系：
  - AssetStorage 存 QuantAsset（索引层）
  - PackageStorage 存 AssetPackage（配置层，manifest 驱动）
  - 两者独立，PackageStorage 专注 manifest.yaml
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

import yaml

from .base import AssetPackage, PackageType, Ref, parse_ref

logger = logging.getLogger("quantlab.asset_package.storage")


DEFAULT_STORAGE_ROOT = "storage/asset_packages"

# PackageType → 存储子目录
PACKAGE_TYPE_DIRS = {
    PackageType.MODEL: "model",
    PackageType.SIGNAL: "signal",
    PackageType.POSITION: "position",
    PackageType.RISK: "risk",
    PackageType.EXECUTION: "execution",
    PackageType.OBSERVE: "observe",
    PackageType.STRATEGY: "strategy",
}


class PackageStorage:
    """
    Package 文件系统存储

    用法：
        store = PackageStorage("storage/asset_packages")
        store.save(package)
        pkg = store.load(PackageType.SIGNAL, "ThresholdSignal", "1.0")
        store.exists(PackageType.SIGNAL, "ThresholdSignal", "1.0")
        store.list(PackageType.SIGNAL)
    """

    def __init__(self, root: str = DEFAULT_STORAGE_ROOT) -> None:
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    # ------------------------------------------------------------------
    # 路径工具
    # ------------------------------------------------------------------

    def _type_dir(self, pkg_type: PackageType) -> str:
        subdir = PACKAGE_TYPE_DIRS.get(pkg_type, pkg_type.value.lower())
        return os.path.join(self.root, subdir)

    def _package_dir(self, pkg_type: PackageType, name: str, version: str) -> str:
        return os.path.join(self._type_dir(pkg_type), f"{name}@{version}")

    def _manifest_path(self, pkg_type: PackageType, name: str, version: str) -> str:
        return os.path.join(self._package_dir(pkg_type, name, version), "manifest.yaml")

    def _artifacts_dir(self, pkg_type: PackageType, name: str, version: str) -> str:
        return os.path.join(self._package_dir(pkg_type, name, version), "artifacts")

    # ------------------------------------------------------------------
    # 保存 / 加载
    # ------------------------------------------------------------------

    def save(self, package: AssetPackage) -> str:
        """保存 Package，返回 manifest 路径"""
        pkg_dir = self._package_dir(package.package_type, package.name, package.version)
        os.makedirs(pkg_dir, exist_ok=True)
        os.makedirs(self._artifacts_dir(package.package_type, package.name, package.version), exist_ok=True)

        manifest_path = self._manifest_path(package.package_type, package.name, package.version)
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(package.to_manifest_yaml())

        logger.info(f"Saved package {package.id} → {manifest_path}")
        return manifest_path

    def save_artifact(self, pkg_type: PackageType, name: str, version: str,
                      artifact_name: str, data: bytes) -> str:
        """保存附加产物文件"""
        art_dir = self._artifacts_dir(pkg_type, name, version)
        os.makedirs(art_dir, exist_ok=True)
        path = os.path.join(art_dir, artifact_name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load(self, pkg_type: PackageType, name: str, version: str) -> Dict[str, Any]:
        """加载 manifest（返回原始字典，由 Registry 反序列化为具体类）"""
        manifest_path = self._manifest_path(pkg_type, name, version)
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Package not found: {pkg_type.value}/{name}@{version}")
        with open(manifest_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def load_artifact(self, pkg_type: PackageType, name: str, version: str,
                      artifact_name: str) -> bytes:
        """加载附加产物文件"""
        path = os.path.join(self._artifacts_dir(pkg_type, name, version), artifact_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Artifact not found: {artifact_name}")
        with open(path, "rb") as f:
            return f.read()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def exists(self, pkg_type: PackageType, name: str, version: str) -> bool:
        """检查 Package 是否存在"""
        return os.path.exists(self._manifest_path(pkg_type, name, version))

    def list(self, pkg_type: PackageType) -> List[Dict[str, Any]]:
        """列出某类型的所有 Package manifest"""
        type_dir = self._type_dir(pkg_type)
        if not os.path.exists(type_dir):
            return []
        results = []
        for entry in os.listdir(type_dir):
            manifest_path = os.path.join(type_dir, entry, "manifest.yaml")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r", encoding="utf-8") as f:
                    results.append(yaml.safe_load(f))
        return results

    def list_versions(self, pkg_type: PackageType, name: str) -> List[str]:
        """列出某 Package 的所有版本"""
        type_dir = self._type_dir(pkg_type)
        if not os.path.exists(type_dir):
            return []
        versions = []
        for entry in os.listdir(type_dir):
            if entry.startswith(f"{name}@"):
                version = entry.rsplit("@", 1)[1]
                versions.append(version)
        return sorted(versions)

    def delete(self, pkg_type: PackageType, name: str, version: str) -> bool:
        """删除 Package"""
        pkg_dir = self._package_dir(pkg_type, name, version)
        if not os.path.exists(pkg_dir):
            return False
        shutil.rmtree(pkg_dir)
        logger.info(f"Deleted package {name}@{version}")
        return True

    # ------------------------------------------------------------------
    # ref 解析
    # ------------------------------------------------------------------

    def load_by_ref(self, pkg_type: PackageType, ref_str: str) -> Dict[str, Any]:
        """通过 ref 字符串加载 Package"""
        ref = parse_ref(ref_str)
        return self.load(pkg_type, ref.name, ref.version)


# ==================================================================
# 单例
# ==================================================================

_storage: Optional[PackageStorage] = None


def get_package_storage() -> PackageStorage:
    global _storage
    if _storage is None:
        _storage = PackageStorage()
    return _storage

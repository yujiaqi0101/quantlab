"""
ModelAssetAdapter — 现有 ModelPackage 适配为 QuantAsset

保持向后兼容：
  - 现有 ModelRegistry API 仍可用
  - ModelPackage 可通过适配器注册到 AssetRegistry

适配流程：
  ModelPackage (M6)
    ↓ adapt
  ModelPackageAsset (Asset)
    ↓ register
  AssetRegistry
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..ml.registry.package import ModelPackage, ModelManifest
from ..ml.registry.registry import ModelVersion, LifecycleStatus
from .base import AssetStatus, AssetType, ModelPackageAsset
from .registry import AssetRegistry, get_asset_registry
from .version import SemanticVersion

logger = logging.getLogger("quantlab.asset.adapter")


class ModelAssetAdapter:
    """
    ModelPackage → ModelPackageAsset 适配器

    用法：
        adapter = ModelAssetAdapter()
        asset = adapter.from_package(package)
        registry.register(asset)
    """

    def from_package(self, package: ModelPackage) -> ModelPackageAsset:
        """从 ModelPackage 转换为 ModelPackageAsset"""
        manifest = package.manifest

        # 解析版本号
        version_str = str(manifest.version) if manifest.version else "1.0.0"
        # 如果是简单数字（如 3），转换为 SemVer
        if version_str.isdigit():
            version_str = f"1.{version_str}.0"

        # 映射状态
        status = self._map_status(manifest.status)

        asset = ModelPackageAsset(
            asset_id=f"ASSET-{manifest.id}" if manifest.id else "",
            name=manifest.id or "unnamed_model",
            family=manifest.family or manifest.id or "default",
            version=version_str,
            asset_type=AssetType.MODEL_PACKAGE,
            status=status,
            model_package_id=manifest.id or "",
            algorithm=manifest.algorithm,
            model_type=manifest.model_type,
            is_classifier=manifest.is_classifier,
            params=manifest.params,
            dataset_id=manifest.dataset_id,
            feature_set_id=manifest.feature_set_id,
            label_set_id=manifest.label_set_id,
            validation_passed=(manifest.status in ("VALIDATED", "CANDIDATE", "CHAMPION")),
            validation_score=0.0,  # 从 validation 结果填充
            validation_grade="",
            tags=manifest.tags,
            description=manifest.description,
        )

        # 如果 asset_id 为空，使用默认生成
        if not asset.asset_id or asset.asset_id == "ASSET-":
            import uuid
            asset.asset_id = f"ASSET-{uuid.uuid4().hex[:8]}"

        return asset

    def from_version(self, version: ModelVersion) -> ModelPackageAsset:
        """从 ModelVersion 转换为 ModelPackageAsset"""
        # 解析版本号
        version_str = str(version.version_number) if version.version_number else "1.0.0"
        if version_str.isdigit():
            version_str = f"1.{version_str}.0"

        status = self._map_lifecycle_status(version.lifecycle.value)

        asset = ModelPackageAsset(
            name=version.name,
            family=version.family or version.name,
            version=version_str,
            asset_type=AssetType.MODEL_PACKAGE,
            status=status,
            model_package_id=version.version_id,
            algorithm=version.model_type.value,
            model_type=version.model_type.value,
            is_classifier=version.is_classifier,
            params=version.params,
            metrics=version.metrics,
            dataset_id=version.dataset_id,
            feature_set_id="",
            label_set_id=version.label_id,
            validation_passed=(
                version.lifecycle
                in (
                    LifecycleStatus.VALIDATED,
                    LifecycleStatus.CANDIDATE,
                    LifecycleStatus.CHAMPION,
                )
            ),
            tags=version.tags,
            description=version.description,
        )

        return asset

    def _map_status(self, manifest_status: str) -> AssetStatus:
        """映射 ModelManifest.status → AssetStatus"""
        mapping = {
            "DRAFT": AssetStatus.DRAFT,
            "TRAINING": AssetStatus.DRAFT,
            "VALIDATING": AssetStatus.DRAFT,
            "VALIDATED": AssetStatus.ACTIVE,
            "CANDIDATE": AssetStatus.ACTIVE,
            "CHAMPION": AssetStatus.ACTIVE,
            "ARCHIVED": AssetStatus.ARCHIVED,
            "RETIRED": AssetStatus.ARCHIVED,
            "DEPRECATED": AssetStatus.DEPRECATED,
        }
        return mapping.get(manifest_status, AssetStatus.DRAFT)

    def _map_lifecycle_status(self, lifecycle: str) -> AssetStatus:
        """映射 LifecycleStatus → AssetStatus"""
        mapping = {
            "DRAFT": AssetStatus.DRAFT,
            "TRAINING": AssetStatus.DRAFT,
            "VALIDATING": AssetStatus.DRAFT,
            "VALIDATED": AssetStatus.ACTIVE,
            "CANDIDATE": AssetStatus.ACTIVE,
            "CHAMPION": AssetStatus.ACTIVE,
            "ARCHIVED": AssetStatus.ARCHIVED,
            "RETIRED": AssetStatus.ARCHIVED,
            "DEPRECATED": AssetStatus.DEPRECATED,
        }
        return mapping.get(lifecycle, AssetStatus.DRAFT)

    def register_package(
        self,
        package: ModelPackage,
        registry: Optional[AssetRegistry] = None,
    ) -> str:
        """
        将 ModelPackage 适配并注册到 AssetRegistry

        Returns:
            asset_id
        """
        registry = registry or get_asset_registry()
        asset = self.from_package(package)

        # Validation 门禁检查
        if not asset.validation_passed:
            raise ValueError(
                f"Cannot register unvalidated ModelPackage: {package.manifest.id}"
            )

        return registry.register(asset)

    def register_version(
        self,
        version: ModelVersion,
        registry: Optional[AssetRegistry] = None,
    ) -> str:
        """将 ModelVersion 适配并注册到 AssetRegistry"""
        registry = registry or get_asset_registry()
        asset = self.from_version(version)

        if not asset.validation_passed:
            raise ValueError(
                f"Cannot register unvalidated ModelVersion: {version.version_id}"
            )

        return registry.register(asset)

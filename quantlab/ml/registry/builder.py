"""
Model Package Builder — 模型包构建器（M6）

  Training 结束后不是只生成 model.pkl，而是：

    Training
      ↓
    TrainingResult
      ↓
    Validation（可选）
      ↓
    ModelPackageBuilder      ← 本模块
      ↓
    ModelRegistry（注册）
      ↓
    VersionManager
      ↓
    ChampionManager

  Builder 职责：
    1. 从 TrainingResult 提取 model + metrics + feature_importance
    2. 从 TrainingJob 提取 dataset_id / feature_set_id / label_set_id / params
    3. 调用 SnapshotManager 捕获 FeatureSet/LabelSet 快照
    4. 构建 ModelManifest
    5. 组装成 ModelPackage
    6. 保存到 ModelStore
    7. 注册到 ModelRegistry
"""

from __future__ import annotations

import importlib
import logging
import uuid
from typing import Any, Dict, Optional

import pandas as pd

from .package import ModelPackage, ModelManifest
from .snapshot import get_snapshot_manager
from .registry import ModelVersion, ModelRegistry, LifecycleStatus, get_model_registry
from .model_store import get_model_store
from .champion_pointer import ChampionPointer

logger = logging.getLogger("quantlab.ml.registry.builder")


class ModelPackageBuilder:
    """
    模型包构建器

    用法：
        builder = ModelPackageBuilder()
        pkg = builder.build(
            job=training_job,
            result=training_result,
            family="LGBM_Momentum",
        )
        # pkg 已保存到磁盘 + 注册到 Registry
    """

    def __init__(self) -> None:
        self.snapshot_mgr = get_snapshot_manager()
        self.store = get_model_store()
        self.registry = get_model_registry()

    def build(
        self,
        job: Any,
        result: Any,
        family: str = "",
        version_number: Optional[int] = None,
        description: str = "",
        tags: Optional[list] = None,
        parent_version_id: str = "",
        lineage_note: str = "",
        save: bool = True,
        register: bool = True,
    ) -> ModelPackage:
        """
        从 TrainingJob + TrainingResult 构建 ModelPackage

        Args:
            job: TrainingJob
            result: TrainingResult
            family: 模型族名（空则自动推断）
            version_number: 版本号（空则自动分配）
            description: 描述
            tags: 标签
            parent_version_id: 父版本 ID（用于血统）
            lineage_note: 血统变更说明
            save: 是否保存到磁盘
            register: 是否注册到 Registry

        Returns:
            ModelPackage
        """
        # 1. 推断 family
        if not family:
            family = self._infer_family(job)

        # 2. 分配 version_number
        if version_number is None:
            version_number = self.registry.get_next_version_number(family)

        # 3. 生成 version_id
        version_id = f"MV-{uuid.uuid4().hex[:8]}"

        # 4. 捕获 FeatureSet 快照
        feature_set_snapshot = None
        if job.feature_set_id:
            feature_set_snapshot = self.snapshot_mgr.capture_feature_set(job.feature_set_id)
        elif job.feature_ids:
            # 传统模式：构造一个临时 snapshot
            from .package import FeatureSetSnapshot
            feature_set_snapshot = FeatureSetSnapshot(
                feature_set_id="",
                name="inline_features",
                feature_ids=list(job.feature_ids),
                snapshot_at=pd.Timestamp.now().isoformat(),
            )

        # 5. 捕获 LabelSet 快照
        label_set_snapshot = None
        if job.label_set_id:
            label_set_snapshot = self.snapshot_mgr.capture_label_set(job.label_set_id)
        elif job.label_id:
            from .package import LabelSetSnapshot
            label_set_snapshot = LabelSetSnapshot(
                label_set_id="",
                name="inline_label",
                label_id=job.label_id,
                snapshot_at=pd.Timestamp.now().isoformat(),
            )

        # 6. 获取框架版本
        framework_version = self._get_framework_version(job.model_type.value)

        # 7. 构建 Manifest
        manifest = ModelManifest(
            id=f"{family}_v{version_number}",
            version=version_number,
            family=family,
            dataset_id=job.dataset_id,
            feature_set_id=job.feature_set_id,
            feature_set_hash=feature_set_snapshot.hash if feature_set_snapshot else "",
            label_set_id=job.label_set_id,
            label_set_hash=label_set_snapshot.hash if label_set_snapshot else "",
            algorithm=job.model_type.value.lower(),
            framework_version=framework_version,
            model_type=job.model_type.value,
            is_classifier=job.is_classifier,
            params=job.model_params,
            status=LifecycleStatus.TRAINING.value,
            description=description or job.notes,
            tags=tags or job.tags,
            parent_version_id=parent_version_id,
            lineage_note=lineage_note,
        )

        # 8. 构建 metrics
        metrics: Dict[str, Any] = {}
        if result.metrics:
            metrics = result.metrics.to_dict()
        metrics["n_train_samples"] = result.n_train_samples
        metrics["n_test_samples"] = result.n_test_samples
        metrics["train_time"] = round(result.train_time, 4)

        # 9. 构建 training_config
        training_config = {
            "train_ratio": job.train_ratio,
            "val_ratio": job.val_ratio,
            "methods": job.methods,
            "job_id": job.job_id,
        }

        # 10. 构建 lineage
        lineage_info = {
            "parent_version_id": parent_version_id,
            "lineage_note": lineage_note,
            "job_id": job.job_id,
            "experiment_id": result.experiment_id,
        }

        # 11. 组装 ModelPackage
        pkg = ModelPackage(
            manifest=manifest,
            model=result.model,
            metrics=metrics,
            validation={},
            training_config=training_config,
            lineage=lineage_info,
            feature_set_snapshot=feature_set_snapshot,
            label_set_snapshot=label_set_snapshot,
            version_id=version_id,
        )

        # 12. 保存到磁盘
        if save:
            version_dir = self.store.save_package(pkg)
            logger.info(f"ModelPackage saved: {manifest.id} → {version_dir}")

            # 保存特征重要性到 artifacts
            if result.feature_importance_by_method:
                from .artifacts import ArtifactStore
                artifacts_dir = self.store._version_dir(family, version_number)
                artifacts_dir = artifacts_dir.replace("\\", "/")
                # 使用 store 的路径计算
                version_dir = self.store._version_dir(family, version_number)
                art_store = ArtifactStore(f"{version_dir}/artifacts")
                art_store.save_importance(result.feature_importance_by_method)

        # 13. 注册到 Registry
        if register:
            self._register_package(pkg, job, result)

        return pkg

    def _register_package(self, pkg: ModelPackage, job: Any, result: Any) -> None:
        """将 ModelPackage 注册到 ModelRegistry（兼容旧 ModelVersion）"""
        from ..model import ModelType

        # 转换为 ModelVersion
        try:
            model_type = ModelType(pkg.manifest.model_type)
        except ValueError:
            model_type = ModelType.LIGHTGBM

        version = ModelVersion(
            version_id=pkg.version_id,
            name=pkg.manifest.id,
            model_type=model_type,
            params=pkg.manifest.params,
            metrics=pkg.metrics,
            dataset_id=pkg.manifest.dataset_id,
            feature_ids=(
                pkg.feature_set_snapshot.feature_ids
                if pkg.feature_set_snapshot else []
            ),
            label_id=(
                pkg.label_set_snapshot.label_id
                if pkg.label_set_snapshot else ""
            ),
            is_classifier=pkg.manifest.is_classifier,
            created_at=pkg.manifest.created_at,
            description=pkg.manifest.description,
            tags=pkg.manifest.tags,
            family=pkg.manifest.family,
            version_number=pkg.manifest.version,
            lifecycle=LifecycleStatus.TRAINING,
            parent_version_id=pkg.manifest.parent_version_id,
            lineage_note=pkg.manifest.lineage_note,
        )
        if pkg.model is not None:
            version.set_model(pkg.model)

        self.registry.register(version)
        logger.info(f"ModelPackage registered: {pkg.manifest.id} ({pkg.version_id})")

    @staticmethod
    def _infer_family(job: Any) -> str:
        """从 job 推断 family 名"""
        if job.name and "_v" in job.name:
            return job.name.rsplit("_v", 1)[0]
        # 默认：{MODEL_TYPE}_{FEATURE_SET}
        parts = [job.model_type.value]
        if job.feature_set_id:
            parts.append(job.feature_set_id)
        return "_".join(parts)

    @staticmethod
    def _get_framework_version(model_type: str) -> str:
        """获取框架版本"""
        version_map = {
            "LIGHTGBM": "lightgbm",
            "XGBOOST": "xgboost",
            "RANDOM_FOREST": "sklearn",
            "LINEAR_REGRESSION": "sklearn",
            "LOGISTIC_REGRESSION": "sklearn",
        }
        pkg_name = version_map.get(model_type, "")
        if not pkg_name:
            return ""
        try:
            mod = importlib.import_module(pkg_name)
            return f"{pkg_name}=={getattr(mod, '__version__', 'unknown')}"
        except ImportError:
            return pkg_name


# 模块级单例
_builder: Optional[ModelPackageBuilder] = None


def get_package_builder() -> ModelPackageBuilder:
    global _builder
    if _builder is None:
        _builder = ModelPackageBuilder()
    return _builder

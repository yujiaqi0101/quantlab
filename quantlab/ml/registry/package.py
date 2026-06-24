"""
Model Package — 模型包（M6 升级核心）

将 Model 从"一个训练结果"升级为"可持续进化的资产（Asset）"。

  Model = 权重 + 元数据 + 配置 + 验证结果 + 依赖定义

  ModelPackage
  ├── Manifest          (manifest.yaml)   模型元信息
  ├── Model             (model.pkl)       模型权重
  ├── FeatureSetSnapshot (snapshot/feature_set.yaml)  特征定义快照
  ├── LabelSetSnapshot   (snapshot/label_set.yaml)    标签定义快照
  ├── Metrics           (metrics.json)    训练指标
  ├── Validation        (validation.json) 验证结果
  ├── TrainingConfig    (training.yaml)   训练配置
  ├── Lineage           (lineage.json)    血统信息
  └── Artifacts         (artifacts/)      SHAP/Importance/WalkForward 等

设计原则：
  1. Model 必须自己携带 Feature Definition（防止训练/实盘特征不一致）
  2. FeatureSet 引用 + 快照（不复制代码，但保存快照防止源修改影响旧模型）
  3. Champion 用 pointer.yaml（runtime 永远 load_champion()，策略无需修改）
"""

from __future__ import annotations

import json
import logging
import os
import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from ..model import Model, ModelType

logger = logging.getLogger("quantlab.ml.registry.package")


# ==================================================================
# Model Manifest — 模型清单
# ==================================================================

@dataclass
class ModelManifest:
    """
    模型清单（manifest.yaml）

    每个模型包的入口文件，描述模型的所有元信息。

    用法：
        m = ModelManifest(
            id="LGBM_Momentum_v3",
            version=3,
            family="LGBM_Momentum",
            algorithm="lightgbm",
            dataset_id="crypto_1h_v2",
            feature_set_id="momentum_v2",
            label_id="future_return_10",
        )
        m.save("/path/to/manifest.yaml")
        m2 = ModelManifest.load("/path/to/manifest.yaml")
    """
    id: str = ""                                    # 如 LGBM_Momentum_v3
    version: int = 1                                # 版本号
    family: str = ""                                # 模型族
    created_at: str = ""

    # 数据依赖
    dataset_id: str = ""
    dataset_name: str = ""

    # 特征依赖（引用 + hash）
    feature_set_id: str = ""
    feature_set_hash: str = ""                      # 快照 hash，防止源修改

    # 标签依赖（引用 + hash）
    label_set_id: str = ""
    label_set_hash: str = ""

    # 算法
    algorithm: str = ""                             # lightgbm / xgboost / ...
    framework_version: str = ""                     # lightgbm==4.x
    model_type: str = ""                            # ModelType.value
    is_classifier: bool = False
    params: Dict[str, Any] = field(default_factory=dict)

    # 状态
    status: str = "DRAFT"                           # LifecycleStatus.value
    promoted_at: str = ""

    # 描述
    description: str = ""
    tags: List[str] = field(default_factory=list)

    # 血统
    parent_version_id: str = ""
    lineage_note: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        if not self.id:
            self.id = f"{self.family}_v{self.version}"
        if not self.algorithm:
            self.algorithm = self.model_type.lower() if self.model_type else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version": self.version,
            "family": self.family,
            "created_at": self.created_at,
            "dataset_id": self.dataset_id,
            "dataset_name": self.dataset_name,
            "feature_set_id": self.feature_set_id,
            "feature_set_hash": self.feature_set_hash,
            "label_set_id": self.label_set_id,
            "label_set_hash": self.label_set_hash,
            "algorithm": self.algorithm,
            "framework_version": self.framework_version,
            "model_type": self.model_type,
            "is_classifier": self.is_classifier,
            "params": self.params,
            "status": self.status,
            "promoted_at": self.promoted_at,
            "description": self.description,
            "tags": self.tags,
            "parent_version_id": self.parent_version_id,
            "lineage_note": self.lineage_note,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ModelManifest":
        return cls(
            id=d.get("id", ""),
            version=d.get("version", 1),
            family=d.get("family", ""),
            created_at=d.get("created_at", ""),
            dataset_id=d.get("dataset_id", ""),
            dataset_name=d.get("dataset_name", ""),
            feature_set_id=d.get("feature_set_id", ""),
            feature_set_hash=d.get("feature_set_hash", ""),
            label_set_id=d.get("label_set_id", ""),
            label_set_hash=d.get("label_set_hash", ""),
            algorithm=d.get("algorithm", ""),
            framework_version=d.get("framework_version", ""),
            model_type=d.get("model_type", ""),
            is_classifier=d.get("is_classifier", False),
            params=d.get("params", {}),
            status=d.get("status", "DRAFT"),
            promoted_at=d.get("promoted_at", ""),
            description=d.get("description", ""),
            tags=d.get("tags", []),
            parent_version_id=d.get("parent_version_id", ""),
            lineage_note=d.get("lineage_note", ""),
        )

    def save(self, path: str) -> None:
        """保存为 manifest.yaml"""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def load(cls, path: str) -> "ModelManifest":
        """从 manifest.yaml 加载"""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)


# ==================================================================
# FeatureSet / LabelSet Snapshot — 依赖快照
# ==================================================================

@dataclass
class FeatureSetSnapshot:
    """
    特征集合快照

    保存 FeatureSet 的完整定义（feature_ids + 每个 feature 的参数），
    防止 FeatureSet 源被修改后旧模型无法恢复。

    存储为 snapshot/feature_set.yaml
    """
    feature_set_id: str = ""
    name: str = ""
    feature_ids: List[str] = field(default_factory=list)
    feature_defs: List[Dict[str, Any]] = field(default_factory=list)  # 每个 feature 的完整定义
    hash: str = ""                                  # 内容 hash
    snapshot_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_set_id": self.feature_set_id,
            "name": self.name,
            "feature_ids": self.feature_ids,
            "feature_defs": self.feature_defs,
            "hash": self.hash,
            "snapshot_at": self.snapshot_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeatureSetSnapshot":
        return cls(
            feature_set_id=d.get("feature_set_id", ""),
            name=d.get("name", ""),
            feature_ids=d.get("feature_ids", []),
            feature_defs=d.get("feature_defs", []),
            hash=d.get("hash", ""),
            snapshot_at=d.get("snapshot_at", ""),
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def load(cls, path: str) -> "FeatureSetSnapshot":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)


@dataclass
class LabelSetSnapshot:
    """
    标签集合快照

    存储为 snapshot/label_set.yaml
    """
    label_set_id: str = ""
    name: str = ""
    label_id: str = ""
    label_type: str = "regression"
    classes: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    hash: str = ""
    snapshot_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label_set_id": self.label_set_id,
            "name": self.name,
            "label_id": self.label_id,
            "label_type": self.label_type,
            "classes": self.classes,
            "params": self.params,
            "hash": self.hash,
            "snapshot_at": self.snapshot_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "LabelSetSnapshot":
        return cls(
            label_set_id=d.get("label_set_id", ""),
            name=d.get("name", ""),
            label_id=d.get("label_id", ""),
            label_type=d.get("label_type", "regression"),
            classes=d.get("classes", []),
            params=d.get("params", {}),
            hash=d.get("hash", ""),
            snapshot_at=d.get("snapshot_at", ""),
        )

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @classmethod
    def load(cls, path: str) -> "LabelSetSnapshot":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)


# ==================================================================
# Model Package — 完整模型包
# ==================================================================

@dataclass
class ModelPackage:
    """
    完整模型包

    一个模型 = 权重 + 元数据 + 配置 + 验证结果 + 依赖定义

    目录结构：
      {family}/v{version}/
      ├── manifest.yaml           模型清单
      ├── model.pkl               模型权重
      ├── metrics.json            训练指标
      ├── validation.json         验证结果
      ├── training.yaml           训练配置
      ├── lineage.json            血统信息
      ├── snapshot/
      │   ├── feature_set.yaml    特征定义快照
      │   └── label_set.yaml      标签定义快照
      └── artifacts/
          ├── importance.json     特征重要性
          ├── walkforward.html    Walk Forward 报告
          ├── shap.parquet        SHAP 值
          └── training.log        训练日志

    用法：
        pkg = ModelPackage(manifest=manifest, model=model, metrics=metrics)
        pkg.save("/path/to/version_dir")
        pkg2 = ModelPackage.load("/path/to/version_dir")
        model = pkg2.load_model()
    """
    manifest: ModelManifest = field(default_factory=ModelManifest)
    model: Optional[Model] = None                   # 模型对象（不直接序列化到 manifest）
    metrics: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)
    training_config: Dict[str, Any] = field(default_factory=dict)
    lineage: Dict[str, Any] = field(default_factory=dict)
    feature_set_snapshot: Optional[FeatureSetSnapshot] = None
    label_set_snapshot: Optional[LabelSetSnapshot] = None
    artifacts: Dict[str, str] = field(default_factory=dict)  # name → path（相对路径）

    # 内存中的 version_id（兼容旧 ModelVersion）
    version_id: str = ""

    def to_dict(self, include_model_info: bool = False) -> Dict[str, Any]:
        d = {
            "version_id": self.version_id,
            "manifest": self.manifest.to_dict(),
            "metrics": self.metrics,
            "validation": self.validation,
            "training_config": self.training_config,
            "lineage": self.lineage,
            "has_model": self.model is not None,
            "has_feature_set_snapshot": self.feature_set_snapshot is not None,
            "has_label_set_snapshot": self.label_set_snapshot is not None,
            "artifacts": list(self.artifacts.keys()),
        }
        if include_model_info and self.model:
            d["model_info"] = self.model.to_dict()
        if self.feature_set_snapshot:
            d["feature_set_snapshot"] = self.feature_set_snapshot.to_dict()
        if self.label_set_snapshot:
            d["label_set_snapshot"] = self.label_set_snapshot.to_dict()
        return d

    # ------------------------------------------------------------------
    # 保存 / 加载
    # ------------------------------------------------------------------

    def save(self, version_dir: str) -> str:
        """
        保存完整 ModelPackage 到目录

        Args:
            version_dir: 版本目录路径（如 storage/models/LGBM_Momentum/v3/）

        Returns:
            保存的目录路径
        """
        os.makedirs(version_dir, exist_ok=True)
        snapshot_dir = os.path.join(version_dir, "snapshot")
        artifacts_dir = os.path.join(version_dir, "artifacts")
        os.makedirs(snapshot_dir, exist_ok=True)
        os.makedirs(artifacts_dir, exist_ok=True)

        # 1. manifest.yaml
        self.manifest.save(os.path.join(version_dir, "manifest.yaml"))

        # 2. model.pkl
        if self.model is not None:
            model_path = os.path.join(version_dir, "model.pkl")
            try:
                with open(model_path, "wb") as f:
                    pickle.dump(self.model, f)
            except Exception as e:
                logger.error(f"Failed to save model.pkl: {e}")
                raise

        # 3. metrics.json
        self._save_json(os.path.join(version_dir, "metrics.json"), self.metrics)

        # 4. validation.json
        self._save_json(os.path.join(version_dir, "validation.json"), self.validation)

        # 5. training.yaml
        self._save_yaml(os.path.join(version_dir, "training.yaml"), self.training_config)

        # 6. lineage.json
        self._save_json(os.path.join(version_dir, "lineage.json"), self.lineage)

        # 7. snapshot/
        if self.feature_set_snapshot:
            self.feature_set_snapshot.save(os.path.join(snapshot_dir, "feature_set.yaml"))
        if self.label_set_snapshot:
            self.label_set_snapshot.save(os.path.join(snapshot_dir, "label_set.yaml"))

        logger.info(f"ModelPackage saved: {self.manifest.id} → {version_dir}")
        return version_dir

    @classmethod
    def load(
        cls,
        version_dir: str,
        load_model: bool = True,
    ) -> "ModelPackage":
        """
        从目录加载 ModelPackage

        Args:
            version_dir: 版本目录路径
            load_model: 是否加载 model.pkl（大文件可延迟加载）

        Returns:
            ModelPackage
        """
        manifest = ModelManifest.load(os.path.join(version_dir, "manifest.yaml"))

        # metrics
        metrics = cls._load_json(os.path.join(version_dir, "metrics.json"))
        # validation
        validation = cls._load_json(os.path.join(version_dir, "validation.json"))
        # training
        training_config = cls._load_yaml(os.path.join(version_dir, "training.yaml"))
        # lineage
        lineage = cls._load_json(os.path.join(version_dir, "lineage.json"))

        # snapshots
        fs_snapshot = None
        fs_path = os.path.join(version_dir, "snapshot", "feature_set.yaml")
        if os.path.exists(fs_path):
            fs_snapshot = FeatureSetSnapshot.load(fs_path)

        ls_snapshot = None
        ls_path = os.path.join(version_dir, "snapshot", "label_set.yaml")
        if os.path.exists(ls_path):
            ls_snapshot = LabelSetSnapshot.load(ls_path)

        # artifacts 列表
        artifacts: Dict[str, str] = {}
        artifacts_dir = os.path.join(version_dir, "artifacts")
        if os.path.exists(artifacts_dir):
            for fn in os.listdir(artifacts_dir):
                artifacts[fn] = f"artifacts/{fn}"

        # model
        model: Optional[Model] = None
        if load_model:
            model_path = os.path.join(version_dir, "model.pkl")
            if os.path.exists(model_path):
                try:
                    with open(model_path, "rb") as f:
                        model = pickle.load(f)
                except Exception as e:
                    logger.error(f"Failed to load model.pkl: {e}")

        return cls(
            manifest=manifest,
            model=model,
            metrics=metrics,
            validation=validation,
            training_config=training_config,
            lineage=lineage,
            feature_set_snapshot=fs_snapshot,
            label_set_snapshot=ls_snapshot,
            artifacts=artifacts,
        )

    def load_model(self) -> Optional[Model]:
        """加载模型对象（如果尚未加载）"""
        if self.model is not None:
            return self.model
        # 子类需知道路径才能延迟加载，这里返回 None
        return self.model

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _save_json(path: str, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def _load_json(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _save_yaml(path: str, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    @staticmethod
    def _load_yaml(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


# ==================================================================
# 包级常量
# ==================================================================

# ModelPackage 目录内的文件名
MANIFEST_FILE = "manifest.yaml"
MODEL_FILE = "model.pkl"
METRICS_FILE = "metrics.json"
VALIDATION_FILE = "validation.json"
TRAINING_FILE = "training.yaml"
LINEAGE_FILE = "lineage.json"
SNAPSHOT_DIR = "snapshot"
ARTIFACTS_DIR = "artifacts"
FEATURE_SET_SNAPSHOT_FILE = "feature_set.yaml"
LABEL_SET_SNAPSHOT_FILE = "label_set.yaml"

# .qlmodel 包扩展名
QLMODEL_EXTENSION = ".qlmodel"

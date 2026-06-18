"""
Model Store — 模型文件统一管理

ML Lab M4 第三部分：不要让模型散落在磁盘

  目录结构：
    storage/models/
    └── LGBM_Momentum/                # Family
        ├── v1/
        │   ├── model.pkl             # 模型对象
        │   └── metadata.json         # 版本元信息
        ├── v2/
        │   ├── model.pkl
        │   └── metadata.json
        └── v3/
            ├── model.pkl
            └── metadata.json

  接口：
    save(version)        保存模型 + 元信息
    load(version_id)     加载模型 + 元信息
    delete(version_id)   删除
    exists(version_id)   检查是否存在
    list_files(family)   列出 family 下所有版本文件
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import shutil
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..model import Model
from .registry import ModelVersion, LifecycleStatus

logger = logging.getLogger("quantlab.ml.registry.store")


# 默认模型存储根目录
DEFAULT_MODELS_DIR = "storage/models"


class ModelStore:
    """
    模型文件存储

    用法：
        store = ModelStore("storage/models")
        store.save(version)                    # 保存模型 + 元信息
        version, model = store.load("MV-xxx")  # 加载
        store.delete("MV-xxx")                 # 删除
    """

    def __init__(self, root_dir: str = DEFAULT_MODELS_DIR) -> None:
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # 路径计算
    # ------------------------------------------------------------------

    def _family_dir(self, family: str) -> str:
        """族目录：storage/models/LGBM_Momentum/"""
        safe_family = self._sanitize(family)
        return os.path.join(self.root_dir, safe_family)

    def _version_dir(self, family: str, version_number: int) -> str:
        """版本目录：storage/models/LGBM_Momentum/v3/"""
        return os.path.join(self._family_dir(family), f"v{version_number}")

    def _model_path(self, family: str, version_number: int) -> str:
        """模型文件路径"""
        return os.path.join(self._version_dir(family, version_number), "model.pkl")

    def _metadata_path(self, family: str, version_number: int) -> str:
        """元信息文件路径"""
        return os.path.join(self._version_dir(family, version_number), "metadata.json")

    @staticmethod
    def _sanitize(name: str) -> str:
        """清理文件名中的非法字符"""
        for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            name = name.replace(ch, '_')
        return name

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    def save(self, version: ModelVersion) -> str:
        """
        保存模型版本到磁盘

        Args:
            version: ModelVersion（应已 set_model）

        Returns:
            保存的版本目录路径
        """
        version_dir = self._version_dir(version.family, version.version_number)
        os.makedirs(version_dir, exist_ok=True)

        # 保存模型对象
        model_path = self._model_path(version.family, version.version_number)
        if version._model is not None:
            try:
                with open(model_path, "wb") as f:
                    pickle.dump(version._model, f)
                logger.info(f"Model saved: {model_path}")
            except Exception as e:
                logger.error(f"Failed to save model: {e}")
                raise
        else:
            logger.warning(f"Version {version.version_id} has no model object, skipping pkl")

        # 保存元信息
        metadata = version.to_dict(include_model=False)
        metadata_path = self._metadata_path(version.family, version.version_number)
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            f"ModelVersion saved: {version.name} → {version_dir}"
        )
        return version_dir

    # ------------------------------------------------------------------
    # 加载
    # ------------------------------------------------------------------

    def load(self, version_id: str) -> Tuple[Optional[ModelVersion], Optional[Model]]:
        """
        根据 version_id 加载模型

        Args:
            version_id: 如 "MV-abc123"

        Returns:
            (ModelVersion, Model) 或 (None, None)
        """
        # 在所有 family 目录下搜索 metadata.json
        metadata_path = self._find_metadata(version_id)
        if metadata_path is None:
            logger.warning(f"Version {version_id} not found in store")
            return None, None

        # 加载元信息
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        version = self._dict_to_version(data)

        # 加载模型对象
        model: Optional[Model] = None
        model_path = os.path.join(os.path.dirname(metadata_path), "model.pkl")
        if os.path.exists(model_path):
            try:
                with open(model_path, "rb") as f:
                    model = pickle.load(f)
                version.set_model(model)
            except Exception as e:
                logger.error(f"Failed to load model: {e}")

        return version, model

    def load_metadata(self, version_id: str) -> Optional[Dict[str, Any]]:
        """仅加载元信息（不加载模型对象）"""
        metadata_path = self._find_metadata(version_id)
        if metadata_path is None:
            return None
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ------------------------------------------------------------------
    # 删除
    # ------------------------------------------------------------------

    def delete(self, version_id: str) -> bool:
        """删除版本目录"""
        metadata_path = self._find_metadata(version_id)
        if metadata_path is None:
            return False
        version_dir = os.path.dirname(metadata_path)
        shutil.rmtree(version_dir, ignore_errors=True)
        logger.info(f"ModelVersion deleted: {version_id}")
        return True

    def delete_family(self, family: str) -> bool:
        """删除整个族目录"""
        family_dir = self._family_dir(family)
        if not os.path.exists(family_dir):
            return False
        shutil.rmtree(family_dir, ignore_errors=True)
        logger.info(f"Model family deleted: {family}")
        return True

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def exists(self, version_id: str) -> bool:
        """检查版本是否存在"""
        return self._find_metadata(version_id) is not None

    def list_files(self, family: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出存储中的所有版本

        Args:
            family: 指定族，None 表示所有

        Returns:
            [{"family": ..., "version_number": ..., "version_id": ..., "path": ...}]
        """
        result: List[Dict[str, Any]] = []
        families = [family] if family else self._list_families()

        for fam in families:
            family_dir = self._family_dir(fam)
            if not os.path.exists(family_dir):
                continue
            for entry in sorted(os.listdir(family_dir)):
                if not entry.startswith("v"):
                    continue
                version_dir = os.path.join(family_dir, entry)
                metadata_path = os.path.join(version_dir, "metadata.json")
                if not os.path.exists(metadata_path):
                    continue
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    version_number = int(entry[1:])
                    result.append({
                        "family": fam,
                        "version_number": version_number,
                        "version_id": meta.get("version_id", ""),
                        "name": meta.get("name", ""),
                        "lifecycle": meta.get("lifecycle", ""),
                        "path": version_dir,
                    })
                except (json.JSONDecodeError, ValueError):
                    continue
        return result

    def list_families(self) -> List[str]:
        """列出所有族名"""
        return self._list_families()

    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        families = self._list_families()
        total_size = 0
        total_versions = 0
        for fam in families:
            family_dir = self._family_dir(fam)
            for dirpath, _, filenames in os.walk(family_dir):
                for fn in filenames:
                    fp = os.path.join(dirpath, fn)
                    if os.path.exists(fp):
                        total_size += os.path.getsize(fp)
                # 统计版本数（含 metadata.json 的目录）
                if "metadata.json" in filenames:
                    total_versions += 1
        return {
            "root_dir": self.root_dir,
            "n_families": len(families),
            "n_versions": total_versions,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "families": families,
        }

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _list_families(self) -> List[str]:
        """列出所有族目录名"""
        if not os.path.exists(self.root_dir):
            return []
        return sorted([
            d for d in os.listdir(self.root_dir)
            if os.path.isdir(os.path.join(self.root_dir, d))
        ])

    def _find_metadata(self, version_id: str) -> Optional[str]:
        """在所有族目录下搜索指定 version_id 的 metadata.json"""
        for fam in self._list_families():
            family_dir = self._family_dir(fam)
            for entry in os.listdir(family_dir):
                if not entry.startswith("v"):
                    continue
                metadata_path = os.path.join(family_dir, entry, "metadata.json")
                if not os.path.exists(metadata_path):
                    continue
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    if meta.get("version_id") == version_id:
                        return metadata_path
                except (json.JSONDecodeError, OSError):
                    continue
        return None

    @staticmethod
    def _dict_to_version(data: Dict[str, Any]) -> ModelVersion:
        """从 dict 恢复 ModelVersion"""
        from ..model import ModelType

        # 处理 enum 字段
        lifecycle_str = data.get("lifecycle", "TRAINING")
        try:
            lifecycle = LifecycleStatus(lifecycle_str)
        except ValueError:
            lifecycle = LifecycleStatus.TRAINING

        model_type_str = data.get("model_type", "LIGHTGBM")
        try:
            model_type = ModelType(model_type_str)
        except ValueError:
            model_type = ModelType.LIGHTGBM

        return ModelVersion(
            version_id=data.get("version_id", ""),
            name=data.get("name", ""),
            model_type=model_type,
            params=data.get("params", {}),
            metrics=data.get("metrics", {}),
            dataset_id=data.get("dataset_id", ""),
            feature_ids=data.get("feature_ids", []),
            label_id=data.get("label_id", ""),
            is_classifier=data.get("is_classifier", False),
            created_at=data.get("created_at", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            family=data.get("family", ""),
            version_number=data.get("version_number", 0),
            lifecycle=lifecycle,
            parent_version_id=data.get("parent_version_id", ""),
            lineage_note=data.get("lineage_note", ""),
            promoted_at=data.get("promoted_at", ""),
            retired_at=data.get("retired_at", ""),
        )


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_model_store: Optional[ModelStore] = None


def get_model_store(root_dir: str = DEFAULT_MODELS_DIR) -> ModelStore:
    """获取 ModelStore 单例"""
    global _model_store
    if _model_store is None:
        _model_store = ModelStore(root_dir)
    return _model_store

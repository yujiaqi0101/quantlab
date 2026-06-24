"""
AssetStorage — 资产存储层

Registry/Storage 职责分离：
  Registry：负责 Find / Load / Version / Compare（索引）
  Storage：负责 Read / Write（数据）

目录结构：
  storage/
  ├── datasets/           # Dataset 资产
  ├── features/           # FeatureSet 资产
  ├── labels/             # LabelSet 资产
  ├── models/             # ModelPackage 资产
  ├── strategies/         # StrategyPackage 资产
  ├── risk_profiles/      # RiskProfile 资产
  ├── deployment_profiles/# DeploymentProfile 资产
  └── artifacts/          # 通用产物（SHAP / Importance / WalkForward）

每个资产存储为：
  storage/{type}/{family}/{asset_id}/
  ├── manifest.json       # 资产元信息
  └── data.*              # 资产数据（pkl / parquet / json）
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import shutil
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from .base import AssetType, QuantAsset

logger = logging.getLogger("quantlab.asset.storage")


# 资产类型 → 存储子目录
ASSET_TYPE_DIRS = {
    AssetType.DATASET: "datasets",
    AssetType.FEATURE_SET: "features",
    AssetType.LABEL_SET: "labels",
    AssetType.MODEL_PACKAGE: "models",
    AssetType.STRATEGY_PACKAGE: "strategies",
    AssetType.RISK_PROFILE: "risk_profiles",
    AssetType.DEPLOYMENT_PROFILE: "deployment_profiles",
}

DEFAULT_STORAGE_ROOT = "storage/assets"


class AssetStorage:
    """
    资产存储层

    用法：
        store = AssetStorage("storage/assets")
        store.save(asset)                    # 保存资产 manifest + 数据
        manifest = store.load_manifest(asset_id)  # 加载 manifest
        location = store.get_location(asset)     # 获取存储路径
        store.exists(asset_id)               # 检查是否存在
    """

    def __init__(self, root_dir: str = DEFAULT_STORAGE_ROOT) -> None:
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)
        # 为每种类型创建子目录
        for subdir in ASSET_TYPE_DIRS.values():
            os.makedirs(os.path.join(self.root_dir, subdir), exist_ok=True)
        os.makedirs(os.path.join(self.root_dir, "artifacts"), exist_ok=True)

    # ------------------------------------------------------------------
    # 路径计算
    # ------------------------------------------------------------------

    def _type_dir(self, asset_type: AssetType) -> str:
        """类型目录：storage/assets/datasets/"""
        subdir = ASSET_TYPE_DIRS.get(asset_type, "misc")
        return os.path.join(self.root_dir, subdir)

    def _asset_dir(self, asset: QuantAsset) -> str:
        """资产目录：storage/assets/datasets/{family}/{asset_id}/"""
        safe_family = self._sanitize(asset.family or "default")
        return os.path.join(self._type_dir(asset.asset_type), safe_family, asset.asset_id)

    def _manifest_path(self, asset: QuantAsset) -> str:
        """manifest 路径"""
        return os.path.join(self._asset_dir(asset), "manifest.json")

    def _data_path(self, asset: QuantAsset, ext: str = "pkl") -> str:
        """数据文件路径"""
        return os.path.join(self._asset_dir(asset), f"data.{ext}")

    @staticmethod
    def _sanitize(name: str) -> str:
        """清理目录名（防止非法字符）"""
        return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)

    # ------------------------------------------------------------------
    # 保存 / 加载
    # ------------------------------------------------------------------

    def save(
        self,
        asset: QuantAsset,
        data: Any = None,
        data_format: str = "pkl",
    ) -> str:
        """
        保存资产

        Args:
            asset: 资产对象
            data: 资产数据（可选，如 DataFrame / dict / model 对象）
            data_format: 数据格式（pkl / parquet / json）

        Returns:
            存储位置路径
        """
        asset_dir = self._asset_dir(asset)
        os.makedirs(asset_dir, exist_ok=True)

        # 保存 manifest
        manifest = asset.to_dict()
        manifest_path = self._manifest_path(asset)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)

        # 保存数据
        if data is not None:
            data_path = self._data_path(asset, data_format)
            if data_format == "pkl":
                with open(data_path, "wb") as f:
                    pickle.dump(data, f)
            elif data_format == "parquet" and isinstance(data, pd.DataFrame):
                data.to_parquet(data_path)
            elif data_format == "json":
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            else:
                # 默认 pkl
                with open(data_path, "wb") as f:
                    pickle.dump(data, f)

        # 更新 asset 的 location
        asset.location = asset_dir
        logger.info(f"Asset saved: {asset.asset_id} → {asset_dir}")
        return asset_dir

    def load_manifest(self, asset_id: str, asset_type: AssetType) -> Optional[Dict[str, Any]]:
        """
        加载资产 manifest

        通过 asset_id 和 asset_type 定位。
        """
        # 搜索 asset_id
        asset_dir = self._find_asset_dir(asset_id, asset_type)
        if asset_dir is None:
            return None
        manifest_path = os.path.join(asset_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return None
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_data(self, asset_id: str, asset_type: AssetType, data_format: str = "pkl") -> Optional[Any]:
        """加载资产数据"""
        asset_dir = self._find_asset_dir(asset_id, asset_type)
        if asset_dir is None:
            return None
        data_path = os.path.join(asset_dir, f"data.{data_format}")
        if not os.path.exists(data_path):
            return None
        if data_format == "pkl":
            with open(data_path, "rb") as f:
                return pickle.load(f)
        elif data_format == "parquet":
            return pd.read_parquet(data_path)
        elif data_format == "json":
            with open(data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _find_asset_dir(self, asset_id: str, asset_type: AssetType) -> Optional[str]:
        """在类型目录下搜索 asset_id"""
        type_dir = self._type_dir(asset_type)
        if not os.path.exists(type_dir):
            return None
        # 遍历 family 目录
        for family_name in os.listdir(type_dir):
            family_dir = os.path.join(type_dir, family_name)
            if not os.path.isdir(family_dir):
                continue
            asset_dir = os.path.join(family_dir, asset_id)
            if os.path.isdir(asset_dir):
                return asset_dir
        return None

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def exists(self, asset_id: str, asset_type: AssetType) -> bool:
        """检查资产是否存在"""
        return self._find_asset_dir(asset_id, asset_type) is not None

    def get_location(self, asset: QuantAsset) -> str:
        """获取资产的存储位置（不实际创建）"""
        return self._asset_dir(asset)

    def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        family: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出存储中的资产

        Returns:
            manifest 列表
        """
        result = []
        types_to_list = [asset_type] if asset_type else list(AssetType)

        for at in types_to_list:
            type_dir = self._type_dir(at)
            if not os.path.exists(type_dir):
                continue
            for family_name in os.listdir(type_dir):
                if family and family_name != self._sanitize(family):
                    continue
                family_dir = os.path.join(type_dir, family_name)
                if not os.path.isdir(family_dir):
                    continue
                for asset_id in os.listdir(family_dir):
                    asset_dir = os.path.join(family_dir, asset_id)
                    if not os.path.isdir(asset_dir):
                        continue
                    manifest_path = os.path.join(asset_dir, "manifest.json")
                    if os.path.exists(manifest_path):
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            manifest = json.load(f)
                        result.append(manifest)

        return result

    def delete(self, asset_id: str, asset_type: AssetType) -> bool:
        """删除资产"""
        asset_dir = self._find_asset_dir(asset_id, asset_type)
        if asset_dir is None:
            return False
        shutil.rmtree(asset_dir)
        logger.info(f"Asset deleted: {asset_id}")
        return True

    # ------------------------------------------------------------------
    # 通用产物存储
    # ------------------------------------------------------------------

    def save_artifact(
        self,
        asset_id: str,
        artifact_name: str,
        data: Any,
        data_format: str = "pkl",
    ) -> str:
        """
        保存通用产物（SHAP / Importance / WalkForward 等）

        存储位置：storage/assets/artifacts/{asset_id}/{artifact_name}.{ext}
        """
        artifact_dir = os.path.join(self.root_dir, "artifacts", asset_id)
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = os.path.join(artifact_dir, f"{artifact_name}.{data_format}")

        if data_format == "pkl":
            with open(artifact_path, "wb") as f:
                pickle.dump(data, f)
        elif data_format == "json":
            with open(artifact_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        elif data_format == "parquet" and isinstance(data, pd.DataFrame):
            data.to_parquet(artifact_path)
        else:
            with open(artifact_path, "wb") as f:
                pickle.dump(data, f)

        return artifact_path

    def load_artifact(
        self,
        asset_id: str,
        artifact_name: str,
        data_format: str = "pkl",
    ) -> Optional[Any]:
        """加载通用产物"""
        artifact_path = os.path.join(
            self.root_dir, "artifacts", asset_id, f"{artifact_name}.{data_format}"
        )
        if not os.path.exists(artifact_path):
            return None
        if data_format == "pkl":
            with open(artifact_path, "rb") as f:
                return pickle.load(f)
        elif data_format == "json":
            with open(artifact_path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif data_format == "parquet":
            return pd.read_parquet(artifact_path)
        return None

    def list_artifacts(self, asset_id: str) -> List[str]:
        """列出资产的所有产物"""
        artifact_dir = os.path.join(self.root_dir, "artifacts", asset_id)
        if not os.path.exists(artifact_dir):
            return []
        return os.listdir(artifact_dir)


# 单例
_asset_storage: Optional[AssetStorage] = None


def get_asset_storage() -> AssetStorage:
    global _asset_storage
    if _asset_storage is None:
        _asset_storage = AssetStorage()
    return _asset_storage

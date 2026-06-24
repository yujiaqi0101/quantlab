"""
QuantAsset — 量化资产基类

QuantLab Asset Registry 的核心抽象。

所有量化资产（Dataset / FeatureSet / LabelSet / ModelPackage / StrategyPackage / ...）
都继承 QuantAsset，拥有统一的 id / name / version / hash / status。

设计原则：
  1. Asset 是索引，不是数据本身
  2. Asset 携带 manifest（元信息），真正数据放 Storage
  3. Asset 有生命周期：DRAFT → ACTIVE → ARCHIVED → DEPRECATED
  4. Asset 有 hash，用于完整性校验
"""

from __future__ import annotations

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd


class AssetType(str, Enum):
    """资产类型"""
    DATASET = "DATASET"
    FEATURE_SET = "FEATURE_SET"
    LABEL_SET = "LABEL_SET"
    MODEL_PACKAGE = "MODEL_PACKAGE"
    STRATEGY_PACKAGE = "STRATEGY_PACKAGE"
    RISK_PROFILE = "RISK_PROFILE"
    DEPLOYMENT_PROFILE = "DEPLOYMENT_PROFILE"


class AssetStatus(str, Enum):
    """资产生命周期状态"""
    DRAFT = "DRAFT"                 # 草稿
    ACTIVE = "ACTIVE"               # 活跃
    ARCHIVED = "ARCHIVED"           # 归档
    DEPRECATED = "DEPRECATED"       # 废弃


class AssetRelation(str, Enum):
    """资产血缘关系类型"""
    DERIVED_FROM = "DERIVED_FROM"           # 派生自（FeatureSet from Dataset）
    TRAINED_ON = "TRAINED_ON"               # 训练于（Model on FeatureSet+LabelSet）
    VALIDATED_BY = "VALIDATED_BY"           # 被验证（Model by ValidationRun）
    PACKAGED_FROM = "PACKAGED_FROM"         # 打包自（Package from Model）
    STRATEGY_USES = "STRATEGY_USES"         # 策略使用（Strategy uses Model）
    DEPLOYED_AS = "DEPLOYED_AS"             # 部署为（Deployment uses Strategy）


@dataclass
class QuantAsset(ABC):
    """
    量化资产基类

    所有资产类型继承此类，实现 to_manifest() 和 compute_hash()。

    用法：
        class DatasetAsset(QuantAsset):
            def to_manifest(self) -> dict:
                return {"symbols": self.symbols, ...}

            def compute_hash(self) -> str:
                return hashlib.sha256(...).hexdigest()
    """
    asset_id: str = field(default_factory=lambda: f"ASSET-{uuid.uuid4().hex[:8]}")
    name: str = ""
    family: str = ""                            # 资产族（如 LGBM_Momentum）
    version: str = "1.0.0"                      # SemVer 语义化版本
    asset_type: AssetType = AssetType.DATASET
    status: AssetStatus = AssetStatus.DRAFT
    created_at: str = ""
    author: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""
    hash: str = ""                              # 内容 hash（由 compute_hash 计算）
    location: str = ""                          # 存储位置（由 Storage 填充）

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = pd.Timestamp.now().isoformat()
        if not self.family:
            self.family = self.name or self.asset_type.value
        # 自动计算 hash（如果子类未在 __post_init__ 中覆盖）
        if not self.hash:
            self.hash = self.compute_hash()

    @abstractmethod
    def to_manifest(self) -> Dict[str, Any]:
        """
        返回资产的 manifest（元信息）

        子类必须实现，包含资产特有的元数据。
        """
        raise NotImplementedError

    @abstractmethod
    def compute_hash(self) -> str:
        """
        计算资产内容的 hash

        子类必须实现，用于完整性校验。
        """
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "family": self.family,
            "version": self.version,
            "asset_type": self.asset_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "author": self.author,
            "tags": self.tags,
            "description": self.description,
            "hash": self.hash,
            "location": self.location,
            "manifest": self.to_manifest(),
        }

    def to_index(self) -> Dict[str, Any]:
        """
        返回索引信息（Registry 保存的精简信息）

        Registry 只保存索引，不保存真正数据。
        """
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "family": self.family,
            "version": self.version,
            "asset_type": self.asset_type.value,
            "status": self.status.value,
            "created_at": self.created_at,
            "author": self.author,
            "tags": self.tags,
            "hash": self.hash,
            "location": self.location,
        }

    @staticmethod
    def _hash_dict(d: Dict[str, Any]) -> str:
        """辅助方法：对字典计算 SHA256 hash"""
        content = json.dumps(d, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


# ==================================================================
# 具体资产类型（轻量实现，适配现有对象）
# ==================================================================


@dataclass
class DatasetAsset(QuantAsset):
    """Dataset 资产"""
    dataset_id: str = ""
    symbols: List[str] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    frequency: str = "1d"
    n_rows: int = 0
    n_cols: int = 0
    asset_type: AssetType = AssetType.DATASET

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "symbols": self.symbols,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "frequency": self.frequency,
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "symbols": sorted(self.symbols),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "frequency": self.frequency,
            "n_rows": self.n_rows,
        })


@dataclass
class FeatureSetAsset(QuantAsset):
    """FeatureSet 资产"""
    feature_set_id: str = ""
    feature_ids: List[str] = field(default_factory=list)
    n_features: int = 0
    asset_type: AssetType = AssetType.FEATURE_SET

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "feature_set_id": self.feature_set_id,
            "feature_ids": self.feature_ids,
            "n_features": self.n_features,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "feature_ids": sorted(self.feature_ids),
            "n_features": self.n_features,
        })


@dataclass
class LabelSetAsset(QuantAsset):
    """LabelSet 资产"""
    label_set_id: str = ""
    label_id: str = ""
    label_type: str = ""
    horizon: int = 0
    asset_type: AssetType = AssetType.LABEL_SET

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "label_set_id": self.label_set_id,
            "label_id": self.label_id,
            "label_type": self.label_type,
            "horizon": self.horizon,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "label_id": self.label_id,
            "label_type": self.label_type,
            "horizon": self.horizon,
        })


@dataclass
class ModelPackageAsset(QuantAsset):
    """ModelPackage 资产"""
    model_package_id: str = ""
    algorithm: str = ""                         # lightgbm / xgboost / ...
    model_type: str = ""                         # ModelType.value
    is_classifier: bool = False
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    dataset_id: str = ""
    feature_set_id: str = ""
    label_set_id: str = ""
    validation_passed: bool = False
    validation_score: float = 0.0
    validation_grade: str = "F"
    asset_type: AssetType = AssetType.MODEL_PACKAGE

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "model_package_id": self.model_package_id,
            "algorithm": self.algorithm,
            "model_type": self.model_type,
            "is_classifier": self.is_classifier,
            "params": self.params,
            "metrics": self.metrics,
            "dataset_id": self.dataset_id,
            "feature_set_id": self.feature_set_id,
            "label_set_id": self.label_set_id,
            "validation_passed": self.validation_passed,
            "validation_score": self.validation_score,
            "validation_grade": self.validation_grade,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "algorithm": self.algorithm,
            "model_type": self.model_type,
            "params": self.params,
            "metrics": self.metrics,
            "dataset_id": self.dataset_id,
            "feature_set_id": self.feature_set_id,
            "label_set_id": self.label_set_id,
        })


@dataclass
class StrategyPackageAsset(QuantAsset):
    """StrategyPackage 资产"""
    strategy_id: str = ""
    model_asset_id: str = ""                    # 引用的 ModelPackage asset_id
    rules: Dict[str, Any] = field(default_factory=dict)
    asset_type: AssetType = AssetType.STRATEGY_PACKAGE

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "model_asset_id": self.model_asset_id,
            "rules": self.rules,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "strategy_id": self.strategy_id,
            "model_asset_id": self.model_asset_id,
            "rules": self.rules,
        })


@dataclass
class RiskProfileAsset(QuantAsset):
    """RiskProfile 资产"""
    max_position: float = 0.0
    max_drawdown: float = 0.0
    stop_loss: float = 0.0
    asset_type: AssetType = AssetType.RISK_PROFILE

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "max_position": self.max_position,
            "max_drawdown": self.max_drawdown,
            "stop_loss": self.stop_loss,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "max_position": self.max_position,
            "max_drawdown": self.max_drawdown,
            "stop_loss": self.stop_loss,
        })


@dataclass
class DeploymentProfileAsset(QuantAsset):
    """DeploymentProfile 资产"""
    strategy_asset_id: str = ""
    environment: str = "paper"                  # paper / live
    broker: str = ""
    asset_type: AssetType = AssetType.DEPLOYMENT_PROFILE

    def to_manifest(self) -> Dict[str, Any]:
        return {
            "strategy_asset_id": self.strategy_asset_id,
            "environment": self.environment,
            "broker": self.broker,
            "description": self.description,
        }

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "strategy_asset_id": self.strategy_asset_id,
            "environment": self.environment,
            "broker": self.broker,
        })

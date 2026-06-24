"""
auto_register — 自动注册资产到 AssetRegistry

各模块创建产物时调用对应函数，自动注册到 AssetRegistry 并建立血缘。

设计原则：
  1. try-except 容错：注册失败不阻断主流程，只记日志
  2. 幂等性：按 hash 去重，重复注册不创建新资产
  3. 统一入口：所有自动注册逻辑集中在此文件
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from .base import (
    AssetRelation,
    AssetStatus,
    AssetType,
    DatasetAsset,
    FeatureSetAsset,
    LabelSetAsset,
    ModelPackageAsset,
    StrategyPackageAsset,
)
from .registry import get_asset_registry

logger = logging.getLogger("quantlab.asset.auto_register")


def _find_by_hash(asset_type: AssetType, content_hash: str):
    """按 hash 查找已有资产（幂等性）"""
    reg = get_asset_registry()
    for asset in reg.list_assets(asset_type=asset_type):
        if asset.hash == content_hash:
            return asset
    return None


def register_dataset_asset(ds) -> Optional[str]:
    """
    将 Dataset 注册为 DATASET 资产

    Args:
        ds: quantlab.ml.dataset.Dataset 对象

    Returns:
        asset_id，失败返回 None
    """
    try:
        # 获取统计信息
        n_rows = 0
        n_cols = 0
        if hasattr(ds, "get_stats"):
            try:
                stats = ds.get_stats()
                n_rows = stats.n_rows
                n_cols = stats.n_cols
            except Exception:
                pass

        asset = DatasetAsset(
            name=ds.name or ds.dataset_id,
            family=ds.name or ds.dataset_id,
            version="1.0.0",
            dataset_id=ds.dataset_id,
            symbols=ds.symbols,
            start_date=ds.start_date,
            end_date=ds.end_date,
            frequency=ds.frequency,
            n_rows=n_rows,
            n_cols=n_cols,
            description=ds.description,
            tags=ds.tags,
            status=AssetStatus.ACTIVE,
        )

        # 幂等：hash 相同则返回已有资产
        existing = _find_by_hash(AssetType.DATASET, asset.hash)
        if existing:
            logger.debug(f"Dataset asset already exists: {existing.asset_id}")
            return existing.asset_id

        reg = get_asset_registry()
        reg.register(asset)
        return asset.asset_id
    except Exception as e:
        logger.warning(f"Failed to register Dataset asset: {e}")
        return None


def register_feature_set_asset(fs) -> Optional[str]:
    """
    将 FeatureSet 注册为 FEATURE_SET 资产

    Args:
        fs: quantlab.ml.feature.set.FeatureSet 对象

    Returns:
        asset_id，失败返回 None
    """
    try:
        asset = FeatureSetAsset(
            name=fs.name,
            family=fs.name,
            version=fs.version or "1.0",
            feature_set_id=fs.fs_id,
            feature_ids=fs.feature_ids,
            n_features=len(fs.feature_ids),
            description=fs.description,
            tags=fs.tags,
            status=AssetStatus.ACTIVE,
        )

        existing = _find_by_hash(AssetType.FEATURE_SET, asset.hash)
        if existing:
            logger.debug(f"FeatureSet asset already exists: {existing.asset_id}")
            return existing.asset_id

        reg = get_asset_registry()
        reg.register(asset)
        return asset.asset_id
    except Exception as e:
        logger.warning(f"Failed to register FeatureSet asset: {e}")
        return None


def register_label_set_asset(ls) -> Optional[str]:
    """
    将 LabelSet 注册为 LABEL_SET 资产

    Args:
        ls: quantlab.ml.label.set.LabelSet 对象

    Returns:
        asset_id，失败返回 None
    """
    try:
        asset = LabelSetAsset(
            name=ls.name,
            family=ls.name,
            version=ls.version or "1.0",
            label_set_id=ls.ls_id,
            label_id=ls.label_id,
            label_type=ls.label_type,
            horizon=0,
            description=ls.description,
            tags=ls.tags,
            status=AssetStatus.ACTIVE,
        )

        existing = _find_by_hash(AssetType.LABEL_SET, asset.hash)
        if existing:
            logger.debug(f"LabelSet asset already exists: {existing.asset_id}")
            return existing.asset_id

        reg = get_asset_registry()
        reg.register(asset)
        return asset.asset_id
    except Exception as e:
        logger.warning(f"Failed to register LabelSet asset: {e}")
        return None


def register_model_asset(
    version,
    validation_passed: bool,
    validation_score: float = 0.0,
    validation_grade: str = "F",
) -> Optional[str]:
    """
    将 ModelVersion 注册为 MODEL_PACKAGE 资产

    Args:
        version: quantlab.ml.registry.ModelVersion 对象
        validation_passed: 是否通过验证
        validation_score: 验证分数
        validation_grade: 验证等级

    Returns:
        asset_id，失败返回 None
    """
    try:
        asset = ModelPackageAsset(
            name=version.name,
            family=version.family or version.name,
            version=version.version_number and f"{version.version_number}.0.0" or "1.0.0",
            model_package_id=version.version_id,
            algorithm=version.model_type.value if hasattr(version.model_type, "value") else str(version.model_type),
            model_type=version.model_type.value if hasattr(version.model_type, "value") else str(version.model_type),
            is_classifier=version.is_classifier,
            params=version.params,
            metrics=version.metrics or {},
            dataset_id=version.dataset_id,
            feature_set_id="",
            label_set_id="",
            validation_passed=validation_passed,
            validation_score=validation_score,
            validation_grade=validation_grade,
            description=version.description,
            tags=version.tags,
            status=AssetStatus.ACTIVE if validation_passed else AssetStatus.DRAFT,
        )

        existing = _find_by_hash(AssetType.MODEL_PACKAGE, asset.hash)
        if existing:
            logger.debug(f"Model asset already exists: {existing.asset_id}")
            return existing.asset_id

        reg = get_asset_registry()
        reg.register(asset)
        return asset.asset_id
    except Exception as e:
        logger.warning(f"Failed to register Model asset: {e}")
        return None


def register_strategy_asset(strategy, model_asset_id: str = "") -> Optional[str]:
    """
    将 Strategy 注册为 STRATEGY_PACKAGE 资产

    Args:
        strategy: 策略对象
        model_asset_id: 关联的 ModelPackage asset_id

    Returns:
        asset_id，失败返回 None
    """
    try:
        strategy_id = getattr(strategy, "strategy_id", "") or getattr(strategy, "name", "")
        name = getattr(strategy, "name", strategy_id)

        asset = StrategyPackageAsset(
            name=name,
            family=name,
            version="1.0.0",
            strategy_id=strategy_id,
            model_asset_id=model_asset_id,
            rules=getattr(strategy, "rules", {}) or {},
            description=getattr(strategy, "description", ""),
            tags=getattr(strategy, "tags", []),
            status=AssetStatus.ACTIVE,
        )

        existing = _find_by_hash(AssetType.STRATEGY_PACKAGE, asset.hash)
        if existing:
            logger.debug(f"Strategy asset already exists: {existing.asset_id}")
            return existing.asset_id

        reg = get_asset_registry()
        reg.register(asset)
        return asset.asset_id
    except Exception as e:
        logger.warning(f"Failed to register Strategy asset: {e}")
        return None


def add_model_lineage(
    model_asset_id: str,
    dataset_asset_id: str = "",
    feature_set_asset_id: str = "",
    label_set_asset_id: str = "",
) -> None:
    """
    建立 Model 的血缘关系

    Dataset → FeatureSet (DERIVED_FROM)
    Dataset → LabelSet (DERIVED_FROM)
    FeatureSet → Model (TRAINED_ON)
    LabelSet → Model (TRAINED_ON)
    Dataset → Model (TRAINED_ON)
    """
    try:
        reg = get_asset_registry()

        if dataset_asset_id and feature_set_asset_id:
            reg.add_lineage(
                dataset_asset_id, feature_set_asset_id,
                AssetRelation.DERIVED_FROM,
                "FeatureSet computed from Dataset",
            )
        if dataset_asset_id and label_set_asset_id:
            reg.add_lineage(
                dataset_asset_id, label_set_asset_id,
                AssetRelation.DERIVED_FROM,
                "LabelSet computed from Dataset",
            )
        if feature_set_asset_id and model_asset_id:
            reg.add_lineage(
                feature_set_asset_id, model_asset_id,
                AssetRelation.TRAINED_ON,
                "Model trained on FeatureSet",
            )
        if label_set_asset_id and model_asset_id:
            reg.add_lineage(
                label_set_asset_id, model_asset_id,
                AssetRelation.TRAINED_ON,
                "Model trained on LabelSet",
            )
        if dataset_asset_id and model_asset_id:
            reg.add_lineage(
                dataset_asset_id, model_asset_id,
                AssetRelation.TRAINED_ON,
                "Model trained on Dataset",
            )
    except Exception as e:
        logger.warning(f"Failed to add model lineage: {e}")


def add_strategy_lineage(
    strategy_asset_id: str,
    model_asset_id: str = "",
) -> None:
    """建立 Strategy → Model 的血缘"""
    try:
        if model_asset_id and strategy_asset_id:
            reg = get_asset_registry()
            reg.add_lineage(
                model_asset_id, strategy_asset_id,
                AssetRelation.PACKAGED_FROM,
                "Strategy packaged from Model",
            )
    except Exception as e:
        logger.warning(f"Failed to add strategy lineage: {e}")

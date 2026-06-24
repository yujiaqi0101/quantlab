"""
QuantLab Asset Registry — 量化资产注册中心

将 Model Registry 升级为统一的 Asset Registry，管理所有量化资产：
  Dataset / FeatureSet / LabelSet / ModelPackage / StrategyPackage / RiskProfile / DeploymentProfile

架构：
  Asset Base (QuantAsset)
  ────────────────────────────────
  AssetStorage        — 存储层（Registry/Storage 分离）
  VersionManager      — SemVer 语义化版本
  LineageManager      — DAG 血缘追溯
  ChampionManager     — 每 Family 一个 Champion
  AssetRegistry       — 统一入口
  ────────────────────────────────
  ModelAssetAdapter   — 现有 ModelPackage 适配
"""

from .base import (
    AssetType,
    AssetStatus,
    AssetRelation,
    QuantAsset,
    DatasetAsset,
    FeatureSetAsset,
    LabelSetAsset,
    ModelPackageAsset,
    StrategyPackageAsset,
    RiskProfileAsset,
    DeploymentProfileAsset,
)
from .storage import (
    AssetStorage,
    get_asset_storage,
    DEFAULT_STORAGE_ROOT,
)
from .version import (
    SemanticVersion,
    VersionManager,
    VersionBumpType,
)
from .lineage import (
    LineageManager,
    LineageNode,
    LineageEdge,
)
from .champion import (
    ChampionManager,
    ChampionPointer,
    ChampionHistoryEntry,
)
from .registry import (
    AssetRegistry,
    get_asset_registry,
)
from .adapter import (
    ModelAssetAdapter,
)

__all__ = [
    # 基类
    "AssetType",
    "AssetStatus",
    "AssetRelation",
    "QuantAsset",
    # 具体资产
    "DatasetAsset",
    "FeatureSetAsset",
    "LabelSetAsset",
    "ModelPackageAsset",
    "StrategyPackageAsset",
    "RiskProfileAsset",
    "DeploymentProfileAsset",
    # 存储层
    "AssetStorage",
    "get_asset_storage",
    "DEFAULT_STORAGE_ROOT",
    # 版本管理
    "SemanticVersion",
    "VersionManager",
    "VersionBumpType",
    # 血缘管理
    "LineageManager",
    "LineageNode",
    "LineageEdge",
    # 冠军管理
    "ChampionManager",
    "ChampionPointer",
    "ChampionHistoryEntry",
    # 统一入口
    "AssetRegistry",
    "get_asset_registry",
    # 适配器
    "ModelAssetAdapter",
]

"""
AssetRegistry — 资产注册中心统一入口

组合 VersionManager + LineageManager + ChampionManager + AssetStorage。

  AssetRegistry
  ├── register(asset)              注册资产
  ├── get(asset_id)                获取资产
  ├── list(asset_type)             列出资产
  ├── search(query)                搜索资产
  ├── get_champion(family)         获取 Champion
  ├── set_champion(family, id)     设置 Champion
  ├── get_lineage(asset_id)        获取血缘
  ├── add_lineage(parent, child)  添加血缘
  └── get_version_history(family)  获取版本历史

设计原则：
  1. Registry 是索引，不保存真正数据（数据在 Storage）
  2. MODEL_PACKAGE 类型强制检查 validation_passed
  3. 向后兼容现有 ModelRegistry API
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union

from .base import (
    AssetRelation,
    AssetStatus,
    AssetType,
    QuantAsset,
    ModelPackageAsset,
)
from .champion import ChampionManager, ChampionPointer
from .lineage import LineageManager, LineageNode
from .storage import AssetStorage, get_asset_storage
from .version import SemanticVersion, VersionManager

logger = logging.getLogger("quantlab.asset.registry")


class AssetRegistry:
    """
    资产注册中心

    用法：
        reg = get_asset_registry()
        reg.register(asset)
        asset = reg.get(asset_id)
        champions = reg.get_all_champions()
        lineage = reg.get_lineage(asset_id)
    """

    def __init__(self, storage: Optional[AssetStorage] = None) -> None:
        self.storage = storage or get_asset_storage()
        self.version_manager = VersionManager()
        self.lineage_manager = LineageManager()
        self.champion_manager = ChampionManager()
        # asset_id → QuantAsset（内存索引）
        self._assets: Dict[str, QuantAsset] = {}

    # ------------------------------------------------------------------
    # 注册 / 获取
    # ------------------------------------------------------------------

    def register(
        self,
        asset: QuantAsset,
        data: Any = None,
        data_format: str = "pkl",
    ) -> str:
        """
        注册资产

        对 MODEL_PACKAGE 类型强制检查 validation_passed。

        Args:
            asset: 资产对象
            data: 资产数据（可选）
            data_format: 数据格式

        Returns:
            asset_id
        """
        # Validation 门禁：MODEL_PACKAGE 必须通过验证
        if asset.asset_type == AssetType.MODEL_PACKAGE:
            if isinstance(asset, ModelPackageAsset):
                if not asset.validation_passed:
                    raise ValueError(
                        f"Cannot register MODEL_PACKAGE without validation: {asset.name}"
                    )

        # 注册版本
        version = SemanticVersion.try_parse(asset.version)
        if version:
            self.version_manager.register(asset.family, version)

        # 注册到血缘图
        self.lineage_manager.add_node(
            asset_id=asset.asset_id,
            name=asset.name,
            asset_type=asset.asset_type.value,
            version=asset.version,
        )

        # 保存到 Storage
        self.storage.save(asset, data=data, data_format=data_format)

        # 内存索引
        self._assets[asset.asset_id] = asset

        logger.info(
            f"Asset registered: {asset.asset_id} "
            f"({asset.asset_type.value}, {asset.name} v{asset.version})"
        )
        return asset.asset_id

    def get(self, asset_id: str) -> Optional[QuantAsset]:
        """获取资产"""
        return self._assets.get(asset_id)

    def get_manifest(self, asset_id: str) -> Optional[Dict[str, Any]]:
        """从 Storage 加载 manifest"""
        asset = self._assets.get(asset_id)
        if asset is None:
            return None
        return self.storage.load_manifest(asset_id, asset.asset_type)

    def list_assets(
        self,
        asset_type: Optional[AssetType] = None,
        family: Optional[str] = None,
        status: Optional[AssetStatus] = None,
    ) -> List[QuantAsset]:
        """列出资产（支持过滤）"""
        result = list(self._assets.values())
        if asset_type:
            result = [a for a in result if a.asset_type == asset_type]
        if family:
            result = [a for a in result if a.family == family]
        if status:
            result = [a for a in result if a.status == status]
        return result

    def search(self, query: str) -> List[QuantAsset]:
        """搜索资产（按 name / family / tags）"""
        query_lower = query.lower()
        result = []
        for asset in self._assets.values():
            if (
                query_lower in asset.name.lower()
                or query_lower in asset.family.lower()
                or any(query_lower in tag.lower() for tag in asset.tags)
            ):
                result.append(asset)
        return result

    def delete(self, asset_id: str) -> bool:
        """删除资产"""
        asset = self._assets.pop(asset_id, None)
        if asset is None:
            return False
        self.storage.delete(asset_id, asset.asset_type)
        logger.info(f"Asset deleted: {asset_id}")
        return True

    # ------------------------------------------------------------------
    # Champion 管理
    # ------------------------------------------------------------------

    def set_champion(
        self,
        family: str,
        asset_id: str,
        reason: str = "",
    ) -> ChampionPointer:
        """设置 Champion"""
        asset = self._assets.get(asset_id)
        if asset is None:
            raise ValueError(f"Asset not found: {asset_id}")
        return self.champion_manager.promote(
            family=family,
            asset_id=asset_id,
            reason=reason,
            asset=asset,
        )

    def get_champion(self, family: str) -> Optional[QuantAsset]:
        """获取 Champion 资产"""
        pointer = self.champion_manager.get_champion(family)
        if pointer is None:
            return None
        return self._assets.get(pointer.champion_asset_id)

    def get_champion_id(self, family: str) -> Optional[str]:
        """获取 Champion asset_id"""
        return self.champion_manager.get_champion_id(family)

    def get_all_champions(self) -> Dict[str, QuantAsset]:
        """获取所有 Champion"""
        pointers = self.champion_manager.get_all_champions()
        result = {}
        for family, pointer in pointers.items():
            asset = self._assets.get(pointer.champion_asset_id)
            if asset:
                result[family] = asset
        return result

    def list_champion_families(self) -> List[str]:
        """列出所有有 Champion 的 Family"""
        return self.champion_manager.list_families()

    # ------------------------------------------------------------------
    # Lineage 管理
    # ------------------------------------------------------------------

    def add_lineage(
        self,
        parent_asset_id: str,
        child_asset_id: str,
        relation: AssetRelation = AssetRelation.DERIVED_FROM,
        note: str = "",
    ) -> bool:
        """添加血缘关系"""
        return self.lineage_manager.add_edge(
            from_asset_id=parent_asset_id,
            to_asset_id=child_asset_id,
            relation=relation,
            note=note,
        )

    def get_lineage(self, asset_id: str) -> Dict[str, Any]:
        """获取资产血缘树"""
        return self.lineage_manager.get_lineage_tree(asset_id)

    def get_ancestors(self, asset_id: str) -> List[LineageNode]:
        """获取祖先"""
        return self.lineage_manager.get_ancestor_nodes(asset_id)

    def get_descendants(self, asset_id: str) -> List[LineageNode]:
        """获取后代"""
        return self.lineage_manager.get_descendant_nodes(asset_id)

    def get_dependency_chain(self, asset_id: str) -> List[Dict[str, Any]]:
        """获取依赖链"""
        return self.lineage_manager.get_dependency_chain(asset_id)

    # ------------------------------------------------------------------
    # Version 管理
    # ------------------------------------------------------------------

    def get_version_history(self, family: str) -> List[Dict[str, Any]]:
        """获取版本历史"""
        return self.version_manager.get_version_history(family)

    def get_latest_version(self, family: str) -> Optional[SemanticVersion]:
        """获取最新版本"""
        return self.version_manager.get_latest(family)

    def list_families(self) -> List[str]:
        """列出所有 Family"""
        return self.version_manager.list_families()

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_assets": len(self._assets),
            "families": self.list_families(),
            "n_champions": len(self.champion_manager.get_all_champions()),
            "champion_families": self.champion_manager.list_families(),
            "assets": [a.to_index() for a in self._assets.values()],
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取摘要"""
        type_counts: Dict[str, int] = {}
        for asset in self._assets.values():
            t = asset.asset_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_assets": len(self._assets),
            "by_type": type_counts,
            "n_families": len(self.list_families()),
            "n_champions": len(self.champion_manager.get_all_champions()),
            "n_lineage_edges": sum(
                len(edges) for edges in self.lineage_manager._children.values()
            ),
        }


# 单例
_asset_registry: Optional[AssetRegistry] = None


def get_asset_registry() -> AssetRegistry:
    global _asset_registry
    if _asset_registry is None:
        _asset_registry = AssetRegistry()
    return _asset_registry

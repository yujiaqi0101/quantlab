"""
Model Lineage — 模型血统图

ML Lab M4 第四部分：记录模型是如何产生的

  例如：
    LGBM_v1
      ↓ 修改 FeatureSet
    LGBM_v2
      ↓ 增加 ATR
    LGBM_v3

  形成 Model Lineage Graph

  以后：为什么 v3 更好？能看出来。

  功能：
    - get_lineage(version_id)        获取血统链
    - get_family_tree(family)        获取族谱树
    - compare_lineage(v1_id, v2_id)  对比两个版本的变更
    - get_change_log(version_id)     获取变更日志
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from .registry import ModelVersion, ModelRegistry

logger = logging.getLogger("quantlab.ml.registry.lineage")


@dataclass
class LineageNode:
    """血统图节点"""
    version_id: str = ""
    name: str = ""
    family: str = ""
    version_number: int = 0
    lifecycle: str = ""
    parent_version_id: str = ""
    lineage_note: str = ""
    created_at: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version_id": self.version_id,
            "name": self.name,
            "family": self.family,
            "version_number": self.version_number,
            "lifecycle": self.lifecycle,
            "parent_version_id": self.parent_version_id,
            "lineage_note": self.lineage_note,
            "created_at": self.created_at,
            "metrics": self.metrics,
        }


@dataclass
class LineageChange:
    """版本间变更"""
    from_version: str = ""
    to_version: str = ""
    changes: Dict[str, str] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_version": self.from_version,
            "to_version": self.to_version,
            "changes": self.changes,
            "note": self.note,
        }


class ModelLineage:
    """
    模型血统图管理器

    用法：
        lineage = ModelLineage(registry)
        chain = lineage.get_lineage("MV-xxx")        # [v1, v2, v3]
        tree = lineage.get_family_tree("LGBM_Mom")   # 族谱
        changes = lineage.compare_versions("v1", "v2")
    """

    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def get_lineage(self, version_id: str) -> List[LineageNode]:
        """
        获取血统链（从最早祖先到当前版本）

        返回：[v1_node, v2_node, v3_node, current_node]
        """
        chain = self.registry.get_lineage(version_id)
        return [self._version_to_node(v) for v in chain]

    def get_family_tree(self, family: str) -> List[LineageNode]:
        """
        获取族谱树（按版本号排序）

        返回：[v1_node, v2_node, v3_node, ...]
        """
        versions = self.registry.get_family(family)
        return [self._version_to_node(v) for v in versions]

    def get_children(self, version_id: str) -> List[LineageNode]:
        """获取直接子版本"""
        children = self.registry.get_children(version_id)
        return [self._version_to_node(v) for v in children]

    def get_root(self, version_id: str) -> Optional[LineageNode]:
        """获取血统链的根（最早祖先）"""
        chain = self.get_lineage(version_id)
        if not chain:
            return None
        return chain[0]

    def compare_versions(
        self,
        from_version_id: str,
        to_version_id: str,
    ) -> LineageChange:
        """
        对比两个版本的变更

        检测：
          - params 变化
          - feature_ids 变化
          - dataset_id 变化
          - label_id 变化
          - metrics 变化
        """
        v1 = self.registry.get_version(from_version_id)
        v2 = self.registry.get_version(to_version_id)
        if v1 is None or v2 is None:
            return LineageChange()

        changes: Dict[str, str] = {}

        # params 变化
        if v1.params != v2.params:
            changes["params"] = f"{v1.params} → {v2.params}"

        # feature_ids 变化
        added_features = set(v2.feature_ids) - set(v1.feature_ids)
        removed_features = set(v1.feature_ids) - set(v2.feature_ids)
        if added_features or removed_features:
            parts = []
            if added_features:
                parts.append(f"+{sorted(added_features)}")
            if removed_features:
                parts.append(f"-{sorted(removed_features)}")
            changes["feature_ids"] = " ".join(parts)

        # dataset 变化
        if v1.dataset_id != v2.dataset_id:
            changes["dataset_id"] = f"{v1.dataset_id} → {v2.dataset_id}"

        # label 变化
        if v1.label_id != v2.label_id:
            changes["label_id"] = f"{v1.label_id} → {v2.label_id}"

        # metrics 变化
        for metric in ["ic", "sharpe", "rmse"]:
            old_val = v1.metrics.get(metric, 0)
            new_val = v2.metrics.get(metric, 0)
            if abs(old_val - new_val) > 1e-6:
                changes[f"metric_{metric}"] = f"{old_val:.4f} → {new_val:.4f}"

        return LineageChange(
            from_version=v1.name,
            to_version=v2.name,
            changes=changes,
            note=v2.lineage_note,
        )

    def get_change_log(self, version_id: str) -> List[LineageChange]:
        """
        获取从根到当前版本的所有变更日志

        返回：[v1→v2 change, v2→v3 change, ...]
        """
        chain = self.registry.get_lineage(version_id)
        if len(chain) < 2:
            return []

        changes: List[LineageChange] = []
        for i in range(1, len(chain)):
            change = self.compare_versions(chain[i-1].version_id, chain[i].version_id)
            changes.append(change)
        return changes

    def get_metrics_evolution(self, family: str, metric: str = "ic") -> pd.DataFrame:
        """
        获取指标随版本演进

        返回 DataFrame:
            version_number | name | ic | sharpe | ...
        """
        versions = self.registry.get_family(family)
        data = []
        for v in versions:
            data.append({
                "version_number": v.version_number,
                "name": v.name,
                "lifecycle": v.lifecycle.value,
                metric: v.metrics.get(metric, 0),
                "sharpe": v.metrics.get("sharpe", 0),
                "ic": v.metrics.get("ic", 0),
                "rmse": v.metrics.get("rmse", 0),
            })
        return pd.DataFrame(data)

    def to_dict(self) -> Dict[str, Any]:
        families = self.registry.list_families()
        trees = {f: [n.to_dict() for n in self.get_family_tree(f)] for f in families}
        return {
            "families": families,
            "trees": trees,
        }

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _version_to_node(v: ModelVersion) -> LineageNode:
        return LineageNode(
            version_id=v.version_id,
            name=v.name,
            family=v.family,
            version_number=v.version_number,
            lifecycle=v.lifecycle.value,
            parent_version_id=v.parent_version_id,
            lineage_note=v.lineage_note,
            created_at=v.created_at,
            metrics=v.metrics,
        )

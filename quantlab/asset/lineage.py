"""
LineageManager — 资产血缘 DAG 管理

跨资产类型追溯：
  Dataset → FeatureSet → LabelSet → TrainingRun → ValidationRun → ModelPackage → StrategyPackage

形成 DAG（有向无环图），任何资产都可以追溯来源。

功能：
  - add_edge(parent, child, relation)   添加血缘边
  - get_ancestors(asset_id)             获取所有祖先
  - get_descendants(asset_id)           获取所有后代
  - get_path(from, to)                  获取路径
  - detect_cycle()                      环检测
  - get_lineage_tree(asset_id)          获取完整血缘树
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .base import AssetRelation

logger = logging.getLogger("quantlab.asset.lineage")


@dataclass
class LineageNode:
    """血缘图节点"""
    asset_id: str = ""
    name: str = ""
    asset_type: str = ""
    version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "version": self.version,
        }


@dataclass
class LineageEdge:
    """血缘图边"""
    from_asset_id: str = ""
    to_asset_id: str = ""
    relation: AssetRelation = AssetRelation.DERIVED_FROM
    note: str = ""
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_asset_id": self.from_asset_id,
            "to_asset_id": self.to_asset_id,
            "relation": self.relation.value,
            "note": self.note,
            "created_at": self.created_at,
        }


class LineageManager:
    """
    血缘管理器（DAG）

    用法：
        mgr = LineageManager()
        mgr.add_node("ASSET-001", "Crypto_1H", "DATASET", "1.0.0")
        mgr.add_node("ASSET-002", "Momentum_v1", "FEATURE_SET", "1.0.0")
        mgr.add_edge("ASSET-001", "ASSET-002", AssetRelation.DERIVED_FROM)

        ancestors = mgr.get_ancestors("ASSET-002")  # [ASSET-001]
        descendants = mgr.get_descendants("ASSET-001")  # [ASSET-002]
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, LineageNode] = {}
        # 邻接表：parent → [child edges]
        self._children: Dict[str, List[LineageEdge]] = defaultdict(list)
        # 逆邻接表：child → [parent edges]
        self._parents: Dict[str, List[LineageEdge]] = defaultdict(list)

    # ------------------------------------------------------------------
    # 节点管理
    # ------------------------------------------------------------------

    def add_node(
        self,
        asset_id: str,
        name: str = "",
        asset_type: str = "",
        version: str = "",
    ) -> LineageNode:
        """添加节点"""
        if asset_id not in self._nodes:
            node = LineageNode(
                asset_id=asset_id,
                name=name,
                asset_type=asset_type,
                version=version,
            )
            self._nodes[asset_id] = node
            logger.debug(f"Lineage node added: {asset_id} ({name})")
        else:
            # 更新信息
            node = self._nodes[asset_id]
            if name:
                node.name = name
            if asset_type:
                node.asset_type = asset_type
            if version:
                node.version = version
        return self._nodes[asset_id]

    def get_node(self, asset_id: str) -> Optional[LineageNode]:
        """获取节点"""
        return self._nodes.get(asset_id)

    def list_nodes(self) -> List[LineageNode]:
        """列出所有节点"""
        return list(self._nodes.values())

    # ------------------------------------------------------------------
    # 边管理
    # ------------------------------------------------------------------

    def add_edge(
        self,
        from_asset_id: str,
        to_asset_id: str,
        relation: AssetRelation = AssetRelation.DERIVED_FROM,
        note: str = "",
        created_at: str = "",
    ) -> bool:
        """
        添加血缘边

        Args:
            from_asset_id: 父资产 ID
            to_asset_id: 子资产 ID
            relation: 关系类型
            note: 变更说明
            created_at: 创建时间

        Returns:
            True 如果添加成功，False 如果会形成环
        """
        import pandas as pd

        # 确保节点存在
        if from_asset_id not in self._nodes:
            self.add_node(from_asset_id)
        if to_asset_id not in self._nodes:
            self.add_node(to_asset_id)

        # 环检测：如果 to → from 已有路径，则不能添加 from → to
        if self._has_path(to_asset_id, from_asset_id):
            logger.warning(
                f"Cycle detected: cannot add edge {from_asset_id} → {to_asset_id}"
            )
            return False

        if not created_at:
            created_at = pd.Timestamp.now().isoformat()

        edge = LineageEdge(
            from_asset_id=from_asset_id,
            to_asset_id=to_asset_id,
            relation=relation,
            note=note,
            created_at=created_at,
        )

        self._children[from_asset_id].append(edge)
        self._parents[to_asset_id].append(edge)

        logger.info(
            f"Lineage edge added: {from_asset_id} --{relation.value}--> {to_asset_id}"
        )
        return True

    def remove_edge(self, from_asset_id: str, to_asset_id: str) -> bool:
        """删除边"""
        before_len = len(self._children.get(from_asset_id, []))
        self._children[from_asset_id] = [
            e for e in self._children.get(from_asset_id, [])
            if e.to_asset_id != to_asset_id
        ]
        self._parents[to_asset_id] = [
            e for e in self._parents.get(to_asset_id, [])
            if e.from_asset_id != from_asset_id
        ]
        return len(self._children[from_asset_id]) < before_len

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_parents(self, asset_id: str) -> List[LineageEdge]:
        """获取直接父节点"""
        return list(self._parents.get(asset_id, []))

    def get_children(self, asset_id: str) -> List[LineageEdge]:
        """获取直接子节点"""
        return list(self._children.get(asset_id, []))

    def get_ancestors(self, asset_id: str) -> List[str]:
        """
        获取所有祖先（BFS）

        返回从近到远的祖先列表。
        """
        ancestors: List[str] = []
        visited: Set[str] = set()
        queue = deque([asset_id])

        while queue:
            current = queue.popleft()
            for edge in self._parents.get(current, []):
                parent_id = edge.from_asset_id
                if parent_id not in visited:
                    visited.add(parent_id)
                    ancestors.append(parent_id)
                    queue.append(parent_id)

        return ancestors

    def get_descendants(self, asset_id: str) -> List[str]:
        """
        获取所有后代（BFS）

        返回从近到远的后代列表。
        """
        descendants: List[str] = []
        visited: Set[str] = set()
        queue = deque([asset_id])

        while queue:
            current = queue.popleft()
            for edge in self._children.get(current, []):
                child_id = edge.to_asset_id
                if child_id not in visited:
                    visited.add(child_id)
                    descendants.append(child_id)
                    queue.append(child_id)

        return descendants

    def get_ancestor_nodes(self, asset_id: str) -> List[LineageNode]:
        """获取所有祖先节点（带信息）"""
        ancestors = self.get_ancestors(asset_id)
        return [self._nodes[aid] for aid in ancestors if aid in self._nodes]

    def get_descendant_nodes(self, asset_id: str) -> List[LineageNode]:
        """获取所有后代节点（带信息）"""
        descendants = self.get_descendants(asset_id)
        return [self._nodes[aid] for aid in descendants if aid in self._nodes]

    def _has_path(self, from_id: str, to_id: str) -> bool:
        """检查是否存在 from → to 的路径（BFS）"""
        if from_id == to_id:
            return True
        visited: Set[str] = set()
        queue = deque([from_id])

        while queue:
            current = queue.popleft()
            if current == to_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            for edge in self._children.get(current, []):
                if edge.to_asset_id not in visited:
                    queue.append(edge.to_asset_id)

        return False

    def get_path(self, from_asset_id: str, to_asset_id: str) -> Optional[List[str]]:
        """
        获取从 from 到 to 的路径（BFS）

        Returns:
            路径节点列表，如果不存在路径则返回 None
        """
        if from_asset_id == to_asset_id:
            return [from_asset_id]

        visited: Set[str] = {from_asset_id}
        # parent 映射，用于重建路径
        parent_map: Dict[str, Optional[str]] = {from_asset_id: None}
        queue = deque([from_asset_id])

        while queue:
            current = queue.popleft()
            for edge in self._children.get(current, []):
                child_id = edge.to_asset_id
                if child_id in visited:
                    continue
                visited.add(child_id)
                parent_map[child_id] = current
                if child_id == to_asset_id:
                    # 重建路径
                    path = []
                    node = child_id
                    while node is not None:
                        path.append(node)
                        node = parent_map.get(node)
                    path.reverse()
                    return path
                queue.append(child_id)

        return None

    # ------------------------------------------------------------------
    # 完整血缘树
    # ------------------------------------------------------------------

    def get_lineage_tree(self, asset_id: str) -> Dict[str, Any]:
        """
        获取完整血缘树（向上追溯所有祖先）

        返回嵌套结构：
        {
            "asset_id": "ASSET-003",
            "name": "Model_v1",
            "parents": [
                {
                    "asset_id": "ASSET-002",
                    "name": "FeatureSet_v1",
                    "relation": "TRAINED_ON",
                    "parents": [...]
                }
            ]
        }
        """
        node = self._nodes.get(asset_id)
        if node is None:
            return {"asset_id": asset_id, "name": "", "parents": []}

        tree: Dict[str, Any] = node.to_dict()
        tree["parents"] = []

        for edge in self._parents.get(asset_id, []):
            parent_tree = self.get_lineage_tree(edge.from_asset_id)
            parent_tree["relation"] = edge.relation.value
            parent_tree["note"] = edge.note
            tree["parents"].append(parent_tree)

        return tree

    def get_dependency_chain(self, asset_id: str) -> List[Dict[str, Any]]:
        """
        获取依赖链（扁平化）

        从根到当前资产的路径列表。
        """
        ancestors = self.get_ancestors(asset_id)
        chain = []
        for aid in reversed(ancestors):  # 从远到近
            node = self._nodes.get(aid)
            if node:
                chain.append(node.to_dict())
        # 加上自己
        node = self._nodes.get(asset_id)
        if node:
            chain.append(node.to_dict())
        return chain

    # ------------------------------------------------------------------
    # 汇总
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_nodes": len(self._nodes),
            "n_edges": sum(len(edges) for edges in self._children.values()),
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [
                e.to_dict()
                for edges in self._children.values()
                for e in edges
            ],
        }

    def detect_cycles(self) -> List[List[str]]:
        """
        检测所有环（理论上 add_edge 已防止环，此方法用于验证）

        Returns:
            环列表，每个环是 asset_id 列表
        """
        cycles: List[List[str]] = []
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for edge in self._children.get(node, []):
                child = edge.to_asset_id
                if child not in visited:
                    dfs(child)
                elif child in rec_stack:
                    # 找到环
                    cycle_start = path.index(child)
                    cycles.append(path[cycle_start:] + [child])

            path.pop()
            rec_stack.discard(node)

        for node_id in self._nodes:
            if node_id not in visited:
                dfs(node_id)

        return cycles

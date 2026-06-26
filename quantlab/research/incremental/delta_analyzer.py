"""
DeltaAnalyzer — 分析 ChangeSet 影响范围，生成 DirtyGraph

输入: ChangeSet + ResearchGraph
输出: 被标记为 dirty 的节点集合 (需要重新计算)

策略:
  1. 直接命中的 DATA 节点 (close/high/...)
  2. 沿 DAG 边传播到所有下游
"""
from __future__ import annotations

from typing import Dict, List, Set

from ..graph import ResearchGraph
from .changeset import ChangeSet


class DeltaAnalyzer:
    """分析 ChangeSet 影响范围。"""

    def __init__(self, graph: ResearchGraph) -> None:
        self._graph = graph

    def analyze(self, changeset: ChangeSet) -> "DirtyGraph":
        """分析变更影响，返回 DirtyGraph。"""
        # 1. 找到直接受影响的 DATA 节点
        dirty_nodes: Set[str] = set()
        affected_fields = set()
        for change in changeset.changes:
            for field in change.fields:
                affected_fields.add(field)
        # DATA 节点 id 通常与字段名一致 (close/high/low/open/volume/vwap)
        data_nodes = self._find_data_nodes_by_field(affected_fields)
        dirty_nodes.update(data_nodes)
        # 2. 沿 DAG 传播到下游
        downstream = self._propagate_downstream(dirty_nodes)
        dirty_nodes.update(downstream)
        return DirtyGraph(
            dirty_nodes=dirty_nodes,
            affected_fields=affected_fields,
            changeset=changeset,
        )

    def _find_data_nodes_by_field(self, fields: Set[str]) -> Set[str]:
        """根据字段名找到对应的 DATA 节点。"""
        result: Set[str] = set()
        for node_id in self._graph.node_ids():
            node = self._graph.get_node(node_id)
            if node is None:
                continue
            # DATA 节点的 id 通常是 close/high/low/open/volume/vwap
            if node.category.value == "data" and node_id in fields:
                result.add(node_id)
        return result

    def _propagate_downstream(self, start_nodes: Set[str]) -> Set[str]:
        """BFS 沿 DAG 边传播到所有下游节点。"""
        result: Set[str] = set()
        queue = list(start_nodes)
        while queue:
            current = queue.pop(0)
            for downstream_id in self._graph.downstream(current):
                if downstream_id not in result and downstream_id not in start_nodes:
                    result.add(downstream_id)
                    queue.append(downstream_id)
        return result


class DirtyGraph:
    """脏图: 被标记为需要重新计算的节点集合。"""

    def __init__(
        self,
        dirty_nodes: Set[str],
        affected_fields: Set[str],
        changeset: ChangeSet,
    ) -> None:
        self.dirty_nodes = dirty_nodes
        self.affected_fields = affected_fields
        self.changeset = changeset

    def is_dirty(self, node_id: str) -> bool:
        return node_id in self.dirty_nodes

    def dirty_count(self) -> int:
        return len(self.dirty_nodes)

    def __repr__(self) -> str:
        return f"DirtyGraph({self.dirty_count()} dirty: {sorted(self.dirty_nodes)})"


__all__ = ["DeltaAnalyzer", "DirtyGraph"]

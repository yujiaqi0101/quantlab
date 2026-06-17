"""
Dataset Lineage — 数据血缘追踪

记录数据从 Raw → Cleaned → Resampled → Feature 的完整血缘链。

例如：
  Raw Binance (btcusdt_raw_1m)
    ↓ cleaned
  Cleaned Binance (btcusdt_clean_1m)
    ↓ resampled
  Resampled 5m (btcusdt_5m)
    ↓ feature
  Feature Dataset (btcusdt_features)

以后：任何实验都能追溯使用了什么数据。

用法：
    lineage = DatasetLineage()
    lineage.add_node("btcusdt_raw_1m", name="Raw Binance", source="binance")
    lineage.add_edge("btcusdt_raw_1m", "btcusdt_clean_1m", op="clean")
    lineage.trace("btcusdt_features")
    → ["btcusdt_raw_1m", "btcusdt_clean_1m", "btcusdt_5m", "btcusdt_features"]
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("quantlab.dataset.lineage")


# ------------------------------------------------------------------
# Lineage Node & Edge
# ------------------------------------------------------------------

@dataclass(slots=True)
class LineageNode:
    """血缘节点（一个数据集）"""
    dataset_id: str
    name: str = ""
    node_type: str = "raw"        # raw / cleaned / resampled / feature / snapshot
    source: str = ""              # binance / tushare / csv
    version: str = "1.0.0"
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LineageEdge:
    """血缘边（数据变换）"""
    source_id: str       # 上游数据集
    target_id: str       # 下游数据集
    operation: str = ""  # clean / resample / merge / feature_compute / snapshot
    params: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------
# DatasetLineage
# ------------------------------------------------------------------

class DatasetLineage:
    """
    数据血缘图

    维护节点（数据集）和边（变换操作），
    支持正向追踪（下游）和反向追溯（上游）。
    """

    def __init__(self, store_dir: str = "storage/lineage") -> None:
        self.store_dir = store_dir
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []
        os.makedirs(store_dir, exist_ok=True)
        self._load()

    # ---- 节点管理 ----

    def add_node(
        self,
        dataset_id: str,
        name: str = "",
        node_type: str = "raw",
        source: str = "",
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        """添加血缘节点"""
        import datetime
        node = LineageNode(
            dataset_id=dataset_id,
            name=name or dataset_id,
            node_type=node_type,
            source=source,
            version=version,
            created_at=datetime.datetime.now().isoformat(timespec="seconds"),
            metadata=metadata or {},
        )
        self._nodes[dataset_id] = node
        self._save()
        logger.info(f"lineage node added: {dataset_id} ({node_type})")
        return node

    def get_node(self, dataset_id: str) -> Optional[LineageNode]:
        return self._nodes.get(dataset_id)

    def list_nodes(self, node_type: Optional[str] = None) -> List[LineageNode]:
        if node_type:
            return [n for n in self._nodes.values() if n.node_type == node_type]
        return list(self._nodes.values())

    # ---- 边管理 ----

    def add_edge(
        self,
        source_id: str,
        target_id: str,
        operation: str = "",
        params: Optional[Dict[str, Any]] = None,
    ) -> LineageEdge:
        """添加血缘边（数据变换）"""
        import datetime
        if source_id not in self._nodes:
            self.add_node(source_id)
        if target_id not in self._nodes:
            self.add_node(target_id)

        edge = LineageEdge(
            source_id=source_id,
            target_id=target_id,
            operation=operation,
            params=params or {},
            created_at=datetime.datetime.now().isoformat(timespec="seconds"),
        )
        self._edges.append(edge)
        self._save()
        logger.info(f"lineage edge: {source_id} --[{operation}]--> {target_id}")
        return edge

    def list_edges(self) -> List[LineageEdge]:
        return list(self._edges)

    # ---- 追踪 ----

    def trace_upstream(self, dataset_id: str) -> List[str]:
        """
        反向追溯：这个数据集是怎么来的？

        返回从根节点到当前数据集的路径列表
        """
        visited: Set[str] = set()
        path: List[str] = []

        def _dfs(node_id: str) -> None:
            if node_id in visited:
                return
            visited.add(node_id)
            # 找上游
            for edge in self._edges:
                if edge.target_id == node_id:
                    _dfs(edge.source_id)
            path.append(node_id)

        _dfs(dataset_id)
        return path

    def trace_downstream(self, dataset_id: str) -> List[str]:
        """
        正向追踪：这个数据集被谁用了？

        返回所有下游数据集
        """
        visited: Set[str] = set()
        result: List[str] = []

        def _bfs(start: str) -> None:
            queue = [start]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                if current != dataset_id:
                    result.append(current)
                for edge in self._edges:
                    if edge.source_id == current and edge.target_id not in visited:
                        queue.append(edge.target_id)

        _bfs(dataset_id)
        return result

    def get_chain(self, dataset_id: str) -> List[Dict[str, Any]]:
        """
        获取完整血缘链（带操作信息）

        返回：
          [
            {"dataset_id": "raw", "operation": null},
            {"dataset_id": "cleaned", "operation": "clean"},
            {"dataset_id": "resampled", "operation": "resample"},
          ]
        """
        upstream = self.trace_upstream(dataset_id)
        chain = []
        for i, ds_id in enumerate(upstream):
            op = ""
            if i > 0:
                # 找到上游到当前的边
                for edge in self._edges:
                    if edge.target_id == ds_id and edge.source_id == upstream[i - 1]:
                        op = edge.operation
                        break
            node = self._nodes.get(ds_id)
            chain.append({
                "dataset_id": ds_id,
                "name": node.name if node else ds_id,
                "node_type": node.node_type if node else "",
                "operation": op,
                "version": node.version if node else "",
            })
        return chain

    # ---- 可视化数据 ----

    def to_graph(self) -> Dict[str, Any]:
        """导出为图数据（前端可视化用）"""
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges],
        }

    # ---- 持久化 ----

    def _meta_path(self) -> str:
        return os.path.join(self.store_dir, "lineage.json")

    def _save(self) -> None:
        data = {
            "nodes": {k: asdict(v) for k, v in self._nodes.items()},
            "edges": [asdict(e) for e in self._edges],
        }
        try:
            with open(self._meta_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"lineage save fail: {e}")

    def _load(self) -> None:
        path = self._meta_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, d in data.get("nodes", {}).items():
                self._nodes[k] = LineageNode(**d)
            for d in data.get("edges", []):
                self._edges.append(LineageEdge(**d))
        except Exception as e:
            logger.warning(f"lineage load fail: {e}")


# ---- 全局单例 ----

_lineage: Optional[DatasetLineage] = None


def get_lineage() -> DatasetLineage:
    global _lineage
    if _lineage is None:
        _lineage = DatasetLineage()
    return _lineage

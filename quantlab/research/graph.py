"""
ResearchGraph — 研究图 (DAG)

节点 + 边 + 编译产物。

  Edge          : source_node_id:output_port -> target_node_id:input_port
  ResearchGraph : add_node/add_edge/compile/to_dag_view/fingerprint
  CompiledGraph : 拓扑序 + 执行计划 + 缓存计划 + 指纹
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .node.base import ResearchNode
from .node.manifest import NodeCategory
from .node.ports import Port, PortType


# ---------------------------------------------------------------------- #
# Edge
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class Edge:
    """图边：source_node:output_port -> target_node:input_port。"""

    source_node: str
    source_port: str
    target_node: str
    target_port: str

    def __repr__(self) -> str:
        return f"{self.source_node}:{self.source_port} -> {self.target_node}:{self.target_port}"


# ---------------------------------------------------------------------- #
# DAG View (调试/可视化)
# ---------------------------------------------------------------------- #
@dataclass
class DAGView:
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    layers: List[List[str]] = field(default_factory=list)  # 按拓扑分层


# ---------------------------------------------------------------------- #
# CompiledGraph
# ---------------------------------------------------------------------- #
@dataclass
class CompiledGraph:
    """编译产物：拓扑序 + 执行计划 (同层并行) + 指纹。"""

    topo_order: List[str]                         # 拓扑序
    execution_plan: List[List[str]]              # 同层可并行分组
    fingerprint: str = ""
    node_count: int = 0
    edge_count: int = 0


# ---------------------------------------------------------------------- #
# GraphError
# ---------------------------------------------------------------------- #
class GraphError(Exception):
    """图构建/编译错误。"""


# ---------------------------------------------------------------------- #
# ResearchGraph
# ---------------------------------------------------------------------- #
class ResearchGraph:
    """研究图：节点 + 边 + 编译。"""

    def __init__(self, name: str = "") -> None:
        self.name = name
        self._nodes: Dict[str, ResearchNode] = {}
        self._edges: List[Edge] = []
        self._adj_in: Dict[str, List[Edge]] = defaultdict(list)   # 节点的入边
        self._adj_out: Dict[str, List[Edge]] = defaultdict(list)  # 节点的出边

    # ---- 节点 ----
    def add_node(self, node: ResearchNode) -> "ResearchGraph":
        if node.id in self._nodes:
            raise GraphError(f"duplicate node id: {node.id}")
        self._nodes[node.id] = node
        self._adj_in.setdefault(node.id, [])
        self._adj_out.setdefault(node.id, [])
        return self

    def get_node(self, node_id: str) -> Optional[ResearchNode]:
        return self._nodes.get(node_id)

    def nodes(self) -> List[ResearchNode]:
        return list(self._nodes.values())

    def node_ids(self) -> List[str]:
        return list(self._nodes.keys())

    # ---- 边 ----
    def add_edge(
        self,
        source_node: str,
        source_port: str,
        target_node: str,
        target_port: str,
    ) -> "ResearchGraph":
        if source_node not in self._nodes:
            raise GraphError(f"source node not found: {source_node}")
        if target_node not in self._nodes:
            raise GraphError(f"target node not found: {target_node}")
        edge = Edge(source_node, source_port, target_node, target_port)
        self._edges.append(edge)
        self._adj_out[source_node].append(edge)
        self._adj_in[target_node].append(edge)
        return self

    def edges(self) -> List[Edge]:
        return list(self._edges)

    def remove_node(self, node_id: str) -> None:
        if node_id not in self._nodes:
            raise GraphError(f"node not found: {node_id}")
        del self._nodes[node_id]
        self._edges = [
            e for e in self._edges
            if e.source_node != node_id and e.target_node != node_id
        ]
        self._adj_in.pop(node_id, None)
        self._adj_out.pop(node_id, None)
        for nid in list(self._adj_in.keys()):
            self._adj_in[nid] = [e for e in self._adj_in[nid] if e.source_node != node_id]
        for nid in list(self._adj_out.keys()):
            self._adj_out[nid] = [e for e in self._adj_out[nid] if e.target_node != node_id]

    def remove_edge(
        self,
        source_node: str,
        source_port: str,
        target_node: str,
        target_port: str,
    ) -> None:
        before = len(self._edges)
        self._edges = [
            e for e in self._edges
            if not (
                e.source_node == source_node
                and e.source_port == source_port
                and e.target_node == target_node
                and e.target_port == target_port
            )
        ]
        removed = before - len(self._edges)
        if removed == 0:
            raise GraphError(
                f"edge not found: {source_node}:{source_port} -> {target_node}:{target_port}"
            )
        self._adj_out[source_node] = [
            e for e in self._adj_out.get(source_node, [])
            if not (
                e.source_port == source_port
                and e.target_node == target_node
                and e.target_port == target_port
            )
        ]
        self._adj_in[target_node] = [
            e for e in self._adj_in.get(target_node, [])
            if not (
                e.source_node == source_node
                and e.source_port == source_port
                and e.target_port == target_port
            )
        ]

    def downstream(self, node_id: str) -> List[str]:
        """直接下游节点 id 列表。"""
        return [e.target_node for e in self._adj_out.get(node_id, [])]

    def upstream(self, node_id: str) -> List[str]:
        """直接上游节点 id 列表。"""
        return [e.source_node for e in self._adj_in.get(node_id, [])]

    def all_downstream(self, node_id: str) -> List[str]:
        """所有下游节点 (含间接)。"""
        result = []
        visited = {node_id}
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            for d in self.downstream(current):
                if d not in visited:
                    visited.add(d)
                    result.append(d)
                    queue.append(d)
        return result

    # ---- 编译 ----
    def compile(self) -> CompiledGraph:
        """编译图：1) 无环校验 2) 端口类型匹配 3) 拓扑排序 4) 同层并行分组。"""
        self._check_no_cycle()
        self._check_port_types()
        topo = self._topo_sort()
        plan = self._build_parallel_plan(topo)
        fp = self.fingerprint()
        return CompiledGraph(
            topo_order=topo,
            execution_plan=plan,
            fingerprint=fp,
            node_count=len(self._nodes),
            edge_count=len(self._edges),
        )

    def _check_no_cycle(self) -> None:
        """Kahn 算法环检测。"""
        in_deg: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_deg[edge.target_node] += 1
        queue = deque([nid for nid, d in in_deg.items() if d == 0])
        visited = 0
        adj: Dict[str, List[str]] = defaultdict(list)
        for edge in self._edges:
            adj[edge.source_node].append(edge.target_node)
        while queue:
            n = queue.popleft()
            visited += 1
            for m in adj[n]:
                in_deg[m] -= 1
                if in_deg[m] == 0:
                    queue.append(m)
        if visited != len(self._nodes):
            raise GraphError("cycle detected in graph")

    def _check_port_types(self) -> None:
        """端口类型匹配校验。"""
        for edge in self._edges:
            src_node = self._nodes[edge.source_node]
            tgt_node = self._nodes[edge.target_node]
            src_port = self._find_port(src_node.outputs, edge.source_port, "output", src_node.id)
            tgt_port = self._find_port(tgt_node.inputs, edge.target_port, "input", tgt_node.id)
            if src_port.type != tgt_port.type:
                raise GraphError(
                    f"port type mismatch on edge {edge}: "
                    f"{src_port.type.value} != {tgt_port.type.value}"
                )

    @staticmethod
    def _find_port(ports: List[Port], name: str, kind: str, node_id: str) -> Port:
        for p in ports:
            if p.name == name:
                return p
        raise GraphError(f"{kind} port '{name}' not found on node '{node_id}'")

    def _topo_sort(self) -> List[str]:
        """Kahn 拓扑排序。"""
        in_deg: Dict[str, int] = {nid: 0 for nid in self._nodes}
        adj: Dict[str, List[str]] = defaultdict(list)
        for edge in self._edges:
            adj[edge.source_node].append(edge.target_node)
            in_deg[edge.target_node] += 1
        # 按字母序入度为 0 的优先
        queue = deque(sorted([nid for nid, d in in_deg.items() if d == 0]))
        order: List[str] = []
        while queue:
            n = queue.popleft()
            order.append(n)
            for m in sorted(adj[n]):
                in_deg[m] -= 1
                if in_deg[m] == 0:
                    queue.append(m)
        return order

    def _build_parallel_plan(self, topo: List[str]) -> List[List[str]]:
        """同层无依赖节点分到一组 (可并行)。"""
        if not topo:
            return []
        in_deg: Dict[str, int] = {nid: 0 for nid in self._nodes}
        adj: Dict[str, List[str]] = defaultdict(list)
        for edge in self._edges:
            adj[edge.source_node].append(edge.target_node)
            in_deg[edge.target_node] += 1
        plan: List[List[str]] = []
        remaining = set(topo)
        while remaining:
            # 当前可执行的：入度为 0
            layer = sorted([nid for nid in remaining if in_deg[nid] == 0])
            if not layer:
                break
            plan.append(layer)
            for n in layer:
                remaining.discard(n)
                for m in adj[n]:
                    in_deg[m] -= 1
        return plan

    # ---- 可视化 ----
    def to_dag_view(self) -> DAGView:
        nodes = [
            {
                "id": n.id,
                "category": n.category.value,
                "inputs": [p.to_dict() for p in n.inputs],
                "outputs": [p.to_dict() for p in n.outputs],
                "params": dict(n.parameters),
                "fingerprint": n.fingerprint(),
            }
            for n in self._nodes.values()
        ]
        edges = [
            {
                "source": e.source_node,
                "source_port": e.source_port,
                "target": e.target_node,
                "target_port": e.target_port,
            }
            for e in self._edges
        ]
        compiled = self.compile()
        return DAGView(nodes=nodes, edges=edges, layers=compiled.execution_plan)

    # ---- 指纹 ----
    def fingerprint(self) -> str:
        """图指纹 = hash(sorted nodes + sorted edges)。"""
        h = hashlib.sha256()
        for nid in sorted(self._nodes.keys()):
            node = self._nodes[nid]
            h.update(nid.encode())
            h.update(node.fingerprint().encode())
        for e in sorted(self._edges, key=lambda x: (x.source_node, x.source_port, x.target_node, x.target_port)):
            h.update(f"{e.source_node}:{e.source_port}->{e.target_node}:{e.target_port}".encode())
        return h.hexdigest()[:16]

    def __repr__(self) -> str:
        return f"ResearchGraph(name='{self.name}', nodes={len(self._nodes)}, edges={len(self._edges)})"

"""
CachePlanner — 编译期缓存规划

基于 Node 的 cache_policy + estimate_cost 生成 CachePlan:
  - 廉价节点 (cost<=2) → L1 Memory
  - 中等节点 (cost=3) → L2 Parquet
  - 高价值节点 (cost>=4) → L3 FeatureStore

输入: CompiledGraph
输出: CachePlan (node_id -> CacheDecision)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ..graph import CompiledGraph, ResearchGraph
from ..node.base import CachePolicy


@dataclass
class CacheDecision:
    node_id: str
    policy: CachePolicy
    level: str  # "L1" / "L2" / "L3" / "NONE"
    reason: str = ""


class CachePlanner:
    """编译期缓存规划器。"""

    def plan(self, graph: ResearchGraph, compiled: CompiledGraph) -> Dict[str, CacheDecision]:
        decisions: Dict[str, CacheDecision] = {}
        for node_id in compiled.topo_order:
            node = graph.get_node(node_id)
            if node is None:
                continue
            policy = node.cache_policy()
            cost = node.estimate_cost().stars
            level, reason = self._decide(policy, cost)
            decisions[node_id] = CacheDecision(
                node_id=node_id, policy=policy, level=level, reason=reason
            )
        return decisions

    @staticmethod
    def _decide(policy: CachePolicy, cost: int) -> tuple:
        if policy == CachePolicy.NONE:
            return "NONE", "node opts out of cache"
        if policy == CachePolicy.RESEARCH_ASSET:
            return "L3", "explicit research_asset policy"
        if policy == CachePolicy.DISK:
            return "L2", "explicit disk policy"
        # MEMORY / AUTO: 按 cost 细分
        if cost <= 2:
            return "L1", f"cheap node (cost={cost})"
        elif cost == 3:
            return "L2", f"medium node (cost={cost})"
        else:
            return "L3", f"expensive node (cost={cost})"


__all__ = ["CachePlanner", "CacheDecision"]

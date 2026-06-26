"""
IncrementalPlanner — 增量执行规划器

6 种策略:
  - FULL: 全量重算 (不支持增量或数据变更过大)
  - APPEND_ONLY: 仅追加新数据 (适合 INSERT)
  - UPDATE_TAIL: 更新尾部 (适合时间序列尾部追加)
  - RECOMPUTE_SUBGRAPH: 重算 dirty 子图
  - USE_CACHE: 使用缓存 (无需计算)
  - FALLBACK: 降级到全量 (增量失败)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from ..graph import ResearchGraph
from .changeset import ChangeOp, ChangeSet
from .delta_analyzer import DirtyGraph


class IncrementalStrategy(str, Enum):
    FULL = "full"  # 全量重算
    APPEND_ONLY = "append_only"  # 仅追加
    UPDATE_TAIL = "update_tail"  # 更新尾部
    RECOMPUTE_SUBGRAPH = "recompute_subgraph"  # 重算 dirty 子图
    USE_CACHE = "use_cache"  # 使用缓存
    FALLBACK = "fallback"  # 降级到全量


@dataclass
class IncrementalPlan:
    """单个节点的增量执行计划。"""
    node_id: str
    strategy: IncrementalStrategy
    reason: str = ""
    dirty: bool = False


class IncrementalPlanner:
    """增量执行规划器。"""

    def plan(
        self,
        graph: ResearchGraph,
        dirty_graph: DirtyGraph,
        changeset: ChangeSet,
    ) -> Dict[str, IncrementalPlan]:
        """为图中每个节点生成增量执行计划。"""
        plans: Dict[str, IncrementalPlan] = {}
        # 分析变更类型分布
        op_counts = self._count_ops(changeset)
        all_inserts = op_counts.get(ChangeOp.INSERT, 0) > 0 and op_counts.get(ChangeOp.UPDATE, 0) == 0 and op_counts.get(ChangeOp.DELETE, 0) == 0
        only_tail = self._is_tail_only(changeset)

        for node_id in graph.node_ids():
            node = graph.get_node(node_id)
            if node is None:
                continue
            is_dirty = dirty_graph.is_dirty(node_id)
            if not is_dirty:
                plans[node_id] = IncrementalPlan(
                    node_id=node_id,
                    strategy=IncrementalStrategy.USE_CACHE,
                    reason="not affected by changeset",
                    dirty=False,
                )
                continue
            # dirty 节点
            supports_inc = node.supports_incremental()
            if not supports_inc:
                plans[node_id] = IncrementalPlan(
                    node_id=node_id,
                    strategy=IncrementalStrategy.FULL,
                    reason="node does not support incremental",
                    dirty=True,
                )
                continue
            # 支持增量
            if all_inserts and only_tail:
                strategy = IncrementalStrategy.APPEND_ONLY
                reason = "pure tail inserts"
            elif all_inserts:
                strategy = IncrementalStrategy.UPDATE_TAIL
                reason = "inserts only"
            else:
                strategy = IncrementalStrategy.RECOMPUTE_SUBGRAPH
                reason = "mixed changes"
            plans[node_id] = IncrementalPlan(
                node_id=node_id,
                strategy=strategy,
                reason=reason,
                dirty=True,
            )
        return plans

    def _count_ops(self, cs: ChangeSet) -> Dict[ChangeOp, int]:
        counts: Dict[ChangeOp, int] = {op: 0 for op in ChangeOp}
        for c in cs.changes:
            counts[c.op] += 1
        return counts

    def _is_tail_only(self, cs: ChangeSet) -> bool:
        """检查所有 INSERT 是否都晚于现有数据尾部 (简化:True)。"""
        return True


__all__ = ["IncrementalPlanner", "IncrementalPlan", "IncrementalStrategy"]

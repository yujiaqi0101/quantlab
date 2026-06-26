"""
CacheInvalidator — 反向依赖索引 + 事件驱动失效传播

当上游节点缓存失效时，所有下游节点缓存也应失效。
  Close 变更 → Return/EMA/MACD 失效，但 ATR 不失效 (ATR 直接读 frame 不依赖 close)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Dict, List, Set

from .manifest import CacheManifest

logger = logging.getLogger(__name__)


class CacheInvalidator:
    """反向依赖索引 + 失效传播。"""

    def __init__(self, manifest: CacheManifest) -> None:
        self._manifest = manifest
        # node_id -> 下游 node_id 集合 (反向索引)
        self._downstream_index: Dict[str, Set[str]] = defaultdict(set)

    def register_dependency(self, upstream_node: str, downstream_node: str) -> None:
        """注册依赖关系：downstream 依赖 upstream。"""
        self._downstream_index[upstream_node].add(downstream_node)

    def invalidate(self, node_id: str) -> List[str]:
        """失效 node_id 及其所有下游 (递归)。返回所有被失效的 node_id。"""
        invalidated: List[str] = []
        visited: Set[str] = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            invalidated.append(current)
            # 从 manifest 删除该节点所有缓存条目
            for entry in self._manifest.find_by_node(current):
                self._manifest.remove(entry.key)
            # 递归失效下游
            for downstream in self._downstream_index.get(current, set()):
                if downstream not in visited:
                    queue.append(downstream)
        logger.info("invalidated %d nodes: %s", len(invalidated), invalidated)
        return invalidated

    def downstream_of(self, node_id: str) -> Set[str]:
        """直接下游。"""
        return set(self._downstream_index.get(node_id, set()))

    def all_downstream(self, node_id: str) -> Set[str]:
        """所有下游 (递归)。"""
        result: Set[str] = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            for d in self._downstream_index.get(current, set()):
                if d not in result:
                    result.add(d)
                    queue.append(d)
        return result

    def clear(self) -> None:
        self._downstream_index.clear()


__all__ = ["CacheInvalidator"]

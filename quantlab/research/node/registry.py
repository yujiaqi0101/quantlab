"""
NodeRegistry — 统一节点注册表

替代旧 FeatureRegistry 和 FactorRegistry，管理所有 ResearchNode。
  - 线程安全
  - id + version 并存 (RSI@1.0.0 与 RSI@2.0.0 可并存)
  - 启动时自动注册所有 builtin 节点
"""
from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from .base import ResearchNode
from .manifest import NodeCategory


class NodeRegistry:
    """统一节点注册表 (id, version) -> node_class。"""

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], type] = {}
        self._lock = threading.RLock()

    def register(self, node_class: type, version: str = "1.0.0") -> "NodeRegistry":
        """注册节点类。node_class 必须是 ResearchNode 子类。"""
        if not issubclass(node_class, ResearchNode):
            raise TypeError(f"{node_class} must be subclass of ResearchNode")
        # 实例化一次获取 id
        try:
            instance = node_class()
            node_id = instance.id
        except Exception:
            node_id = node_class.__name__.lower()
        with self._lock:
            self._store[(node_id, version)] = node_class
        return self

    def get(
        self, node_id: str, version: str = "1.0.0"
    ) -> Optional[type]:
        with self._lock:
            return self._store.get((node_id, version))

    def get_latest(self, node_id: str) -> Optional[type]:
        """获取最新版本的节点类。"""
        with self._lock:
            versions = [v for (nid, v) in self._store if nid == node_id]
            if not versions:
                return None
            # 简单版本排序 (语义化版本)
            versions.sort(key=lambda v: tuple(int(x) for x in v.split(".")))
            return self._store.get((node_id, versions[-1]))

    def list_nodes(self) -> List[Dict]:
        with self._lock:
            return [
                {"id": nid, "version": ver, "class": cls.__name__}
                for (nid, ver), cls in self._store.items()
            ]

    def list_by_category(self, category: NodeCategory) -> List[Dict]:
        with self._lock:
            result = []
            for (nid, ver), cls in self._store.items():
                try:
                    inst = cls()
                    if inst.category == category:
                        result.append({"id": nid, "version": ver, "class": cls.__name__})
                except Exception:
                    pass
            return result

    def list_categories(self) -> List[str]:
        with self._lock:
            cats = set()
            for (nid, ver), cls in self._store.items():
                try:
                    inst = cls()
                    cats.add(inst.category.value)
                except Exception:
                    pass
            return sorted(cats)

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


# 全局单例
_global_registry: Optional[NodeRegistry] = None
_global_lock = threading.Lock()


def get_registry() -> NodeRegistry:
    """获取全局 NodeRegistry (自动注册 builtin)。"""
    global _global_registry
    if _global_registry is None:
        with _global_lock:
            if _global_registry is None:
                reg = NodeRegistry()
                _register_builtins(reg)
                _global_registry = reg
    return _global_registry


def _register_builtins(reg: NodeRegistry) -> None:
    """注册所有 builtin 节点。"""
    from ..builtin import (
        Alpha014Node,
        ATRNode,
        CloseNode,
        CrossSectionRankNode,
        DiffNode,
        DirectionNode,
        EMANode,
        FutureReturnNode,
        HighNode,
        LiquidityFilterNode,
        LogNode,
        LowNode,
        MACDNode,
        NormalizeNode,
        OpenNode,
        PercentileNode,
        ReturnNode,
        RollingMaxNode,
        RollingMeanNode,
        RollingMinNode,
        RollingStdNode,
        RSINode,
        SMANode,
        UniverseFilterNode,
        VolumeNode,
        VWAPNode,
        ZScoreNode,
    )
    for cls in [
        OpenNode, HighNode, LowNode, CloseNode, VolumeNode, VWAPNode,
        ReturnNode, DiffNode, LogNode, ZScoreNode, NormalizeNode,
        RSINode, SMANode, EMANode, MACDNode, ATRNode,
        RollingMeanNode, RollingStdNode, RollingMaxNode, RollingMinNode,
        CrossSectionRankNode, PercentileNode,
        FutureReturnNode, DirectionNode,
        Alpha014Node,
        UniverseFilterNode, LiquidityFilterNode,
    ]:
        try:
            reg.register(cls)
        except Exception:
            pass


__all__ = ["NodeRegistry", "get_registry"]

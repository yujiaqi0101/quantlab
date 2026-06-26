"""
CacheManager — 5级缓存统一入口

提供 get/set 接口，按级别依次查询。
  L1 (Memory) -> L2 (Parquet) -> L3 (FeatureStore) -> L4 (Artifact) -> L5 (Redis)
"""
from __future__ import annotations

import logging
from typing import List, Optional

from ..frame import ResearchFrame
from .base import CacheEntry, CacheKey
from .invalidator import CacheInvalidator
from .manifest import CacheManifest, CacheManifestEntry
from .memory import MemoryCache
from .parquet import ParquetCache
from .planner import CachePlanner, CacheDecision

logger = logging.getLogger(__name__)


class CacheManager:
    """5级缓存统一入口。"""

    def __init__(
        self,
        memory_cache: Optional[MemoryCache] = None,
        parquet_cache: Optional[ParquetCache] = None,
        manifest: Optional[CacheManifest] = None,
        invalidator: Optional[CacheInvalidator] = None,
        planner: Optional[CachePlanner] = None,
    ) -> None:
        self.memory = memory_cache or MemoryCache()
        self.parquet = parquet_cache
        self.manifest = manifest or CacheManifest()
        self.invalidator = invalidator or CacheInvalidator(self.manifest)
        self.planner = planner or CachePlanner()
        # L3/L4/L5 预留接口
        self.feature_store = None
        self.artifact_store = None
        self.redis = None

    def get(self, key: CacheKey) -> Optional[CacheEntry]:
        """按级别依次查询。命中后回填上级。"""
        # L1
        entry = self.memory.get(key)
        if entry:
            return entry
        # L2
        if self.parquet:
            entry = self.parquet.get(key)
            if entry:
                # 回填 L1
                self.memory.set(entry)
                return entry
        # L3/L4/L5 预留
        return None

    def set(
        self,
        key: CacheKey,
        data: ResearchFrame,
        level: str = "L1",
        ttl: Optional[float] = None,
        upstream_keys: Optional[List[str]] = None,
    ) -> None:
        """写入缓存到指定级别。"""
        entry = CacheEntry(key=key, data=data, ttl=ttl)
        # 注册到 manifest
        manifest_entry = CacheManifestEntry(
            key=str(key),
            node_id=key.node_id,
            node_fingerprint=key.node_fingerprint,
            dataset_fingerprint=key.dataset_fingerprint,
            level=level,
            created_at=entry.created_at,
            ttl=ttl,
            size_bytes=entry.size_bytes,
            upstream_keys=upstream_keys or [],
        )
        self.manifest.add(manifest_entry)
        # 实际写入
        if level == "L1":
            self.memory.set(entry)
        elif level == "L2" and self.parquet:
            self.parquet.set(entry)
            # 同时回填 L1
            self.memory.set(entry)
        elif level == "L3":
            # 预留 L3
            self.memory.set(entry)
        else:
            self.memory.set(entry)

    def invalidate(self, key: CacheKey) -> bool:
        """失效单个 key (含传播)。"""
        # 找到 node_id
        manifest_entry = self.manifest.get(str(key))
        if manifest_entry is None:
            return False
        node_id = manifest_entry.node_id
        # 失效传播
        invalidated = self.invalidator.invalidate(node_id)
        # 清理各级缓存
        self.memory.invalidate(key)
        if self.parquet:
            self.parquet.invalidate(key)
        return len(invalidated) > 0

    def invalidate_node(self, node_id: str) -> List[str]:
        """失效一个节点的所有缓存 (含下游传播)。"""
        # 先收集所有待失效的 node_id (含下游)
        all_nodes = {node_id} | self.invalidator.all_downstream(node_id)
        # 收集这些 node 的所有 manifest entries 的 key 字符串
        keys_to_remove = []
        for nid in all_nodes:
            for entry in self.manifest.find_by_node(nid):
                keys_to_remove.append(entry.key)
        # 调用 invalidator 失效 manifest
        invalidated = self.invalidator.invalidate(node_id)
        # 清理 memory/parquet 中实际数据
        for key_str in keys_to_remove:
            # 在 memory 中找匹配的 CacheKey
            for ck in list(self.memory._store.keys()):
                if str(ck) == key_str:
                    self.memory.invalidate(ck)
                    break
            if self.parquet:
                # parquet 文件名是 key hash
                pq_path = self.parquet._dir / f"{key_str}.parquet"
                if pq_path.exists():
                    pq_path.unlink()
                meta_path = self.parquet._dir / f"{key_str}.meta.json"
                if meta_path.exists():
                    meta_path.unlink()
        return invalidated

    def stats(self) -> dict:
        return {
            "memory": self.memory.stats(),
            "parquet": self.parquet.stats() if self.parquet else None,
            "manifest_entries": len(self.manifest.list_all()),
        }

    def clear(self) -> None:
        self.memory.clear()
        if self.parquet:
            self.parquet.clear()
        self.manifest.clear()
        self.invalidator.clear()


__all__ = ["CacheManager"]

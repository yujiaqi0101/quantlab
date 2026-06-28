"""
Cache Layer — 5级缓存系统

L1 Memory  : 进程内 dict (最快)
L2 Parquet : 本地 parquet 文件
L3 FeatureStore : 跨执行持久化 (预留)
L4 Artifact : 分析产物 (预留)
L5 Redis   : 分布式缓存 (预留)
"""
from .base import CacheEntry, CacheKey, CacheLevel
from .invalidator import CacheInvalidator
from .manager import CacheManager
from .manifest import CacheManifest, CacheManifestEntry
from .memory import MemoryCache
from .parquet import ParquetCache
from .planner import CacheDecision, CachePlanner
from .window import WindowCache

_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager(parquet_cache=ParquetCache())
    return _cache_manager


__all__ = [
    "CacheKey",
    "CacheEntry",
    "CacheLevel",
    "MemoryCache",
    "WindowCache",
    "ParquetCache",
    "CacheManifest",
    "CacheManifestEntry",
    "CacheInvalidator",
    "CachePlanner",
    "CacheDecision",
    "CacheManager",
    "get_cache_manager",
]

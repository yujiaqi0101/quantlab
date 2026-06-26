"""
Cache Layer — 5级缓存系统

L1 Memory  : 进程内 dict (最快, 容量受限)
L2 Parquet : 本地 parquet 文件 (中等速度, 大容量)
L3 FeatureStore : 跨执行持久化 (MaterializedFeature)
L4 Artifact : SHAP/Importance/Distribution 等分析产物
L5 Redis   : 分布式缓存 (可选)

设计原则:
  - 统一 CacheKey (node_id + fingerprint + dataset_fingerprint)
  - 统一 CacheEntry (data + metadata + ttl)
  - 失效传播 (反向依赖索引)
  - 编译期缓存规划 (CachePlanner)
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..frame import ResearchFrame


# ---------------------------------------------------------------------- #
# CacheKey
# ---------------------------------------------------------------------- #
@dataclass(frozen=True)
class CacheKey:
    """缓存键：node_id + node_fingerprint + dataset_fingerprint。"""

    node_id: str
    node_fingerprint: str
    dataset_fingerprint: str = ""

    def __str__(self) -> str:
        h = hashlib.sha256()
        h.update(self.node_id.encode())
        h.update(self.node_fingerprint.encode())
        h.update(self.dataset_fingerprint.encode())
        return h.hexdigest()[:32]

    def __repr__(self) -> str:
        return f"CacheKey({self.node_id}/{self.node_fingerprint})"


# ---------------------------------------------------------------------- #
# CacheEntry
# ---------------------------------------------------------------------- #
@dataclass
class CacheEntry:
    """缓存条目。"""

    key: CacheKey
    data: ResearchFrame
    created_at: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # 秒, None=永久
    size_bytes: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.ttl is None:
            return False
        now = now or time.time()
        return (now - self.created_at) > self.ttl


# ---------------------------------------------------------------------- #
# CacheLevel
# ---------------------------------------------------------------------- #
class CacheLevel:
    """缓存级别枚举。"""

    L1_MEMORY = "L1_memory"
    L2_PARQUET = "L2_parquet"
    L3_FEATURE_STORE = "L3_feature_store"
    L4_ARTIFACT = "L4_artifact"
    L5_REDIS = "L5_redis"


__all__ = [
    "CacheKey",
    "CacheEntry",
    "CacheLevel",
]

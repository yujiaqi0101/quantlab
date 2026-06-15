"""
ResearchCache — V4.5 研究缓存

职责：
  - 缓存 DataFrame / Feature / Factor 计算结果
  - 基于 key + version 的 LRU 缓存
  - 支持磁盘持久化（parquet / pickle）
  - 避免 10GB 数据集每次重算

用法：
    cache = ResearchCache(cache_dir="storage/research_cache")
    cache.put("rsi14_AAPL", df_rsi)
    df = cache.get("rsi14_AAPL")
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger("quantlab.research.cache")


# ------------------------------------------------------------------
# Cache entry metadata
# ------------------------------------------------------------------
@dataclass(slots=True)
class CacheEntry:
    key: str
    version: str
    size_bytes: int
    created_at: str
    last_hit: str
    hit_count: int = 0
    dtype: str = ""           # "dataframe" / "series" / "object"
    metadata: Dict[str, Any] = field(default_factory=dict)


# ------------------------------------------------------------------
# ResearchCache
# ------------------------------------------------------------------
class ResearchCache:
    """
    研究缓存

    两层：
      L1: 内存 LRU（默认 512 条）
      L2: 磁盘 parquet/pickle（cache_dir 下）

    key 设计："{category}:{name}:{version}"
      category ∈ {"feature", "factor", "dataset", "artifact", "custom"}
    """

    def __init__(
        self,
        cache_dir: str = "storage/research_cache",
        max_memory_entries: int = 512,
    ) -> None:
        self.cache_dir = cache_dir
        self.max_memory_entries = max_memory_entries
        self._memory: OrderedDict[str, Tuple[Any, CacheEntry]] = OrderedDict()
        self._catalog: Dict[str, CacheEntry] = {}
        os.makedirs(cache_dir, exist_ok=True)
        self._load_catalog()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------
    def put(
        self,
        key: str,
        value: Any,
        category: str = "custom",
        version: str = "1",
        metadata: Optional[Dict] = None,
    ) -> CacheEntry:
        """写入缓存（内存 + 磁盘）"""
        entry = CacheEntry(
            key=key,
            version=version,
            size_bytes=self._estimate_size(value),
            created_at=_now_iso(),
            last_hit=_now_iso(),
            dtype=self._dtype_of(value),
            metadata=metadata or {},
        )
        # L1: 内存
        self._memory[key] = (value, entry)
        self._memory.move_to_end(key)
        self._evict_memory()
        # L2: 磁盘
        self._write_disk(key, value, category, version)
        # catalog
        self._catalog[key] = entry
        self._save_catalog()
        return entry

    def get(self, key: str, version: Optional[str] = None) -> Optional[Any]:
        """读取缓存，先 L1 再 L2"""
        # L1
        if key in self._memory:
            value, entry = self._memory[key]
            if version and entry.version != version:
                pass  # version 不匹配，fall through 到 L2
            else:
                self._memory.move_to_end(key)
                entry.hit_count += 1
                entry.last_hit = _now_iso()
                return value
        # L2
        val = self._read_disk(key, version)
        if val is not None:
            entry = self._catalog.get(key)
            if entry:
                entry.hit_count += 1
                entry.last_hit = _now_iso()
            self._memory[key] = (val, entry or self._make_entry(key, val, version or "1"))
            self._memory.move_to_end(key)
            self._evict_memory()
            return val
        return None

    def has(self, key: str, version: Optional[str] = None) -> bool:
        if key in self._memory:
            if version:
                _, entry = self._memory[key]
                return entry.version == version
            return True
        return self._disk_exists(key, version)

    def invalidate(self, key: str) -> bool:
        """删除某条缓存"""
        removed = False
        if key in self._memory:
            del self._memory[key]
            removed = True
        path = self._disk_path(key)
        if os.path.exists(path):
            os.remove(path)
            removed = True
        self._catalog.pop(key, None)
        if removed:
            self._save_catalog()
        return removed

    def clear(self) -> int:
        """清空所有缓存，返回删除条数"""
        count = len(self._memory)
        self._memory.clear()
        self._catalog.clear()
        # 清磁盘
        for fname in os.listdir(self.cache_dir):
            if fname.endswith((".parquet", ".pkl", ".json")):
                os.remove(os.path.join(self.cache_dir, fname))
        self._save_catalog()
        return count

    def stats(self) -> Dict[str, Any]:
        """缓存统计"""
        total_hits = sum(e.hit_count for e in self._catalog.values())
        total_size = sum(e.size_bytes for e in self._catalog.values())
        return {
            "memory_entries": len(self._memory),
            "disk_entries": len(self._catalog),
            "total_hits": total_hits,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "max_memory_entries": self.max_memory_entries,
        }

    def list_keys(self, category: Optional[str] = None) -> List[str]:
        """列出所有缓存 key，可选按 category 过滤"""
        if category is None:
            return list(self._catalog.keys())
        return [
            k for k, e in self._catalog.items()
            if k.startswith(f"{category}:")
        ]

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _evict_memory(self):
        while len(self._memory) > self.max_memory_entries:
            self._memory.popitem(last=False)

    def _disk_path(self, key: str) -> str:
        safe = _safe_filename(key)
        return os.path.join(self.cache_dir, f"{safe}.parquet")

    def _disk_meta_path(self, key: str) -> str:
        safe = _safe_filename(key)
        return os.path.join(self.cache_dir, f"{safe}.meta.json")

    def _write_disk(self, key: str, value: Any, category: str, version: str):
        path = self._disk_path(key)
        try:
            if isinstance(value, pd.DataFrame):
                value.to_parquet(path)
            elif isinstance(value, pd.Series):
                value.to_frame().to_parquet(path)
            else:
                import pickle
                pkl_path = path.replace(".parquet", ".pkl")
                with open(pkl_path, "wb") as f:
                    pickle.dump(value, f)
        except Exception as e:
            logger.warning(f"cache write fail [{key}]: {e}")

    def _read_disk(self, key: str, version: Optional[str] = None) -> Optional[Any]:
        path = self._disk_path(key)
        pkl_path = path.replace(".parquet", ".pkl")
        try:
            if os.path.exists(path):
                return pd.read_parquet(path)
            elif os.path.exists(pkl_path):
                import pickle
                with open(pkl_path, "rb") as f:
                    return pickle.load(f)
        except Exception as e:
            logger.warning(f"cache read fail [{key}]: {e}")
        return None

    def _disk_exists(self, key: str, version: Optional[str] = None) -> bool:
        path = self._disk_path(key)
        pkl_path = path.replace(".parquet", ".pkl")
        return os.path.exists(path) or os.path.exists(pkl_path)

    def _estimate_size(self, value: Any) -> int:
        try:
            if isinstance(value, pd.DataFrame):
                return int(value.memory_usage(deep=True).sum())
            elif isinstance(value, pd.Series):
                return int(value.memory_usage(deep=True))
            else:
                import sys
                return sys.getsizeof(value)
        except Exception:
            return 0

    def _dtype_of(self, value: Any) -> str:
        if isinstance(value, pd.DataFrame):
            return "dataframe"
        elif isinstance(value, pd.Series):
            return "series"
        return "object"

    def _make_entry(self, key: str, value: Any, version: str) -> CacheEntry:
        return CacheEntry(
            key=key, version=version,
            size_bytes=self._estimate_size(value),
            created_at=_now_iso(), last_hit=_now_iso(),
            dtype=self._dtype_of(value),
        )

    def _catalog_path(self) -> str:
        return os.path.join(self.cache_dir, "_catalog.json")

    def _load_catalog(self):
        cp = self._catalog_path()
        if not os.path.exists(cp):
            return
        try:
            with open(cp, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for k, d in raw.items():
                self._catalog[k] = CacheEntry(**d)
        except Exception:
            self._catalog = {}

    def _save_catalog(self):
        cp = self._catalog_path()
        try:
            raw = {k: asdict(v) for k, v in self._catalog.items()}
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(raw, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"catalog save fail: {e}")


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")


def _safe_filename(key: str) -> str:
    return hashlib.md5(key.encode()).hexdigest()[:16]

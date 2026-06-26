"""
L1 MemoryCache — 进程内 dict 缓存

特点:
  - 最快访问速度
  - 容量受限 (按条数或字节数)
  - LRU 淘汰策略
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Optional

from .base import CacheEntry, CacheKey


class MemoryCache:
    """L1 进程内缓存 (LRU)。"""

    def __init__(self, max_entries: int = 1000) -> None:
        self._store: OrderedDict[CacheKey, CacheEntry] = OrderedDict()
        self._max = max_entries
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def get(self, key: CacheKey) -> Optional[CacheEntry]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.is_expired():
                del self._store[key]
                self.misses += 1
                return None
            # LRU: 移到末尾 (最近使用)
            self._store.move_to_end(key)
            self.hits += 1
            return entry

    def set(self, entry: CacheEntry) -> None:
        with self._lock:
            key = entry.key
            self._store[key] = entry
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                self._store.popitem(last=False)

    def has(self, key: CacheKey) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._store[key]
                return False
            return True

    def invalidate(self, key: CacheKey) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self.hits = 0
            self.misses = 0

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            return {
                "level": "L1_memory",
                "entries": len(self._store),
                "max_entries": self._max,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": self.hits / total if total else 0.0,
            }


__all__ = ["MemoryCache"]

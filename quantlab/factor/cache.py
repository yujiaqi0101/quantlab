"""
因子计算缓存（简单进程内 LRU 缓存）
==================================
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Any, Optional

import pandas as pd


class FactorCache:
    """简单 LRU 缓存，key = (factor_name, dataset_id, symbol, param_hash)。"""

    def __init__(self, max_size: int = 256) -> None:
        self._cache: "OrderedDict[str, pd.DataFrame]" = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

    def _key(self, factor_name: str, dataset_id: str, symbol: str) -> str:
        return f"{factor_name}|{dataset_id}|{symbol or '*'}"

    def get(self, factor_name: str, dataset_id: str, symbol: str = "") -> Optional[pd.DataFrame]:
        key = self._key(factor_name, dataset_id, symbol)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            self._misses += 1
            return None

    def set(self, factor_name: str, dataset_id: str, df: pd.DataFrame, symbol: str = "") -> None:
        key = self._key(factor_name, dataset_id, symbol)
        with self._lock:
            self._cache[key] = df
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def invalidate(self, dataset_id: Optional[str] = None) -> None:
        with self._lock:
            if dataset_id is None:
                self._cache.clear()
                return
            keys = [k for k in self._cache if f"|{dataset_id}|" in k]
            for k in keys:
                self._cache.pop(k, None)

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(hit_rate, 4),
            }


_cache_instance: Optional[FactorCache] = None
_cache_lock = threading.Lock()


def get_factor_cache() -> FactorCache:
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = FactorCache()
    return _cache_instance

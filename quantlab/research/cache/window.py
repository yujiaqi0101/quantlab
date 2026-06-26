"""
L1 WindowCache — 滚动窗口缓存

针对 Rolling/EMA 等有状态节点，缓存最近 N 期的状态。
"""
from __future__ import annotations

import threading
from collections import deque
from typing import Any, Deque, Dict, Optional

from .base import CacheKey


class WindowCache:
    """滚动窗口缓存 (按 key 保存最近 window_size 条状态)。"""

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._store: Dict[CacheKey, Deque[Any]] = {}
        self._lock = threading.RLock()

    def get_state(self, key: CacheKey) -> Optional[Any]:
        with self._lock:
            dq = self._store.get(key)
            if not dq:
                return None
            return dq[-1]  # 最新状态

    def append_state(self, key: CacheKey, state: Any) -> None:
        with self._lock:
            dq = self._store.setdefault(key, deque(maxlen=self._window_size))
            dq.append(state)

    def get_history(self, key: CacheKey) -> list:
        with self._lock:
            dq = self._store.get(key)
            return list(dq) if dq else []

    def invalidate(self, key: CacheKey) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._store)


__all__ = ["WindowCache"]

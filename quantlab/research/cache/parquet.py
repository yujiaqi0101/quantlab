"""
L2 ParquetCache — 本地 parquet 文件缓存

特点:
  - 中等访问速度 (磁盘 IO)
  - 大容量
  - 跨进程持久化
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Optional

import pandas as pd

from ..frame import ResearchFrame
from .base import CacheEntry, CacheKey

logger = logging.getLogger(__name__)


class ParquetCache:
    """L2 本地 parquet 文件缓存。"""

    def __init__(self, cache_dir: str = ".quantlab_cache/parquet") -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.hits = 0
        self.misses = 0

    def _path(self, key: CacheKey) -> Path:
        return self._dir / f"{key}.parquet"

    def _meta_path(self, key: CacheKey) -> Path:
        return self._dir / f"{key}.meta.json"

    def get(self, key: CacheKey) -> Optional[CacheEntry]:
        with self._lock:
            path = self._path(key)
            if not path.exists():
                self.misses += 1
                return None
            try:
                df = pd.read_parquet(path)
                if isinstance(df.index, pd.MultiIndex):
                    pass
                else:
                    # 已 reset_index 保存，需要重建
                    if "datetime" in df.columns and "symbol" in df.columns:
                        df = df.set_index(["datetime", "symbol"])
                # 优先用 meta 文件中的 name，否则用 node_id
                name = self._read_meta_name(key) or key.node_id
                rf = ResearchFrame.from_panel(df, name=name)
                entry = CacheEntry(key=key, data=rf, size_bytes=path.stat().st_size)
                self.hits += 1
                return entry
            except Exception as e:
                logger.warning("parquet cache read failed for %s: %s", key, e)
                self.misses += 1
                return None

    def _read_meta_name(self, key: CacheKey) -> Optional[str]:
        import json
        meta_path = self._meta_path(key)
        if meta_path.exists():
            try:
                return json.loads(meta_path.read_text()).get("name")
            except Exception:
                return None
        return None

    def _write_meta_name(self, key: CacheKey, name: str) -> None:
        import json
        meta_path = self._meta_path(key)
        try:
            meta_path.write_text(json.dumps({"name": name}))
        except Exception:
            pass

    def set(self, entry: CacheEntry) -> None:
        with self._lock:
            path = self._path(entry.key)
            try:
                df = entry.data.data.reset_index()
                df.to_parquet(path, index=False)
                # 保存 name 到 meta 文件
                self._write_meta_name(entry.key, entry.data.name)
            except Exception as e:
                logger.warning("parquet cache write failed for %s: %s", entry.key, e)

    def has(self, key: CacheKey) -> bool:
        return self._path(key).exists()

    def invalidate(self, key: CacheKey) -> bool:
        with self._lock:
            path = self._path(key)
            if path.exists():
                path.unlink()
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            for p in self._dir.glob("*.parquet"):
                p.unlink()
            for p in self._dir.glob("*.meta.json"):
                p.unlink()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict:
        with self._lock:
            files = list(self._dir.glob("*.parquet"))
            total_size = sum(f.stat().st_size for f in files)
            return {
                "level": "L2_parquet",
                "dir": str(self._dir),
                "entries": len(files),
                "total_bytes": total_size,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": (
                    self.hits / (self.hits + self.misses)
                    if (self.hits + self.misses)
                    else 0.0
                ),
            }


__all__ = ["ParquetCache"]

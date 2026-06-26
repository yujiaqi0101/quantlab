"""
CacheManifest — 缓存元数据持久化

记录每个缓存条目的:
  - key (CacheKey 字符串)
  - node_id, node_fingerprint, dataset_fingerprint
  - level (L1/L2/...)
  - created_at, ttl, size_bytes
  - upstream_keys (上游缓存 key，用于反向失效)
"""
from __future__ import annotations

import json
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class CacheManifestEntry:
    key: str
    node_id: str
    node_fingerprint: str
    dataset_fingerprint: str = ""
    level: str = ""
    created_at: float = 0.0
    ttl: Optional[float] = None
    size_bytes: int = 0
    upstream_keys: List[str] = field(default_factory=list)
    meta: Dict = field(default_factory=dict)


class CacheManifest:
    """缓存清单 (持久化到 JSON)。"""

    def __init__(self, path: str = ".quantlab_cache/manifest.json") -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: Dict[str, CacheManifestEntry] = {}
        self._lock = threading.RLock()
        self._load()

    def add(self, entry: CacheManifestEntry) -> None:
        with self._lock:
            self._entries[entry.key] = entry
            self._save()

    def get(self, key: str) -> Optional[CacheManifestEntry]:
        with self._lock:
            return self._entries.get(key)

    def remove(self, key: str) -> bool:
        with self._lock:
            removed = self._entries.pop(key, None) is not None
            if removed:
                self._save()
            return removed

    def list_all(self) -> List[CacheManifestEntry]:
        with self._lock:
            return list(self._entries.values())

    def find_by_node(self, node_id: str) -> List[CacheManifestEntry]:
        with self._lock:
            return [e for e in self._entries.values() if e.node_id == node_id]

    def find_downstream(self, upstream_key: str) -> List[CacheManifestEntry]:
        """找出所有依赖 upstream_key 的下游条目。"""
        with self._lock:
            return [
                e for e in self._entries.values() if upstream_key in e.upstream_keys
            ]

    def _save(self) -> None:
        try:
            data = {k: asdict(v) for k, v in self._entries.items()}
            self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception:
            pass  # 持久化失败不阻塞主流程

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text())
            for k, d in data.items():
                self._entries[k] = CacheManifestEntry(**d)
        except Exception:
            pass

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._save()


__all__ = ["CacheManifest", "CacheManifestEntry"]

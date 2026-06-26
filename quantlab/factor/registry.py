"""
FactorRegistry — 全局因子注册表
===============================
"""
from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional

from .base import FactorInfo, FactorFn


class FactorRegistry:
    """线程安全的因子注册表。"""

    def __init__(self) -> None:
        self._factors: Dict[str, FactorInfo] = {}
        self._lock = threading.RLock()

    # ---------- 注册 ----------
    def register(
        self,
        name: str,
        category: str,
        description: str,
        fn: FactorFn,
        direction: int = 0,
        source: str = "custom",
        params: Optional[Dict] = None,
        overwrite: bool = False,
    ) -> FactorInfo:
        with self._lock:
            if name in self._factors and not overwrite:
                raise ValueError(f"因子 {name} 已注册，使用 overwrite=True 覆盖")
            info = FactorInfo(
                name=name,
                category=category,
                description=description,
                fn=fn,
                direction=direction,
                source=source,
                params=params or {},
            )
            self._factors[name] = info
            return info

    # ---------- 查询 ----------
    def get(self, name: str) -> Optional[FactorInfo]:
        return self._factors.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._factors

    def list_factors(self, category: Optional[str] = None) -> List[FactorInfo]:
        items = list(self._factors.values())
        if category:
            items = [f for f in items if f.category == category]
        items.sort(key=lambda x: x.name)
        return items

    def list_categories(self) -> List[str]:
        cats = sorted({f.category for f in self._factors.values()})
        return cats

    def clear(self) -> None:
        with self._lock:
            self._factors.clear()


# ---- 单例 ----
_registry_singleton: Optional[FactorRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> FactorRegistry:
    """获取全局 FactorRegistry 单例。"""
    global _registry_singleton
    if _registry_singleton is None:
        with _registry_lock:
            if _registry_singleton is None:
                _registry_singleton = FactorRegistry()
    return _registry_singleton
